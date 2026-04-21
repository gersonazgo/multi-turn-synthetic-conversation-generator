from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Generator
from datetime import datetime, timezone

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

from .models import AssistantConfig, Conversation, ConversationMetadata, Message, ScenarioConfig, ToolCall

console = Console()

# ── Custom exceptions ───────────────────────────────────────────────────────


class LLMError(Exception):
    """Base error for LLM call failures."""


class LLMTransientError(LLMError):
    """Transient error (rate limit, timeout, server error) after exhausting retries."""


class LLMContentError(LLMError):
    """Content error (None response, filter, refusal)."""


class LLMNonTransientError(LLMError):
    """Non-transient error (auth, bad request, policy violation)."""


# litellm exceptions that are transient and deserve retry
_TRANSIENT_ERRORS = (RateLimitError, InternalServerError, Timeout, ServiceUnavailableError, APIConnectionError)


# ── Tool definitions ───────────────────────────────────────────────────────

MAX_TOOL_ITERATIONS = 20

EMERGENCY_CONTACT_TOOL = {
    "type": "function",
    "function": {
        "name": "call_emergency_contact",
        "description": (
            "Aciona o contato de emergência do paciente. Use quando detectar "
            "risco iminente à vida (ideação suicida com plano, autolesão com "
            "risco de vida, posse de arma em contexto de intenção autolesiva) "
            "ou sofrimento muito intenso que exija intervenção externa "
            "imediata. O contato será notificado; você deve continuar "
            "acolhendo o paciente normalmente na conversa."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": (
                        "Justificativa clara e específica do porquê você está "
                        "acionando o contato de emergência neste momento. "
                        "Descreva os sinais observados e o nível de urgência."
                    ),
                },
            },
            "required": ["reasoning"],
        },
    },
}


def _mock_emergency_contact(args: dict) -> str:
    return "Contato de emergência acionado com sucesso."


def _is_user_satisfied(content: str, stop_phrase: str) -> bool:
    return stop_phrase in content.lower()


def _call_llm(model: str, temperature: float, messages: list[dict], max_retries: int = 3, tools: list[dict] | None = None):
    for attempt in range(max_retries):
        try:
            kwargs = {"model": model, "temperature": temperature, "messages": messages}
            if tools:
                kwargs["tools"] = tools
            response = litellm.completion(**kwargs)
            msg = response.choices[0].message
            has_tool_calls = bool(getattr(msg, "tool_calls", None))
            if (msg.content is None or msg.content == "") and not has_tool_calls:
                raise LLMContentError("LLM returned no content and no tool calls.")
            return msg
        except _TRANSIENT_ERRORS as e:
            wait = 15 * (attempt + 1)
            console.print(f"[yellow]Transient error ({type(e).__name__}). Attempt {attempt + 1}/{max_retries}. Waiting {wait}s...[/]")
            time.sleep(wait)
        except LLMContentError:
            raise
        except APIError as e:
            raise LLMNonTransientError(f"{type(e).__name__}: {e}") from e
    raise LLMTransientError("Persistent transient error after multiple retries.")


def _run_assistant_turn(
    model: str,
    temperature: float,
    assistant_history: list[dict],
    turn: int,
    on_tool_call: Callable[[str, dict, int], None] | None = None,
) -> tuple[str, list[dict]]:
    """Run one assistant turn with RAG-style tool loop.

    Returns (final_text, tool_calls_record). Raises LLMNonTransientError if
    the model exceeds MAX_TOOL_ITERATIONS in a single turn (safety fuse).
    """
    tool_calls_record: list[dict] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        msg = _call_llm(model, temperature, assistant_history, tools=[EMERGENCY_CONTACT_TOOL])

        if not getattr(msg, "tool_calls", None):
            return (msg.content or "", tool_calls_record)

        assistant_history.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {}
            tool_calls_record.append({"name": tc.function.name, "arguments": args})
            if on_tool_call:
                on_tool_call(tc.function.name, args, turn)

            result = _mock_emergency_contact(args) if tc.function.name == "call_emergency_contact" else ""
            assistant_history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    raise LLMNonTransientError(f"Exceeded {MAX_TOOL_ITERATIONS} tool iterations in a single turn")


