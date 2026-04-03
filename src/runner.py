from __future__ import annotations

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
from .models import BatchConfig, Defaults, NamiConfig, ScenarioConfig

app = typer.Typer(help="NAMI Evals — Gerador de conversas sintéticas multi-turno")
console = Console()

STOP_LABELS = {
    "nami_succeeded": "NAMI teve sucesso",
    "turns_ended": "Nami não conseguiu obter sucesso no limite de turnos estabelecido",
    "rate_limit_error": "ERRO — Rate limit",
    "llm_transient_error": "ERRO — Erro transiente persistente (rate limit / timeout / server)",
    "llm_content_error": "ERRO — Conteúdo vazio ou recusado pelo LLM",
    "llm_non_transient_error": "ERRO — Falha não-transiente do LLM",
    "role_swap_error": "ERRO — Paciente trocou de papel (role-swap)",
}

CONFIG_DIR = Path("config")
NAMI_DIR = CONFIG_DIR / "nami"
SCENARIOS_DIR = CONFIG_DIR / "scenarios"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_defaults() -> Defaults:
    defaults_path = CONFIG_DIR / "defaults.yml"
    if defaults_path.exists():
        return Defaults(**_load_yaml(defaults_path))
    return Defaults()


def _load_nami_config(path: Optional[Path] = None) -> NamiConfig:
    config_path = path or NAMI_DIR / "nami.yml"
    return NamiConfig(**_load_yaml(config_path))


def _load_scenario(name: str) -> ScenarioConfig:
    scenario_path = SCENARIOS_DIR / f"{name}.yml"
    if not scenario_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {scenario_path}")
    return ScenarioConfig(**_load_yaml(scenario_path))


def _list_scenarios() -> list[str]:
    if not SCENARIOS_DIR.exists():
        return []
    return [p.stem for p in SCENARIOS_DIR.glob("*.yml")]


def _run_scenario(
    scenario_name: str,
    nami_config: NamiConfig,
    defaults: Defaults,
    max_turns_override: Optional[int],
    output_dir_override: Optional[str],
    delay_override: Optional[float] = None,
) -> None:
    scenario = _load_scenario(scenario_name)
    max_turns = max_turns_override or scenario.max_turns or defaults.max_turns
    output_dir = output_dir_override or defaults.output_dir
    delay = delay_override if delay_override is not None else defaults.delay

    console.print(Panel(
        f"[bold]{scenario.scenario}[/]\n"
        f"Persona: {scenario.persona}\n"
        f"Colaboração: {scenario.collaboration}\n"
        f"Paciente modelo: {scenario.model} (temp={scenario.temperature})\n"
        f"NAMI modelo: {nami_config.model} (temp={nami_config.temperature})\n"
        f"Turnos: {max_turns}",
        title=f"Test Case: {scenario.test_case}",
    ))

    conversation = generate_conversation(nami_config, scenario, max_turns, delay=delay)
    json_path, docx_path = save_conversation(conversation, output_dir)

    stop_label = STOP_LABELS.get(conversation.conversation_stop_reason, conversation.conversation_stop_reason)
    console.print(f"\n[bold green]JSON:[/] {json_path}")
    console.print(f"[bold green]DOCX:[/] {docx_path}")
    console.print(f"[dim]Total de turnos: {conversation.metadata.total_turns} | Motivo: {stop_label}[/]")


@app.command()
def run(
    scenario: str = typer.Argument(help="Nome do cenário (sem extensão .yml)"),
    nami_config: Optional[Path] = typer.Option(None, "--nami-config", help="Caminho para config da NAMI"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Override de turnos máximos"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Diretório de saída"),
    delay: Optional[float] = typer.Option(None, "--delay", help="Delay em segundos entre chamadas LLM (útil para rate limits)"),
) -> None:
    """Roda um cenário específico."""
    defaults = _load_defaults()
    nami = _load_nami_config(nami_config)
    _run_scenario(scenario, nami, defaults, max_turns, output_dir, delay_override=delay)


