"""Duyệt một mục (SPEC M3 §4.4) — thuần, không I/O.

Người duyệt chỉ trả lời Xác nhận / Bác bỏ / để họp sau. Trạng thái mới lấy từ bảng
ON_CONFIRM / ON_REJECT của type (luật vàng #1: không ai tự gõ trạng thái).
"""

from __future__ import annotations

import datetime as dt

from chot.domain.enums import ItemType, ReviewAction, ReviewState, Status
from chot.domain.models import Evidence, Item
from chot.domain.reasons import ReasonCode as C
from chot.domain.status_table import ON_CONFIRM, ON_REJECT, check_status

_ANSWER = {  # hành động → (review_state, ghi chú trên bằng chứng người duyệt)
    ReviewAction.CONFIRM: (ReviewState.CONFIRMED, "Xác nhận"),
    ReviewAction.REJECT: (ReviewState.REJECTED, "Bác bỏ"),
    ReviewAction.DEFER: (ReviewState.DEFERRED, "Để họp sau"),
}


def initial_review_state(item: Item) -> ReviewState:
    """Có mã hỏi → chờ trả lời. needs_confirmation không mã (grounding hạ cấp) cũng phải hỏi."""
    if item.status == Status.NEEDS_CONFIRMATION or any(r.asking for r in item.reasons):
        return ReviewState.PENDING
    return ReviewState.AUTO_ACCEPTED


def _require_answers(
    item: Item, owner: str | None, deadline: dt.date | None, thread: str | None
) -> None:
    codes = {r.code for r in item.reasons}
    if C.OWNER_MISSING in codes and not (owner or item.owner):
        raise ValueError("Cần chọn người làm trước khi xác nhận")
    if C.DEADLINE_VAGUE in codes and not (deadline or item.deadline):
        raise ValueError("Cần chọn ngày hạn chót trước khi xác nhận")
    if C.THREAD_UNMAPPED in codes and not thread:
        raise ValueError("Cần chọn chủ đề trước khi xác nhận")


def apply_answer(
    item: Item,
    action: ReviewAction,
    *,
    owner: str | None = None,
    deadline: dt.date | None = None,
    thread: str | None = None,
    by: str = "reviewer",
    at: dt.datetime | None = None,
) -> Item:
    state, note = _ANSWER[action]
    update: dict = {"review_state": state}
    if action == ReviewAction.CONFIRM:
        _require_answers(item, owner, deadline, thread)
        update["status"] = ON_CONFIRM.get(item.type, item.status)
        # người / ngày / chủ đề chỉ áp khi xác nhận (câu trả lời cho mã hỏi tương ứng)
        for field, value in (("owner", owner), ("deadline", deadline), ("thread", thread)):
            if value:
                update[field] = value
    elif action == ReviewAction.REJECT:
        update["status"] = ON_REJECT.get(item.type, item.status)
        if item.type == ItemType.KNOWLEDGE:
            update["scope"] = "meeting"  # bác bỏ = chỉ giữ trong buổi họp, không vào Kho
    elif item.type == ItemType.DECISION:
        update["status"] = Status.DEFERRED
    check_status(item.type, update.get("status", item.status))
    reviewer = Evidence(kind="reviewer", by=by, at=at or dt.datetime.now(dt.UTC), note=note)
    update["evidence"] = [*item.evidence, reviewer]
    return item.model_copy(update=update)
