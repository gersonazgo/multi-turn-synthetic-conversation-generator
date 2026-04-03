from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Empty, Queue

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

load_dotenv()

from .exporter import save_conversation
from .generator import generate_conversation_stream
from .models import Conversation, Defaults, NamiConfig, ScenarioConfig

app = FastAPI(title="NAMI Playground")

CONFIG_DIR = Path("config")
NAMI_DIR = CONFIG_DIR / "nami"
SCENARIOS_DIR = CONFIG_DIR / "scenarios"
BACKUPS_DIR = CONFIG_DIR / "backups"
WEB_DIR = Path(__file__).parent / "web"

BRT = timezone(timedelta(hours=-3))

# State for cancel support
_cancel_event: threading.Event | None = None


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_defaults() -> Defaults:
    defaults_path = CONFIG_DIR / "defaults.yml"
    if defaults_path.exists():
        return Defaults(**_load_yaml(defaults_path))
    return Defaults()


# ── Static ──────────────────────────────────────────────────────────────────


@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "index.html")


# ── Config endpoints ────────────────────────────────────────────────────────


@app.get("/api/configs/nami")
async def list_nami_configs():
    if not NAMI_DIR.exists():
        return []
    return [p.stem for p in sorted(NAMI_DIR.glob("*.yml"))]


@app.get("/api/configs/scenarios")
async def list_scenario_configs():
    if not SCENARIOS_DIR.exists():
        return []
    configs = []
    for p in sorted(SCENARIOS_DIR.glob("*.yml")):
        data = _load_yaml(p)
        configs.append({
            "name": p.stem,
            "test_case": data.get("test_case", p.stem),
            "scenario": data.get("scenario", ""),
        })
    return configs


@app.get("/api/configs/nami/{name}")
async def get_nami_config(name: str):
    path = NAMI_DIR / f"{name}.yml"
    if not path.exists():
        raise HTTPException(404, f"Config não encontrada: {name}")
    return JSONResponse({"name": name, "content": path.read_text(encoding="utf-8")})


@app.put("/api/configs/nami/{name}")
async def save_nami_config(name: str, request: Request):
    body = await request.json()
    content = body.get("content", "")
    if not content.strip():
        raise HTTPException(400, "Conteúdo vazio")

    # Validate YAML
    try:
        parsed = yaml.safe_load(content)
        NamiConfig(**parsed)
    except Exception as e:
        raise HTTPException(400, f"YAML inválido: {e}")

    path = NAMI_DIR / f"{name}.yml"

    # Backup if file exists
    if path.exists():
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(BRT).strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUPS_DIR / f"{name}_{timestamp}.yml"
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    path.write_text(content, encoding="utf-8")
    return {"status": "saved", "name": name}


# ── Conversation stream ────────────────────────────────────────────────────


@app.get("/api/conversation/stream")
async def conversation_stream(nami: str, scenario: str):
    global _cancel_event

    nami_path = NAMI_DIR / f"{nami}.yml"
    scenario_path = SCENARIOS_DIR / f"{scenario}.yml"

    if not nami_path.exists():
        raise HTTPException(404, f"Config Nami não encontrada: {nami}")
    if not scenario_path.exists():
        raise HTTPException(404, f"Cenário não encontrado: {scenario}")

    nami_config = NamiConfig(**_load_yaml(nami_path))
    scenario_config = ScenarioConfig(**_load_yaml(scenario_path))
    defaults = _load_defaults()
    max_turns = scenario_config.max_turns or defaults.max_turns

    _cancel_event = threading.Event()
    cancel = _cancel_event

    # Queue to bridge sync generator → async SSE
    queue: Queue = Queue()

    def run_generator():
        try:
            for event in generate_conversation_stream(nami_config, scenario_config, max_turns, cancel, nami_config_name=nami):
                # Save conversation BEFORE queueing done event (avoids race with frontend reload)
                if event["type"] == "done" and event.get("conversation"):
                    try:
                        conv = Conversation(**event["conversation"])
                        save_conversation(conv, defaults.output_dir)
                        print(f"[playground] Conversa salva: {conv.id}")
                    except Exception as save_err:
                        print(f"[playground] ERRO ao salvar conversa: {save_err}", flush=True)
                        import traceback
                        traceback.print_exc()
                queue.put(event)
            queue.put(None)  # sentinel
        except Exception as e:
            print(f"[playground] ERRO no generator: {e}", flush=True)
            import traceback
            traceback.print_exc()
            queue.put({"type": "error", "message": str(e)})
            queue.put(None)

    async def event_generator():
        # Send metadata first
        yield {
            "event": "metadata",
            "data": json.dumps({
                "nami_config": nami,
                "scenario": scenario,
                "test_case": scenario_config.test_case,
                "persona": scenario_config.persona,
                "max_turns": max_turns,
                "nami_model": nami_config.model,
                "patient_model": scenario_config.model,
            }),
        }

        # Start generator in thread
        thread = threading.Thread(target=run_generator, daemon=True)
        thread.start()

        while True:
            # Poll queue without blocking event loop
            try:
                event = queue.get_nowait()
            except Empty:
                await asyncio.sleep(0.1)
                continue

            if event is None:
                break

            event_name = "error_event" if event["type"] == "error" else event["type"]
            yield {
                "event": event_name,
                "data": json.dumps(event, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@app.post("/api/conversation/stop")
async def stop_conversation():
    global _cancel_event
    if _cancel_event:
        _cancel_event.set()
        return {"status": "stopping"}
    return {"status": "no_conversation_running"}


# ── Conversation history ────────────────────────────────────────────────────


@app.get("/api/conversations")
async def list_conversations():
    defaults = _load_defaults()
    datasets_dir = Path(defaults.output_dir)
    if not datasets_dir.exists():
        return []

    conversations = []
    for p in sorted(datasets_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            conversations.append({
                "id": data.get("id", p.stem),
                "test_case": data.get("test_case", ""),
                "nami_model": data.get("metadata", {}).get("nami_model", ""),
                "nami_config_name": data.get("metadata", {}).get("nami_config_name", ""),
                "stop_reason": data.get("conversation_stop_reason", ""),
                "started_at": data.get("metadata", {}).get("started_at", ""),
                "total_turns": data.get("metadata", {}).get("total_turns", 0),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return conversations


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    defaults = _load_defaults()
    datasets_dir = Path(defaults.output_dir)
    path = datasets_dir / f"{conv_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Conversa não encontrada: {conv_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def main():
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)
