"""Grounding 2 tầng — "không có bằng chứng hợp lệ thì không xuất".

Tầng 1 (có thật): trích dẫn phải nằm nguyên văn trong câu nói được trỏ tới. Sai → bỏ bằng chứng;
             mục không còn bằng chứng nào → bị loại khỏi Ledger.
Tầng 2 (đúng ngữ cảnh): bằng chứng phải chứng minh đúng loại mục. Vi phạm → hạ FINAL xuống
             NEEDS_CONFIRMATION, gắn cờ cho người duyệt.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from chot.domain.enums import ItemType, Status
from chot.domain.models import Item, Ledger, Transcript
from chot.domain.text import is_hedged, normalize


class GroundingReport(BaseModel):
    quotes_total: int = 0
    quotes_valid: int = 0
    items_dropped: list[str] = Field(default_factory=list)
    items_downgraded: list[str] = Field(default_factory=list)

    @property
    def tier1_rate(self) -> float:
        return self.quotes_valid / self.quotes_total if self.quotes_total else 1.0


def quote_in_utterance(quote: str, utt_text: str) -> bool:
    q = normalize(quote)
    return bool(q) and q in normalize(utt_text)


def _tier2_violation(item: Item, tr: Transcript) -> str | None:
    if item.type == ItemType.DECISION and item.status == Status.FINAL:
        if item.decided_by not in tr.chairs:
            return "quyết định đã chốt nhưng người chốt không phải chủ trì"
        latest = max(item.evidence, key=lambda ev: tr.order(ev.utt))
        u = tr.utt(latest.utt)
        if u is None or u.speaker != item.decided_by:
            return "bằng chứng mới nhất không phải câu của người chốt"
        if is_hedged(latest.quote):
            return "câu chốt có rào đón"
    if item.owner and item.owner not in tr.names:
        return "owner không có trong danh sách người tham gia"
    if item.decided_by and item.decided_by not in tr.names:
        return "người quyết định không có trong danh sách người tham gia"
    return None


def apply_grounding(ledger: Ledger, tr: Transcript) -> tuple[Ledger, GroundingReport]:
    report = GroundingReport()
    kept: list[Item] = []
    for item in ledger.items:
        valid = []
        for ev in item.evidence:
            report.quotes_total += 1
            u = tr.utt(ev.utt)
            if u and quote_in_utterance(ev.quote, u.text):
                report.quotes_valid += 1
                valid.append(ev)
        if not valid:
            report.items_dropped.append(item.id)
            continue
        item = item.model_copy(update={"evidence": valid})

        reason = _tier2_violation(item, tr)
        if reason:
            update: dict = {"flags": [*item.flags, f"grounding: {reason}"]}
            if item.status == Status.FINAL:
                update["status"] = Status.NEEDS_CONFIRMATION
                report.items_downgraded.append(item.id)
            if item.owner and item.owner not in tr.names:
                update["owner"] = None
            item = item.model_copy(update=update)
        kept.append(item)

    return ledger.model_copy(update={"items": kept}), report
