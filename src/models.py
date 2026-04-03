from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class NamiConfig(BaseModel):
    model: str
    temperature: float = 0.7
    system_prompt: str


class ScenarioConfig(BaseModel):
    capability: str = ""
    test_case: str
    scenario: str
    persona: str
    collaboration: str = ""
    model: str
    temperature: float = 0.8
    system_prompt: str
    first_message: str
    max_turns: Optional[int] = None


class BatchConfig(BaseModel):
    conversation_rounds: int = 1
    scenarios: list[str] = []


class Defaults(BaseModel):
    max_turns: int = 12
    delay: float = 0
    output_dir: str = "datasets"


class Message(BaseModel):
    role: str  # "patient" | "nami"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConversationMetadata(BaseModel):
    nami_model: str
    nami_temperature: float
    patient_model: str
    patient_temperature: float
    nami_config_name: str = ""
    total_turns: int = 0
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None


class Conversation(BaseModel):
    id: str
    capability: str = ""
    test_case: str
    scenario: str
    persona: str
    collaboration: str = ""
    conversation_stop_reason: str = "turns_ended"
    # "turns_ended" | "nami_succeeded" | "role_swap_error" | "llm_transient_error" | "llm_content_error" | "llm_non_transient_error"
    messages: list[Message] = []
    metadata: ConversationMetadata
