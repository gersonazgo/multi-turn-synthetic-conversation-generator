from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from dotenv import load_dotenv

load_dotenv()

from .exporter import save_conversation
from .generator import generate_conversation
from .models import Defaults, NamiConfig, ScenarioConfig

app = typer.Typer(help="NAMI Evals — Gerador de conversas sintéticas multi-turno")
console = Console()

CONFIG_DIR = Path("config")
SCENARIOS_DIR = CONFIG_DIR / "scenarios"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_defaults() -> Defaults:
    defaults_path = CONFIG_DIR / "defaults.yml"
    if defaults_path.exists():
        return Defaults(**_load_yaml(defaults_path))
    return Defaults()


def _load_nami_config(path: Optional[Path] = None) -> NamiConfig:
    config_path = path or CONFIG_DIR / "nami.yml"
    return NamiConfig(**_load_yaml(config_path))


def _load_scenario(name: str) -> ScenarioConfig:
    scenario_path = SCENARIOS_DIR / f"{name}.yml"
    if not scenario_path.exists():
        console.print(f"[red]Cenário não encontrado: {scenario_path}[/]")
        raise typer.Exit(1)
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

    stop_label = "NAMI teve sucesso" if conversation.conversation_stop_reason == "nami_succeeded" else "Limite de turnos atingido"
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
def list_scenarios() -> None:
    """Lista cenários disponíveis."""
    scenarios = _list_scenarios()
    if not scenarios:
        console.print("[dim]Nenhum cenário encontrado.[/]")
        return
    for name in scenarios:
        scenario = _load_scenario(name)
        console.print(f"  [bold]{name}[/] — {scenario.test_case} | {scenario.scenario}")