def generate_conversation(
    assistant_config: AssistantConfig,
    scenario: ScenarioConfig,
    max_turns: int,
    delay: float = 0,
    stop_phrase: str = "thank you, assistant",
    tz: timezone = timezone.utc,
) -> Conversation:
    conv_id = f"{scenario.test_case}_{datetime.now(tz).strftime('%Y%m%d_%H%M%S')}"

    conversation = Conversation(
        id=conv_id,
        capability=scenario.capability,
        test_case=scenario.test_case,
        scenario=scenario.scenario,
        persona=scenario.persona,
        collaboration=scenario.collaboration,
        messages=[],
        metadata=ConversationMetadata(
            assistant_model=assistant_config.model,
            assistant_temperature=assistant_config.temperature,
            user_model=scenario.model,
            user_temperature=scenario.temperature,
        ),
    )

    assistant_history: list[dict] = [
        {"role": "system", "content": assistant_config.system_prompt, "cache_control": {"type": "ephemeral"}},
    ]
    user_history: list[dict] = [
        {"role": "system", "content": scenario.system_prompt, "cache_control": {"type": "ephemeral"}},
    ]

    # User sends first_message
    first_msg = Message(role="user", content=scenario.first_message)
    conversation.messages.append(first_msg)
    console.print(f"[bold cyan]{scenario.persona}:[/] {scenario.first_message}")

    assistant_history.append({"role": "user", "content": scenario.first_message})
    user_history.append({"role": "assistant", "content": scenario.first_message})

    stop_reason = "turns_ended"
    turn = 0

    def _log_tool_call(name: str, args: dict, turn_num: int) -> None:
        console.print(f"[bold red]Tool call (turn {turn_num}): {name}({args})[/]")

    try:
        for turn in range(1, max_turns + 1):
            # Assistant responds
            if delay > 0 and turn > 1:
                time.sleep(delay)
            console.print(f"[dim]Turn {turn}/{max_turns} — Assistant thinking...[/]")
            assistant_response, tool_calls_record = _run_assistant_turn(
                assistant_config.model,
                assistant_config.temperature,
                assistant_history,
                turn,
                on_tool_call=_log_tool_call,
            )
            assistant_msg = Message(
                role="assistant",
                content=assistant_response,
                tool_calls=[ToolCall(**tc) for tc in tool_calls_record] or None,
            )
            conversation.messages.append(assistant_msg)
            console.print(f"[bold green]Assistant:[/] {assistant_response}")

            assistant_history.append({"role": "assistant", "content": assistant_response})
            user_history.append({"role": "user", "content": assistant_response})

            if turn >= max_turns:
                break

            # User responds
            if delay > 0:
                time.sleep(delay)
            console.print(f"[dim]Turn {turn}/{max_turns} — {scenario.persona} thinking...[/]")
            user_msg_obj = _call_llm(scenario.model, scenario.temperature, user_history)
            user_response = user_msg_obj.content or ""

            user_msg = Message(role="user", content=user_response)
            conversation.messages.append(user_msg)
            console.print(f"[bold cyan]{scenario.persona}:[/] {user_response}")

            user_history.append({"role": "assistant", "content": user_response})
            assistant_history.append({"role": "user", "content": user_response})

            # User satisfied — assistant closes and we end
            if _is_user_satisfied(user_response, stop_phrase):
                console.print(f"[dim]Turn {turn + 1}/{max_turns} — Assistant closing...[/]")
                assistant_closing, closing_tool_calls = _run_assistant_turn(
                    assistant_config.model,
                    assistant_config.temperature,
                    assistant_history,
                    turn + 1,
                    on_tool_call=_log_tool_call,
                )
                assistant_closing_msg = Message(
                    role="assistant",
                    content=assistant_closing,
                    tool_calls=[ToolCall(**tc) for tc in closing_tool_calls] or None,
                )
                conversation.messages.append(assistant_closing_msg)
                console.print(f"[bold green]Assistant:[/] {assistant_closing}")
                stop_reason = "assistant_succeeded"
                turn += 1
                break
    except LLMTransientError:
        stop_reason = "llm_transient_error"
        console.print("[bold red]Conversation interrupted by persistent transient error (rate limit / timeout / server).[/]")
    except LLMContentError:
        stop_reason = "llm_content_error"
        console.print("[bold red]Conversation interrupted: LLM returned empty or refused content.[/]")
    except LLMNonTransientError as e:
        stop_reason = "llm_non_transient_error"
        console.print(f"[bold red]Conversation interrupted by non-transient error: {e}[/]")

    conversation.conversation_stop_reason = stop_reason
    conversation.metadata.total_turns = turn
    conversation.metadata.finished_at = datetime.now(timezone.utc).isoformat()

    return conversation


