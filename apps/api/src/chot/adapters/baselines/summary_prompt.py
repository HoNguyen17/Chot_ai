"""Baseline "1 prompt tóm tắt" — cách mà đa số tutorial / sản phẩm hiện tại đang làm.

Một lần gọi LLM: "đọc transcript, liệt kê quyết định và action items". Không có chủ đề, không có
luật trạng thái. Dùng chung client OpenAI-compatible với extractor chính để so sánh công bằng.
"""

from __future__ import annotations

import json

from chot.adapters.llm.client import LLMClient
from chot.domain.dates import resolve_deadline
from chot.domain.enums import ItemType, Status
from chot.domain.models import Evidence, Item, Ledger, Transcript

_PROMPT = """Bạn là trợ lý ghi biên bản. Đọc transcript cuộc họp dưới đây và trả về JSON:
{"decisions": [{"content": str, "utt": str}], "action_items": [{"content": str, "owner": str|null, "deadline_text": str|null, "utt": str}]}
"utt" là mã câu (vd "u012") làm bằng chứng. Chỉ trả JSON.

TRANSCRIPT:
"""


class SummaryPromptBaseline:
    name = "summary-prompt-baseline"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def build(self, tr: Transcript) -> Ledger:
        lines = "\n".join(f"{u.id} [{u.ts_label}] {u.speaker}: {u.text}" for u in tr.utterances)
        raw = self.client.complete_json(_PROMPT + lines, schema=None)
        data = json.loads(raw)
        items: list[Item] = []

        def ev(utt_id: str) -> list[Evidence]:
            u = tr.utt(utt_id)
            return [Evidence(utt=u.id, quote=u.text, ts=u.ts_label, speaker=u.speaker)] if u else []

        for i, d in enumerate(data.get("decisions", []), 1):
            items.append(
                Item(
                    id=f"D{i}",
                    type=ItemType.DECISION,
                    content=d.get("content", ""),
                    status=Status.FINAL,
                    evidence=ev(d.get("utt", "")),
                )
            )
        for i, a in enumerate(data.get("action_items", []), 1):
            items.append(
                Item(
                    id=f"T{i}",
                    type=ItemType.TASK,
                    content=a.get("content", ""),
                    status=Status.OPEN,
                    owner=a.get("owner"),
                    deadline_text=a.get("deadline_text"),
                    deadline=resolve_deadline(a.get("deadline_text"), tr.date),
                    evidence=ev(a.get("utt", "")),
                )
            )
        return Ledger(meeting_id=tr.meeting_id, generated_by=self.name, items=items)
