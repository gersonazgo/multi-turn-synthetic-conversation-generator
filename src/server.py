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
from .models import AssistantConfig, Conversation, Defaults, ScenarioConfig

app = FastAPI(title="Conversation Playground")

CONFIG_DIR = Path("config")
ASSISTANT_DIR = CONFIG_DIR / "assistant"
USER_DIR = CONFIG_DIR / "user"
BACKUPS_DIR = CONFIG_DIR / "backups"
WEB_DIR = Path(__file__).parent / "web"

# State for cancel support
_cancel_event: threading.Event | None = None


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


# ── Static ──────────────────────────────────────────────────────────────────


@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "index.html")


# ── Config endpoints ────────────────────────────────────────────────────────


@app.get("/api/configs/assistant")
async def list_assistant_configs():
    if not ASSISTANT_DIR.exists():
        return []
    return [p.stem for p in sorted(ASSISTANT_DIR.glob("*.yml"))]


@app.get("/api/configs/user")
async def list_scenario_configs():
    if not USER_DIR.exists():
        return []
    configs = []
    for p in sorted(USER_DIR.glob("*.yml")):
        data = _load_yaml(p)
        configs.append({
            "name": p.stem,
            "test_case": data.get("test_case", p.stem),
            "scenario": data.get("scenario", ""),
        })
    return configs


@app.get("/api/configs/assistant/{name}")
async def get_assistant_config(name: str):
    path = ASSISTANT_DIR / f"{name}.yml"
    if not path.exists():
        raise HTTPException(404, f"Config not found: {name}")
    return JSONResponse({"name": name, "content": path.read_text(encoding="utf-8")})


@app.put("/api/configs/assistant/{name}")
async def save_assistant_config(name: str, request: Request):
    body = await request.json()
    content = body.get("content", "")
    if not content.strip():
        raise HTTPException(400, "Empty content")

    # Validate YAML
    try:
        parsed = yaml.safe_load(content)
        AssistantConfig(**parsed)
    except Exception as e:
        raise HTTPException(400, f"Invalid YAML: {e}")

    path = ASSISTANT_DIR / f"{name}.yml"

    # Backup if file exists
    if path.exists():
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        defaults = _load_defaults()
        tz = _parse_timezone(defaults.timezone)
        timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUPS_DIR / f"{name}_{timestamp}.yml"
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    path.write_text(content, encoding="utf-8")
    return {"status": "saved", "name": name}


@app.get("/api/configs/assistant/{name}/prompt")
async def get_assistant_prompt(name: str):
    path = ASSISTANT_DIR / f"{name}.yml"
    if not path.exists():
        raise HTTPException(404, f"Config not found: {name}")
    data = _load_yaml(path)
    config = AssistantConfig(**data)
    return JSONResponse({
        "model": config.model,
        "temperature": config.temperature,
        "system_prompt": config.system_prompt,
    })


@app.put("/api/configs/assistant/{name}/prompt")
async def save_assistant_prompt(name: str, request: Request):
    body = await request.json()
    system_prompt = body.get("system_prompt", "")
    if not system_prompt.strip():
        raise HTTPException(400, "Empty system_prompt")

    path = ASSISTANT_DIR / f"{name}.yml"
    if not path.exists():
        raise HTTPException(404, f"Config not found: {name}")

    # Load existing config to preserve model/temperature
    data = _load_yaml(path)
    data["system_prompt"] = system_prompt

    # Validate
    try:
        AssistantConfig(**data)
    except Exception as e:
        raise HTTPException(400, f"Invalid config: {e}")

    # Backup
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    defaults = _load_defaults()
    tz = _parse_timezone(defaults.timezone)
    timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUPS_DIR / f"{name}_{timestamp}.yml"
    backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    # Write back preserving block scalar style for system_prompt
    class _BlockDumper(yaml.SafeDumper):
        pass

    def _str_representer(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    _BlockDumper.add_representer(str, _str_representer)

    path.write_text(
        yaml.dump(data, Dumper=_BlockDumper, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return {"status": "saved", "name": name}


# ── Conversation stream ────────────────────────────────────────────────────


@app.get("/api/conversation/stream")
async def conversation_stream(assistant: str, scenario: str):
    global _cancel_event

    assistant_path = ASSISTANT_DIR / f"{assistant}.yml"
    scenario_path = USER_DIR / f"{scenario}.yml"

    if not assistant_path.exists():
        raise HTTPException(404, f"Assistant config not found: {assistant}")
    if not scenario_path.exists():
        raise HTTPException(404, f"Scenario not found: {scenario}")

    assistant_config = AssistantConfig(**_load_yaml(assistant_path))
    scenario_config = ScenarioConfig(**_load_yaml(scenario_path))
    defaults = _load_defaults()
    max_turns = scenario_config.max_turns or defaults.max_turns
    tz = _parse_timezone(defaults.timezone)

    _cancel_event = threading.Event()
    cancel = _cancel_event

    # Queue to bridge sync generator → async SSE
    queue: Queue = Queue()

    def run_generator():
        try:
            for event in generate_conversation_stream(
                assistant_config, scenario_config, max_turns, cancel,
                assistant_config_name=assistant, stop_phrase=defaults.stop_phrase, tz=tz,
            ):
                # Save conversation BEFORE queueing done event (avoids race with frontend reload)
                if event["type"] == "done" and event.get("conversation"):
                    try:
                        conv = Conversation(**event["conversation"])
                        save_conversation(conv, defaults.output_dir)
                        print(f"[playground] Conversation saved: {conv.id}")
                    except Exception as save_err:
                        print(f"[playground] ERROR saving conversation: {save_err}", flush=True)
                        import traceback
                        traceback.print_exc()
                queue.put(event)
            queue.put(None)  # sentinel
        except Exception as e:
            print(f"[playground] ERROR in generator: {e}", flush=True)
            import traceback
            traceback.print_exc()
            queue.put({"type": "error", "message": str(e)})
            queue.put(None)

    async def event_generator():
        # Send metadata first
        yield {
            "event": "metadata",
            "data": json.dumps({
                "assistant_config": assistant,
                "scenario": scenario,
                "test_case": scenario_config.test_case,
                "persona": scenario_config.persona,
                "max_turns": max_turns,
                "assistant_model": assistant_config.model,
                "user_model": scenario_config.model,
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
            meta = data.get("metadata", {})
            conversations.append({
                "id": data.get("id", p.stem),
                "test_case": data.get("test_case", ""),
                "assistant_model": meta.get("assistant_model", meta.get("nami_model", "")),
                "assistant_config_name": meta.get("assistant_config_name", meta.get("nami_config_name", "")),
                "stop_reason": data.get("conversation_stop_reason", ""),
                "started_at": meta.get("started_at", ""),
                "total_turns": meta.get("total_turns", 0),
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
        raise HTTPException(404, f"Conversation not found: {conv_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def main():
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)
