# nami-evals

Gerador de conversas sinteticas multi-turno entre paciente (LLM) e NAMI (LLM).

## Setup

```bash
uv sync
```

Configurar API keys no `.env`:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Comandos

```bash
# Rodar um cenario
uv run nami-evals run p01_camila

# Rodar todos os cenarios
uv run nami-evals run-all

# Listar cenarios disponiveis
uv run nami-evals list-scenarios
```

## Opcoes

```bash
--max-turns 20        # Override de turnos maximos
--delay 5             # Delay em segundos entre chamadas (util para rate limits)
--nami-config path    # Usar outro arquivo de config da NAMI
--output-dir path     # Diretorio de saida (default: datasets/)
```

## Arquivos de config

| Arquivo | O que faz |
|---|---|
| `config/nami.yml` | System prompt + modelo + temperatura da NAMI |
| `config/defaults.yml` | max_turns e output_dir |
| `config/scenarios/*.yml` | Um arquivo por cenario (persona do paciente) |

## Output

Cada execucao gera dois arquivos em `datasets/`:
- `.json` — dados estruturados completos
- `.docx` — formatado para revisao humana no Word
