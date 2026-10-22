"""Lượt 1 của extractor M3: bản đồ chủ đề cho cả cuộc họp — không sự kiện, không trạng thái."""

from __future__ import annotations

import json
from typing import Any

from chot.adapters.llm.client import LLMClient
from chot.adapters.llm.event_extractor import load_prompt, render_transcript
from chot.domain.models import Thread, Transcript

_STRS = {"type": "array", "items": {"type": "string"}}

TOPIC_MAP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["threads"],
    "properties": {
        "threads": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title", "keys", "utt_ids"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "keys": _STRS,
                    "utt_ids": _STRS,
                },
            },
        }
    },
}


class LLMTopicMapper:
    def __init__(self, client: LLMClient, prompt_name: str = "map_topics") -> None:
        self.client = client
        self.prompt_template = load_prompt(prompt_name)

    def map(self, tr: Transcript) -> list[Thread]:
        prompt = self.prompt_template.replace("{{TRANSCRIPT}}", render_transcript(tr))
        data = json.loads(self.client.complete_json(prompt, schema=TOPIC_MAP_SCHEMA))
        return [Thread.model_validate(t) for t in data.get("threads", [])]
