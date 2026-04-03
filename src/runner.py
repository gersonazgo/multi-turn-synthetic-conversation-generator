from __future__ import annotations

from datetime import timedelta, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from dotenv import load_dotenv

load_dotenv()

from .exporter import save_batch, save_conversation
from .generator import generate_conversation
from .models import AssistantConfig, BatchConfig, Defaults, ScenarioConfig

app = typer.Typer(help="Multi-Turn Synthetic Conversation Generator")
console = Console()

STOP_LABELS = {
    "assistant_succeeded": "Assistant succeeded",
    "turns_ended": "Turn limit reached without success",
    "llm_transient_error": "ERROR — Persistent transient error (rate limit / timeout / server)",
    "llm_content_error": "ERROR — Empty or refused content from LLM",
    "llm_non_transient_error": "ERROR — Non-transient LLM failure",
}

CONFIG_DIR = Path("config")
ASSISTANT_DIR = CONFIG_DIR / "assistant"
USER_DIR = CONFIG_DIR / "user"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_defaults() -> Defaults:
    defaults_path = CONFIG_DIR / "defaults.yml"
    if defaults_path.exists():
        return Defaults(**_load_yaml(defaults_path))
    return Defaults()


def _parse_timezone(tz_str: str) -> timezone:
    if tz_str == "UTC":
        return timezone.utc
    try:
        hours = int(tz_str)
        return timezone(timedelta(hours=hours))
    except ValueError:
        return timezone.utc


def _load_assistant_config(path: Optional[Path] = None) -> AssistantConfig:
    config_path = path or ASSISTANT_DIR / "assistant.yml"
    return AssistantConfig(**_load_yaml(config_path))


def _load_scenario(name: str) -> ScenarioConfig:
    scenario_path = USER_DIR / f"{name}.yml"
    if not scenario_path.exists():
        raise FileNotFoundError(f"File not found: {scenario_path}")
    return ScenarioConfig(**_load_yaml(scenario_path))


def _list_scenarios() -> list[str]:
    if not USER_DIR.exists():
        return []
    return [p.stem for p in USER_DIR.glob("*.yml")]


def _run_scenario(
    scenario_name: str,
    assistant_config: AssistantConfig,
    defaults: Defaults,
    max_turns_override: Optional[int],
    output_dir_override: Optional[str],
    delay_override: Optional[float] = None,
) -> None:
    scenario = _load_scenario(scenario_name)
    max_turns = max_turns_override or scenario.max_turns or defaults.max_turns
    output_dir = output_dir_override or defaults.output_dir
    delay = delay_override if delay_override is not None else defaults.delay
    tz = _parse_timezone(defaults.timezone)

    console.print(Panel(
        f"[bold]{scenario.scenario}[/]\n"
        f"Persona: {scenario.persona}\n"
        f"Collaboration: {scenario.collaboration}\n"
        f"User model: {scenario.model} (temp={scenario.temperature})\n"
        f"Assistant model: {assistant_config.model} (temp={assistant_config.temperature})\n"
        f"Turns: {max_turns}",
        title=f"Test Case: {scenario.test_case}",
    ))

    conversation = generate_conversation(
        assistant_config, scenario, max_turns,
        delay=delay, stop_phrase=defaults.stop_phrase, tz=tz,
    )
    json_path, docx_path = save_conversation(conversation, output_dir)

    stop_label = STOP_LABELS.get(conversation.conversation_stop_reason, conversation.conversation_stop_reason)
    console.print(f"\n[bold green]JSON:[/] {json_path}")
    console.print(f"[bold green]DOCX:[/] {docx_path}")
    console.print(f"[dim]Total turns: {conversation.metadata.total_turns} | Reason: {stop_label}[/]")


@app.command()
def run(
    scenario: str = typer.Argument(help="Scenario name (without .yml extension)"),
    assistant_config: Optional[Path] = typer.Option(None, "--assistant-config", help="Path to assistant config"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Override max turns"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Output directory"),
    delay: Optional[float] = typer.Option(None, "--delay", help="Delay in seconds between LLM calls (useful for rate limits)"),
) -> None:
    """Run a specific scenario."""
    defaults = _load_defaults()
    assistant = _load_assistant_config(assistant_config)
    _run_scenario(scenario, assistant, defaults, max_turns, output_dir, delay_override=delay)