@app.command()
def run_all(
    nami_config: Optional[Path] = typer.Option(None, "--nami-config", help="Caminho para config da NAMI"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Override de turnos máximos"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Diretório de saída"),
    delay: Optional[float] = typer.Option(None, "--delay", help="Delay em segundos entre chamadas LLM (útil para rate limits)"),
) -> None:
    """Roda todos os cenários em config/scenarios/."""
    scenarios = _list_scenarios()
    if not scenarios:
        console.print("[red]Nenhum cenário encontrado em config/scenarios/[/]")
        raise typer.Exit(1)

    defaults = _load_defaults()
    nami = _load_nami_config(nami_config)

    console.print(f"[bold]Rodando {len(scenarios)} cenário(s):[/] {', '.join(scenarios)}\n")

    for name in scenarios:
        _run_scenario(name, nami, defaults, max_turns, output_dir, delay_override=delay)
        console.print()


@app.command()
def run_batch(
    batch_config: Path = typer.Option(CONFIG_DIR / "batch.yml", "--batch-config", help="Caminho para config do batch"),
    nami_config: Optional[Path] = typer.Option(None, "--nami-config", help="Caminho para config da NAMI"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Override de turnos máximos"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Diretório de saída"),
    delay: Optional[float] = typer.Option(None, "--delay", help="Delay em segundos entre chamadas LLM"),
) -> None:
    """Roda cenários listados no batch.yml, repetindo N vezes cada."""
    batch = BatchConfig(**_load_yaml(batch_config))
    defaults = _load_defaults()
    nami = _load_nami_config(nami_config)

    # Validação: carrega todos os cenários antes de iniciar
    console.print("[dim]Validando cenários...[/]")
    errors = []
    for scenario_name in batch.scenarios:
        try:
            _load_scenario(scenario_name)
        except (typer.Exit, Exception) as e:
            errors.append(f"  {scenario_name}: {e}")
    if errors:
        console.print("[bold red]Erros encontrados nos cenários:[/]")
        for err in errors:
            console.print(f"[red]{err}[/]")
        raise typer.Exit(1)
    console.print(f"[green]Todos os {len(batch.scenarios)} cenário(s) validados.[/]\n")

    resolved_max_turns = max_turns
    resolved_output_dir = output_dir or defaults.output_dir
    resolved_delay = delay if delay is not None else defaults.delay

    total = len(batch.scenarios) * batch.conversation_rounds
    console.print(
        f"[bold]Batch:[/] {len(batch.scenarios)} cenário(s) x {batch.conversation_rounds} rodada(s) = {total} conversa(s)\n"
    )

    all_conversations = []

    for round_num in range(1, batch.conversation_rounds + 1):
        console.print(f"[bold]━━━ Rodada {round_num}/{batch.conversation_rounds} ━━━[/]\n")

        for scenario_name in batch.scenarios:
            scenario = _load_scenario(scenario_name)
            turns = resolved_max_turns or scenario.max_turns or defaults.max_turns

            console.print(Panel(
                f"[bold]{scenario.scenario}[/]\n"
                f"Persona: {scenario.persona}\n"
                f"Rodada: {round_num}/{batch.conversation_rounds}",
                title=f"Test Case: {scenario.test_case}",
            ))

            conversation = generate_conversation(nami, scenario, turns, delay=resolved_delay)
            json_path, _ = save_conversation(conversation, resolved_output_dir)
            all_conversations.append(conversation)

            stop_labels = {"nami_succeeded": "NAMI teve sucesso", "rate_limit_error": "ERRO — Rate limit", "turns_ended": "Nami não conseguiu obter sucesso no limite de turnos estabelecido"}
            stop_label = stop_labels.get(conversation.conversation_stop_reason, conversation.conversation_stop_reason)
            console.print(f"[bold green]JSON:[/] {json_path}")
            console.print(f"[dim]Turnos: {conversation.metadata.total_turns} | {stop_label}[/]\n")

    # DOCX combinado
    batch_docx = save_batch(all_conversations, resolved_output_dir)
    console.print(f"\n[bold green]DOCX combinado:[/] {batch_docx}")
    console.print(f"[dim]Total: {len(all_conversations)} conversa(s) gerada(s)[/]")


@app.command()
def list_scenarios() -> None:
    """Lista cenários disponíveis."""
    scenarios = _list_scenarios()
    if not scenarios:
        console.print("[dim]Nenhum cenário encontrado.[/]")
        return
    for name in scenarios:
        scenario = _load_scenario(name)
        console.print(f"  [bold]{name}[/] — {scenario.test_case} | {scenario.scenario}")
