from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .models import Conversation

BRT = timezone(timedelta(hours=-3))


def _format_timestamp(ts: str | None) -> str:
    if not ts:
        return "—"
    dt = datetime.fromisoformat(ts).astimezone(BRT)
    return dt.strftime("%d/%m/%Y %H:%M:%S")


STOP_REASON_LABELS = {
    "turns_ended": "Limite de turnos atingido",
    "nami_succeeded": "NAMI teve sucesso",
}


def save_conversation(conversation: Conversation, output_dir: str) -> tuple[Path, Path]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    base = conversation.id

    # JSON
    json_path = path / f"{base}.json"
    json_path.write_text(
        json.dumps(conversation.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # DOCX
    docx_path = path / f"{base}.docx"
    _save_docx(conversation, docx_path)

    return json_path, docx_path


def _add_header_field(doc: Document, label: str, value: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(0)
    run_label = p.add_run(f"{label}: ")
    run_label.bold = True
    run_label.font.size = Pt(10)
    run_label.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    run_value = p.add_run(value)
    run_value.font.size = Pt(10)


def _save_docx(conversation: Conversation, filepath: Path) -> None:
    doc = Document()

    # Título
    title = doc.add_heading(f"Conversa: {conversation.test_case}", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Header com metadata
    meta = conversation.metadata
    stop_label = STOP_REASON_LABELS.get(
        conversation.conversation_stop_reason, conversation.conversation_stop_reason
    )

    _add_header_field(doc, "Capability", conversation.capability)
    _add_header_field(doc, "Test Case", conversation.test_case)
    _add_header_field(doc, "Cenário", conversation.scenario)
    _add_header_field(doc, "Persona", conversation.persona)
    _add_header_field(doc, "Colaboração", conversation.collaboration)
    _add_header_field(doc, "Modelo NAMI", meta.nami_model)
    _add_header_field(doc, "Temperatura NAMI", str(meta.nami_temperature))
    _add_header_field(doc, "Modelo Paciente", meta.patient_model)
    _add_header_field(doc, "Temperatura Paciente", str(meta.patient_temperature))
    _add_header_field(doc, "Total de turnos", str(meta.total_turns))
    _add_header_field(doc, "Resultado", stop_label)
    _add_header_field(doc, "Início", _format_timestamp(meta.started_at))
    _add_header_field(doc, "Fim", _format_timestamp(meta.finished_at))

    # Separador
    doc.add_paragraph("─" * 50)

    # Mensagens
    for msg in conversation.messages:
        speaker = conversation.persona if msg.role == "patient" else "Nami"
        color = RGBColor(0x1A, 0x73, 0xE8) if msg.role == "patient" else RGBColor(0x1E, 0x88, 0x50)

        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(8)

        run_name = p.add_run(f"{speaker}: ")
        run_name.bold = True
        run_name.font.size = Pt(11)
        run_name.font.color.rgb = color

        run_content = p.add_run(msg.content)
        run_content.font.size = Pt(11)

    doc.save(str(filepath))
