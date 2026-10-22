"""Bước AI gán nhãn sự kiện cho từng câu (lượt 2 của extractor M3).

LLM KHÔNG quyết định trạng thái cuối. Nó chỉ trả lời "câu này là đề xuất / phản đối / đồng ý /
giao việc… thuộc chủ đề nào". Trạng thái do chot.domain.status_rules suy ra.

Hai chế độ: `extract` — cả transcript 1 lần gọi (họp ngắn, như M2); `extract_chunk` — một đoạn,
có bản đồ chủ đề của lượt 1 và câu ngữ cảnh CHỈ ĐỌC.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from chot.adapters.llm.client import LLMClient
from chot.domain.chunking import Chunk
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
                    "durable_hint",
                    "new_key",
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
                    "durable_hint": {"type": "boolean"},
                    "new_key": {"type": "boolean"},
                },
            },
        },
    },
}

NO_MAP = "Không có bản đồ — tự tách chủ đề theo mục 1."


def load_prompt(name: str) -> str:
    return resources.files("chot.prompts").joinpath(f"{name}.md").read_text(encoding="utf-8")


def render_transcript(tr: Transcript, chunk: Chunk | None = None) -> str:
    """Header + các câu. Có `chunk` → chỉ câu ngữ cảnh (gắn [CHỈ ĐỌC]) và câu cần gán nhãn."""
    people = "\n".join(
        f"- {p.name}" + (f" ({p.role})" if p.role else "") + (" — CHỦ TRÌ" if p.is_chair else "")
        for p in tr.participants
    )
    absent = ", ".join(p.name for p in tr.absent) or "không"
    shown = None if chunk is None else {*chunk.label_ids, *chunk.context_ids}
    lines = "\n".join(
        ("[CHỈ ĐỌC] " if chunk and u.id in chunk.context_ids else "")
        + f"{u.id} [{u.ts_label}] {u.speaker}: {u.text}"
        for u in tr.utterances
        if shown is None or u.id in shown
    )
    return (
        f"Tiêu đề: {tr.title or '-'}\nNgày họp: {tr.date or '-'}\n"
        f"Người tham gia:\n{people}\nVắng mặt: {absent}\n\nTRANSCRIPT:\n{lines}"
    )


def _spans(utt_ids: list[str], gap: int = 5) -> str:
    """["u010","u012","u101"] → "u010–u012, u101": thấy chủ đề quay lại ở đoạn sau."""
    nums = sorted({int(u[1:]) for u in utt_ids if u[1:].isdigit()})
    spans: list[list[int]] = []
    for n in nums:
        if spans and n - spans[-1][1] <= gap:
            spans[-1][1] = n
        else:
            spans.append([n, n])
    return ", ".join(f"u{a:03d}" + (f"–u{b:03d}" if b > a else "") for a, b in spans)


def render_topic_map(threads: list[Thread]) -> str:
    """Mỗi chủ đề 1 dòng: id, tiêu đề, dải câu, key — để lượt 2 dùng đúng nguyên văn."""
    return "\n".join(
        f"- `{t.id}` — {t.title}"
        + (f" (câu {_spans(t.utt_ids)})" if t.utt_ids else "")
        + f"; keys: {', '.join(f'`{k}`' for k in t.keys) or '(chưa có)'}"
        for t in threads
    )


class LLMEventExtractor:
    name = "llm-events"

    def __init__(self, client: LLMClient, prompt_name: str = "extract_events") -> None:
        self.client = client
        self.prompt_template = load_prompt(prompt_name)

    def extract(self, tr: Transcript) -> ExtractionResult:
        return self._call(NO_MAP, render_transcript(tr))

    def extract_chunk(
        self, tr: Transcript, threads: list[Thread], chunk: Chunk
    ) -> ExtractionResult:
        return self._call(render_topic_map(threads), render_transcript(tr, chunk))

    def _call(self, topic_map: str, transcript: str) -> ExtractionResult:
        prompt = self.prompt_template.replace("{{TOPIC_MAP}}", topic_map).replace(
            "{{TRANSCRIPT}}", transcript
        )
        data = json.loads(self.client.complete_json(prompt, schema=EXTRACTION_SCHEMA))
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
