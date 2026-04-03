from __future__ import annotations

import threading
import time
from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import litellm
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from rich.console import Console

from .models import Conversation, ConversationMetadata, Message, NamiConfig, ScenarioConfig

console = Console()

STOP_PHRASE = "obg, nami"

# ── Exceções customizadas ────────────────────────────────────────────────────


class LLMError(Exception):
    """Erro base para falhas de chamada LLM."""


class LLMTransientError(LLMError):
    """Erro transiente (rate limit, timeout, server error) após esgotar retries."""


class LLMContentError(LLMError):
    """Erro de conteúdo (resposta None, filtro, recusa)."""


class LLMNonTransientError(LLMError):
    """Erro não-transiente (auth, bad request, policy violation)."""


# Exceções do litellm que são transientes e merecem retry
_TRANSIENT_ERRORS = (RateLimitError, InternalServerError, Timeout, ServiceUnavailableError, APIConnectionError)

# ── Detecção de role-swap ────────────────────────────────────────────────────

_ROLE_SWAP_SIGNALS = [
    "como posso te ajudar",
    "estou aqui para",
    "você não está sozinha",
    "você não está sozinho",
    "me conte mais",
    "como você está se sentindo",
    "fico feliz que",
    "é importante que você saiba",
    "vamos conversar sobre",
    "conte comigo",
    "eu entendi o que você disse",
    "eu ouvi o que você disse",
    "isso foi corajoso",
    "isso importa muito",
    "isso foi importante",
    "faz sentido estar",
    "faz todo sentido",
    "eu acredito que você",
    "isso foi um ato de",
]


def _detect_role_swap(content: str, persona: str) -> bool:
    """Detecta se a resposta do paciente parece ser de terapeuta.

    Sinal forte: resposta começa endereçando alguém pelo nome
    (pacientes não se dirigem a si mesmos em terceira pessoa).
    Sinais fracos: frases terapêuticas (≥2 necessários).
    """
    lower = content.lower()
    stripped = content.strip()

    # Não marcar como role-swap se for a frase de encerramento ("Obg, Nami")
    if _is_patient_satisfied(lower):
        return False

    # Sinal forte: começa com nome próprio + pontuação (ex: "Bia, ...", "Beatriz. ...")
    # Paciente real escreve informal, começando com minúscula ("tô mal", "sim...", "eu não sei").
    # Role-swap endereça o paciente: "Bia, eu ouvi...", "Beatriz. Você fez isso."
    _NON_NAME_STARTERS = {
        "sim", "não", "nao", "ok", "bom", "bem", "olha", "nossa", "poxa",
        "enfim", "tipo", "então", "entao", "mas", "porque", "pois", "pronto",
        "certo", "aliás", "alias", "ah", "ei", "oi", "hm", "tá", "obg",
    }
    if stripped:
        first_word = stripped.split()[0]
        bare = first_word.rstrip(".,!:;")
        if (
            len(bare) >= 2
            and bare[0].isupper()
            and bare.isalpha()
            and first_word[-1] in ".,!:;"
            and bare.lower() not in _NON_NAME_STARTERS
        ):
            return True

    # Sinais fracos: precisa de ≥2 para ativar
    return sum(1 for s in _ROLE_SWAP_SIGNALS if s in lower) >= 2


def _is_patient_satisfied(content: str) -> bool:
    return STOP_PHRASE in content.lower()


