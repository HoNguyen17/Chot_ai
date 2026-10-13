"""Bước AI duy nhất trong pipeline v1: tách chủ đề + gán nhãn sự kiện cho từng câu.

LLM KHÔNG quyết định trạng thái cuối. Nó chỉ trả lời "câu này là đề xuất / phản đối / đồng ý /
giao việc… thuộc chủ đề nào". Trạng thái do chot.domain.status_rules suy ra.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from chot.adapters.llm.client import LLMClient
from chot.domain.enums import EventKind
from chot.domain.models import Event, ExtractionResult, Thread, Transcript

_NULLABLE_STR = {"type": ["string", "null"]}

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["threads", "events"],
    "properties": {
        "threads": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title"],
                "properties": {"id": {"type": "string"}, "title": {"type": "string"}},
            },
        },
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "utt",
                    "thread",
                    "kind",
                    "speaker",
                    "key",
                    "content",
                    "hedged",
                    "owner",
                    "deadline_text",
                    "quote",
                ],
                "properties": {
                    "utt": {"type": "string"},
                    "thread": {"type": "string"},
                    "kind": {"type": "string", "enum": [k.value for k in EventKind]},
                    "speaker": {"type": "string"},
                    "key": _NULLABLE_STR,
                    "content": {"type": "string"},
                    "hedged": {"type": "boolean"},
                    "owner": _NULLABLE_STR,
                    "deadline_text": _NULLABLE_STR,
                    "quote": {"type": "string"},
                },
            },
        },
    },
}


def load_prompt(name: str) -> str:
    return resources.files("chot.prompts").joinpath(f"{name}.md").read_text(encoding="utf-8")


def render_transcript(tr: Transcript) -> str:
    people = "\n".join(
        f"- {p.name}" + (f" ({p.role})" if p.role else "") + (" — CHỦ TRÌ" if p.is_chair else "")
        for p in tr.participants
    )
    absent = ", ".join(p.name for p in tr.absent) or "không"
    lines = "\n".join(f"{u.id} [{u.ts_label}] {u.speaker}: {u.text}" for u in tr.utterances)
    return (
        f"Tiêu đề: {tr.title or '-'}\nNgày họp: {tr.date or '-'}\n"
        f"Người tham gia:\n{people}\nVắng mặt: {absent}\n\nTRANSCRIPT:\n{lines}"
    )


class LLMEventExtractor:
    name = "llm-events"

    def __init__(self, client: LLMClient, prompt_name: str = "extract_events") -> None:
        self.client = client
        self.prompt_template = load_prompt(prompt_name)

    def extract(self, tr: Transcript) -> ExtractionResult:
        prompt = self.prompt_template.replace("{{TRANSCRIPT}}", render_transcript(tr))
        raw = self.client.complete_json(prompt, schema=EXTRACTION_SCHEMA)
        data = json.loads(raw)
        events = []
        for e in data.get("events", []):
            try:
                events.append(Event.model_validate(e))
            except ValueError:
                continue  # bỏ sự kiện sai schema thay vì làm hỏng cả cuộc họp
        return ExtractionResult(
            threads=[Thread.model_validate(t) for t in data.get("threads", [])],
            events=events,
        )