def generate_conversation_stream(
    assistant_config: AssistantConfig,
    scenario: ScenarioConfig,
    max_turns: int,
    cancel_event: threading.Event | None = None,
    assistant_config_name: str = "",
    stop_phrase: str = "thank you, assistant",
    tz: timezone = timezone.utc,
) -> Generator[dict, None, None]:
    """Streaming version of generate_conversation. Yields event dicts."""
    conv_id = f"{scenario.test_case}_{datetime.now(tz).strftime('%Y%m%d_%H%M%S')}"

    conversation = Conversation(
        id=conv_id,
        capability=scenario.capability,
        test_case=scenario.test_case,
        scenario=scenario.scenario,
        persona=scenario.persona,
        collaboration=scenario.collaboration,
        messages=[],
        metadata=ConversationMetadata(
            assistant_model=assistant_config.model,
            assistant_temperature=assistant_config.temperature,
            user_model=scenario.model,
            user_temperature=scenario.temperature,
            assistant_config_name=assistant_config_name,
        ),
    )

    assistant_history: list[dict] = [
        {"role": "system", "content": assistant_config.system_prompt, "cache_control": {"type": "ephemeral"}},
    ]
    user_history: list[dict] = [
        {"role": "system", "content": scenario.system_prompt, "cache_control": {"type": "ephemeral"}},
    ]

    # First message
    first_msg = Message(role="user", content=scenario.first_message)
    conversation.messages.append(first_msg)
    assistant_history.append({"role": "user", "content": scenario.first_message})
    user_history.append({"role": "assistant", "content": scenario.first_message})

    yield {"type": "message", "role": "user", "content": scenario.first_message, "turn": 0}

    stop_reason = "turns_ended"
    turn = 0

    # Buffer tool calls emitted from inside _run_assistant_turn (which is a
    # regular function, not a generator) so we can yield them after the
    # assistant text message.
    pending_tool_events: list[dict] = []

    def _collect_tool_call(name: str, args: dict, turn_num: int) -> None:
        pending_tool_events.append({"type": "tool_call", "name": name, "arguments": args, "turn": turn_num})

    try:
        for turn in range(1, max_turns + 1):
            if cancel_event and cancel_event.is_set():
                stop_reason = "cancelled"
                break

            # Assistant responds
            yield {"type": "status", "text": f"Turn {turn}/{max_turns} — Assistant thinking..."}
            pending_tool_events.clear()
            assistant_response, tool_calls_record = _run_assistant_turn(
                assistant_config.model,
                assistant_config.temperature,
                assistant_history,
                turn,
                on_tool_call=_collect_tool_call,
            )
            assistant_msg = Message(
                role="assistant",
                content=assistant_response,
                tool_calls=[ToolCall(**tc) for tc in tool_calls_record] or None,
            )
            conversation.messages.append(assistant_msg)
            assistant_history.append({"role": "assistant", "content": assistant_response})
            user_history.append({"role": "user", "content": assistant_response})

            yield {"type": "message", "role": "assistant", "content": assistant_response, "turn": turn}
            for ev in pending_tool_events:
                yield ev

            if turn >= max_turns:
                break

            if cancel_event and cancel_event.is_set():
                stop_reason = "cancelled"
                break

            # User responds
            yield {"type": "status", "text": f"Turn {turn}/{max_turns} — {scenario.persona} thinking..."}
            user_msg_obj = _call_llm(scenario.model, scenario.temperature, user_history)
            user_response = user_msg_obj.content or ""

            user_msg = Message(role="user", content=user_response)
            conversation.messages.append(user_msg)
            user_history.append({"role": "assistant", "content": user_response})
            assistant_history.append({"role": "user", "content": user_response})

            yield {"type": "message", "role": "user", "content": user_response, "turn": turn}

            if _is_user_satisfied(user_response, stop_phrase):
                if cancel_event and cancel_event.is_set():
                    stop_reason = "cancelled"
                    break
                yield {"type": "status", "text": f"Turn {turn + 1}/{max_turns} — Assistant closing..."}
                pending_tool_events.clear()
                assistant_closing, closing_tool_calls = _run_assistant_turn(
                    assistant_config.model,
                    assistant_config.temperature,
                    assistant_history,
                    turn + 1,
                    on_tool_call=_collect_tool_call,
                )
                assistant_closing_msg = Message(
                    role="assistant",
                    content=assistant_closing,
                    tool_calls=[ToolCall(**tc) for tc in closing_tool_calls] or None,
                )
                conversation.messages.append(assistant_closing_msg)
                yield {"type": "message", "role": "assistant", "content": assistant_closing, "turn": turn + 1}
                for ev in pending_tool_events:
                    yield ev
                stop_reason = "assistant_succeeded"
                turn += 1
                break

    except LLMTransientError:
        stop_reason = "llm_transient_error"
        yield {"type": "error", "message": "Persistent transient error (rate limit / timeout / server)."}
    except LLMContentError:
        stop_reason = "llm_content_error"
        yield {"type": "error", "message": "LLM returned empty or refused content."}
    except LLMNonTransientError as e:
        stop_reason = "llm_non_transient_error"
        yield {"type": "error", "message": f"Non-transient error: {e}"}

    conversation.conversation_stop_reason = stop_reason
    conversation.metadata.total_turns = turn
    conversation.metadata.finished_at = datetime.now(timezone.utc).isoformat()

    yield {"type": "done", "stop_reason": stop_reason, "total_turns": turn, "conversation": conversation.model_dump()}