def _call_llm(model: str, temperature: float, messages: list[dict], max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=model,
                temperature=temperature,
                messages=messages,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMContentError("LLM retornou conteúdo None (possível recusa ou filtro).")
            return content
        except _TRANSIENT_ERRORS as e:
            wait = 30 * (attempt + 1)
            console.print(f"[yellow]Erro transiente ({type(e).__name__}). Tentativa {attempt + 1}/{max_retries}. Aguardando {wait}s...[/]")
            time.sleep(wait)
        except LLMContentError:
            raise
        except APIError as e:
            raise LLMNonTransientError(f"{type(e).__name__}: {e}") from e
    raise LLMTransientError("Erro transiente persistente após múltiplas tentativas.")


def generate_conversation(
    nami_config: NamiConfig,
    scenario: ScenarioConfig,
    max_turns: int,
    delay: float = 0,
) -> Conversation:
    BRT = timezone(timedelta(hours=-3))
    conv_id = f"{scenario.test_case}_{datetime.now(BRT).strftime('%Y%m%d_%H%M%S')}"

    conversation = Conversation(
        id=conv_id,
        capability=scenario.capability,
        test_case=scenario.test_case,
        scenario=scenario.scenario,
        persona=scenario.persona,
        collaboration=scenario.collaboration,
        messages=[],
        metadata=ConversationMetadata(
            nami_model=nami_config.model,
            nami_temperature=nami_config.temperature,
            patient_model=scenario.model,
            patient_temperature=scenario.temperature,
        ),
    )

    # Históricos separados no formato OpenAI chat para cada LLM
    # cache_control permite cache de system prompts na Anthropic (5min TTL)
    nami_history: list[dict] = [
        {"role": "system", "content": nami_config.system_prompt, "cache_control": {"type": "ephemeral"}},
    ]
    patient_history: list[dict] = [
        {"role": "system", "content": scenario.system_prompt, "cache_control": {"type": "ephemeral"}},
    ]

    # Paciente envia first_message
    first_msg = Message(role="patient", content=scenario.first_message)
    conversation.messages.append(first_msg)
    console.print(f"[bold cyan]{scenario.persona}:[/] {scenario.first_message}")

    # Adiciona first_message aos históricos
    nami_history.append({"role": "user", "content": scenario.first_message})
    patient_history.append({"role": "assistant", "content": scenario.first_message})

    # Cada turno = 1 ida e volta (paciente + NAMI)
    # A first_message já é a primeira "ida", falta a "volta" da NAMI para completar o turno 1
    stop_reason = "turns_ended"
    turn = 0

    try:
        for turn in range(1, max_turns + 1):
            # NAMI responde
            if delay > 0 and turn > 1:
                time.sleep(delay)
            console.print(f"[dim]Turno {turn}/{max_turns} — NAMI pensando...[/]")
            nami_response = _call_llm(nami_config.model, nami_config.temperature, nami_history)
            nami_msg = Message(role="nami", content=nami_response)
            conversation.messages.append(nami_msg)
            console.print(f"[bold green]Nami:[/] {nami_response}")

            nami_history.append({"role": "assistant", "content": nami_response})
            patient_history.append({"role": "user", "content": nami_response})

            if turn >= max_turns:
                break

            # Paciente responde
            if delay > 0:
                time.sleep(delay)
            console.print(f"[dim]Turno {turn}/{max_turns} — {scenario.persona} pensando...[/]")
            patient_response = _call_llm(scenario.model, scenario.temperature, patient_history)

            # Detecta role-swap: paciente respondendo como terapeuta
            if _detect_role_swap(patient_response, scenario.persona):
                console.print(f"[yellow]Role-swap detectado. Tentando novamente com lembrete de papel...[/]")
                retry_messages = patient_history + [
                    {"role": "user", "content": f"[Lembre-se: você é {scenario.persona}. Responda APENAS como paciente, nunca como terapeuta ou conselheira.]"},
                ]
                patient_response = _call_llm(scenario.model, scenario.temperature, retry_messages)
                if _detect_role_swap(patient_response, scenario.persona):
                    console.print(f"[bold red]Role-swap persistente após retry. Encerrando conversa.[/]")
                    stop_reason = "role_swap_error"
                    break

            patient_msg = Message(role="patient", content=patient_response)
            conversation.messages.append(patient_msg)
            console.print(f"[bold cyan]{scenario.persona}:[/] {patient_response}")

            patient_history.append({"role": "assistant", "content": patient_response})
            nami_history.append({"role": "user", "content": patient_response})

            # Paciente satisfeito — NAMI fecha e encerramos
            if _is_patient_satisfied(patient_response):
                console.print(f"[dim]Turno {turn + 1}/{max_turns} — NAMI fechando...[/]")
                nami_closing = _call_llm(nami_config.model, nami_config.temperature, nami_history)
                nami_closing_msg = Message(role="nami", content=nami_closing)
                conversation.messages.append(nami_closing_msg)
                console.print(f"[bold green]Nami:[/] {nami_closing}")
                stop_reason = "nami_succeeded"
                turn += 1
                break
    except LLMTransientError:
        stop_reason = "llm_transient_error"
        console.print("[bold red]Conversa interrompida por erro transiente persistente (rate limit / timeout / server).[/]")
    except LLMContentError:
        stop_reason = "llm_content_error"
        console.print("[bold red]Conversa interrompida: LLM retornou conteúdo vazio ou recusado.[/]")
    except LLMNonTransientError as e:
        stop_reason = "llm_non_transient_error"
        console.print(f"[bold red]Conversa interrompida por erro não-transiente: {e}[/]")

    conversation.conversation_stop_reason = stop_reason
    conversation.metadata.total_turns = turn
    conversation.metadata.finished_at = datetime.now(timezone.utc).isoformat()

    return conversation


def generate_conversation_stream(
    nami_config: NamiConfig,
    scenario: ScenarioConfig,
    max_turns: int,
    cancel_event: threading.Event | None = None,
    nami_config_name: str = "",
) -> Generator[dict, None, None]:
    """Versão streaming de generate_conversation. Faz yield de eventos dict."""
    BRT = timezone(timedelta(hours=-3))
    conv_id = f"{scenario.test_case}_{datetime.now(BRT).strftime('%Y%m%d_%H%M%S')}"

    conversation = Conversation(
        id=conv_id,
        capability=scenario.capability,
        test_case=scenario.test_case,
        scenario=scenario.scenario,
        persona=scenario.persona,
        collaboration=scenario.collaboration,
        messages=[],
        metadata=ConversationMetadata(
            nami_model=nami_config.model,
            nami_temperature=nami_config.temperature,
            patient_model=scenario.model,
            patient_temperature=scenario.temperature,
            nami_config_name=nami_config_name,
        ),
    )

    nami_history: list[dict] = [
        {"role": "system", "content": nami_config.system_prompt, "cache_control": {"type": "ephemeral"}},
    ]
    patient_history: list[dict] = [
        {"role": "system", "content": scenario.system_prompt, "cache_control": {"type": "ephemeral"}},
    ]

    # First message
    first_msg = Message(role="patient", content=scenario.first_message)
    conversation.messages.append(first_msg)
    nami_history.append({"role": "user", "content": scenario.first_message})
    patient_history.append({"role": "assistant", "content": scenario.first_message})

    yield {"type": "message", "role": "patient", "content": scenario.first_message, "turn": 0}

    stop_reason = "turns_ended"
    turn = 0

    try:
        for turn in range(1, max_turns + 1):
            if cancel_event and cancel_event.is_set():
                stop_reason = "cancelled"
                break

            # NAMI responds
            yield {"type": "status", "text": f"Turno {turn}/{max_turns} — NAMI pensando..."}
            nami_response = _call_llm(nami_config.model, nami_config.temperature, nami_history)
            nami_msg = Message(role="nami", content=nami_response)
            conversation.messages.append(nami_msg)
            nami_history.append({"role": "assistant", "content": nami_response})
            patient_history.append({"role": "user", "content": nami_response})

            yield {"type": "message", "role": "nami", "content": nami_response, "turn": turn}

            if turn >= max_turns:
                break

            if cancel_event and cancel_event.is_set():
                stop_reason = "cancelled"
                break

            # Patient responds
            yield {"type": "status", "text": f"Turno {turn}/{max_turns} — {scenario.persona} pensando..."}
            patient_response = _call_llm(scenario.model, scenario.temperature, patient_history)

            if _detect_role_swap(patient_response, scenario.persona):
                retry_messages = patient_history + [
                    {"role": "user", "content": f"[Lembre-se: você é {scenario.persona}. Responda APENAS como paciente, nunca como terapeuta ou conselheira.]"},
                ]
                patient_response = _call_llm(scenario.model, scenario.temperature, retry_messages)
                if _detect_role_swap(patient_response, scenario.persona):
                    stop_reason = "role_swap_error"
                    break

            patient_msg = Message(role="patient", content=patient_response)
            conversation.messages.append(patient_msg)
            patient_history.append({"role": "assistant", "content": patient_response})
            nami_history.append({"role": "user", "content": patient_response})

            yield {"type": "message", "role": "patient", "content": patient_response, "turn": turn}

            if _is_patient_satisfied(patient_response):
                if cancel_event and cancel_event.is_set():
                    stop_reason = "cancelled"
                    break
                yield {"type": "status", "text": f"Turno {turn + 1}/{max_turns} — NAMI fechando..."}
                nami_closing = _call_llm(nami_config.model, nami_config.temperature, nami_history)
                nami_closing_msg = Message(role="nami", content=nami_closing)
                conversation.messages.append(nami_closing_msg)
                yield {"type": "message", "role": "nami", "content": nami_closing, "turn": turn + 1}
                stop_reason = "nami_succeeded"
                turn += 1
                break

    except LLMTransientError:
        stop_reason = "llm_transient_error"
        yield {"type": "error", "message": "Erro transiente persistente (rate limit / timeout / server)."}
    except LLMContentError:
        stop_reason = "llm_content_error"
        yield {"type": "error", "message": "LLM retornou conteúdo vazio ou recusado."}
    except LLMNonTransientError as e:
        stop_reason = "llm_non_transient_error"
        yield {"type": "error", "message": f"Erro não-transiente: {e}"}

    conversation.conversation_stop_reason = stop_reason
    conversation.metadata.total_turns = turn
    conversation.metadata.finished_at = datetime.now(timezone.utc).isoformat()

    yield {"type": "done", "stop_reason": stop_reason, "total_turns": turn, "conversation": conversation.model_dump()}
