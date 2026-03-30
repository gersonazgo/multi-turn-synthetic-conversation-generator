from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import litellm
from litellm.exceptions import RateLimitError
from rich.console import Console

from .models import Conversation, ConversationMetadata, Message, NamiConfig, ScenarioConfig

console = Console()

STOP_PHRASE = "obg, nami"


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
            return response.choices[0].message.content
        except RateLimitError:
            wait = 30 * (attempt + 1)
            console.print(f"[yellow]Rate limit atingido. Aguardando {wait}s...[/]")
            time.sleep(wait)
    raise RuntimeError("Rate limit excedido após múltiplas tentativas.")


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
    nami_history: list[dict] = [
        {"role": "system", "content": nami_config.system_prompt},
    ]
    patient_history: list[dict] = [
        {"role": "system", "content": scenario.system_prompt},
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
    except RuntimeError:
        stop_reason = "rate_limit_error"
        console.print("[bold red]Conversa interrompida por rate limit.[/]")

    conversation.conversation_stop_reason = stop_reason
    conversation.metadata.total_turns = turn
    conversation.metadata.finished_at = datetime.now(timezone.utc).isoformat()

    return conversation
