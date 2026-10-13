"""Baseline lọc keyword — cố tình ngây thơ, để chứng minh vì sao cần Decision Ledger.

Câu nào có "chốt / thống nhất / quyết định / đồng ý" → quyết định ĐÃ CHỐT.
Câu "<Tên> ... nhé" hoặc "em/anh/chị sẽ ..." → task ĐÃ NHẬN.
Không có khái niệm chủ đề, đổi ý, rào đón hay thẩm quyền.
"""

from __future__ import annotations

import re

from chot.domain.dates import extract_deadline_phrase, resolve_deadline
from chot.domain.enums import ItemType, Status
from chot.domain.models import Evidence, Item, Ledger, Transcript
from chot.domain.text import normalize

DECISION_KEYWORDS = ("chốt", "thống nhất", "quyết định", "đồng ý")
_SELF_TASK_RE = re.compile(r"\b(em|anh|chị|mình|tôi) sẽ\b")


class KeywordBaseline:
    name = "keyword-baseline"

    def build(self, tr: Transcript) -> Ledger:
        items: list[Item] = []
        n = {"D": 0, "T": 0}
        for u in tr.utterances:
            text = normalize(u.text)
            ev = [Evidence(utt=u.id, quote=u.text, ts=u.ts_label, speaker=u.speaker)]

            if any(k in text for k in DECISION_KEYWORDS):
                n["D"] += 1
                items.append(
                    Item(
                        id=f"D{n['D']}",
                        type=ItemType.DECISION,
                        content=u.text,
                        status=Status.FINAL,
                        decided_by=u.speaker,
                        evidence=ev,
                    )
                )
                continue

            owner = None
            first_word = u.text.split(" ", 1)[0].strip(",.")
            if first_word in tr.names and first_word != u.speaker and "nhé" in text:
                owner = first_word
            elif _SELF_TASK_RE.search(text):
                owner = u.speaker
            if owner:
                n["T"] += 1
                phrase = extract_deadline_phrase(u.text)
                items.append(
                    Item(
                        id=f"T{n['T']}",
                        type=ItemType.TASK,
                        content=u.text,
                        status=Status.OPEN,
                        owner=owner,
                        deadline=resolve_deadline(phrase, tr.date),
                        deadline_text=phrase,
                        evidence=ev,
                    )
                )
        return Ledger(meeting_id=tr.meeting_id, generated_by=self.name, items=items)