@app.command()
def run_all(
    assistant_config: Optional[Path] = typer.Option(None, "--assistant-config", help="Path to assistant config"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Override max turns"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Output directory"),
    delay: Optional[float] = typer.Option(None, "--delay", help="Delay in seconds between LLM calls"),
) -> None:
    """Run all scenarios in config/user/."""
    scenarios = _list_scenarios()
    if not scenarios:
        console.print("[red]No scenarios found in config/user/[/]")
        raise typer.Exit(1)

    defaults = _load_defaults()
    assistant = _load_assistant_config(assistant_config)

    console.print(f"[bold]Running {len(scenarios)} scenario(s):[/] {', '.join(scenarios)}\n")

    for name in scenarios:
        _run_scenario(name, assistant, defaults, max_turns, output_dir, delay_override=delay)
        console.print()


@app.command()
def run_batch(
    batch_config: Path = typer.Option(CONFIG_DIR / "batch.yml", "--batch-config", help="Path to batch config"),
    assistant_config: Optional[Path] = typer.Option(None, "--assistant-config", help="Path to assistant config"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Override max turns"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Output directory"),
    delay: Optional[float] = typer.Option(None, "--delay", help="Delay in seconds between LLM calls"),
) -> None:
    """Run scenarios listed in batch.yml, repeating N times each."""
    batch = BatchConfig(**_load_yaml(batch_config))
    defaults = _load_defaults()
    assistant = _load_assistant_config(assistant_config)
    tz = _parse_timezone(defaults.timezone)

    # Validate: load all scenarios before starting
    console.print("[dim]Validating scenarios...[/]")
    errors = []
    for scenario_name in batch.scenarios:
        try:
            _load_scenario(scenario_name)
        except (typer.Exit, Exception) as e:
            errors.append(f"  {scenario_name}: {e}")
    if errors:
        console.print("[bold red]Errors found in scenarios:[/]")
        for err in errors:
            console.print(f"[red]{err}[/]")
        raise typer.Exit(1)
    console.print(f"[green]All {len(batch.scenarios)} scenario(s) validated.[/]\n")

    resolved_max_turns = max_turns
    resolved_output_dir = output_dir or defaults.output_dir
    resolved_delay = delay if delay is not None else defaults.delay

    total = len(batch.scenarios) * batch.conversation_rounds
    console.print(
        f"[bold]Batch:[/] {len(batch.scenarios)} scenario(s) x {batch.conversation_rounds} round(s) = {total} conversation(s)\n"
    )

    all_conversations = []

    for round_num in range(1, batch.conversation_rounds + 1):
        console.print(f"[bold]━━━ Round {round_num}/{batch.conversation_rounds} ━━━[/]\n")

        for scenario_name in batch.scenarios:
            scenario = _load_scenario(scenario_name)
            turns = resolved_max_turns or scenario.max_turns or defaults.max_turns

            console.print(Panel(
                f"[bold]{scenario.scenario}[/]\n"
                f"Persona: {scenario.persona}\n"
                f"Round: {round_num}/{batch.conversation_rounds}",
                title=f"Test Case: {scenario.test_case}",
            ))

            conversation = generate_conversation(
                assistant, scenario, turns,
                delay=resolved_delay, stop_phrase=defaults.stop_phrase, tz=tz,
            )
            json_path, _ = save_conversation(conversation, resolved_output_dir)
            all_conversations.append(conversation)

            stop_label = STOP_LABELS.get(conversation.conversation_stop_reason, conversation.conversation_stop_reason)
            console.print(f"[bold green]JSON:[/] {json_path}")
            console.print(f"[dim]Turns: {conversation.metadata.total_turns} | {stop_label}[/]\n")

    # Combined DOCX
    batch_docx = save_batch(all_conversations, resolved_output_dir)
    console.print(f"\n[bold green]Combined DOCX:[/] {batch_docx}")
    console.print(f"[dim]Total: {len(all_conversations)} conversation(s) generated[/]")


@app.command()
def list_scenarios() -> None:
    """List available scenarios."""
    scenarios = _list_scenarios()
    if not scenarios:
        console.print("[dim]No scenarios found.[/]")
        return
    for name in scenarios:
        scenario = _load_scenario(name)
        console.print(f"  [bold]{name}[/] — {scenario.test_case} | {scenario.scenario}")
