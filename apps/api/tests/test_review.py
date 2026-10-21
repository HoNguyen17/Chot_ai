"""Duyệt (SPEC M3 §4.4): tự chấp nhận mục không có câu hỏi; trả lời chỉ đổi trạng thái theo bảng."""

import datetime as dt

import pytest

from chot.domain.enums import ItemType as T
from chot.domain.enums import ReviewAction as A
from chot.domain.enums import ReviewState as RS
from chot.domain.enums import Status as S
from chot.domain.models import Evidence, Item
from chot.domain.reasons import Reason
from chot.domain.reasons import ReasonCode as C
from chot.domain.review import apply_answer, initial_review_state


def item(type_, status, *codes, **kw):
    return Item(
        id="X1",
        type=type_,
        content="nội dung",
        status=status,
        evidence=[Evidence(utt="u001", quote="câu")],
        reasons=[Reason(code=c) for c in codes],
        **kw,
    )


@pytest.mark.parametrize(
    ("it", "expected"),
    [
        (item(T.DECISION, S.FINAL), RS.AUTO_ACCEPTED),
        (item(T.DECISION, S.FINAL, C.FALLBACK_KEPT, C.CHANGED_MIND), RS.AUTO_ACCEPTED),
        (item(T.OPEN_QUESTION, S.OPEN, C.NO_AGREEMENT), RS.AUTO_ACCEPTED),
        (item(T.DECISION, S.NEEDS_CONFIRMATION, C.HEDGED), RS.PENDING),
        (item(T.TASK, S.OPEN, C.DEADLINE_VAGUE), RS.PENDING),
        (item(T.KNOWLEDGE, S.NOTED, C.DURABLE_KNOWLEDGE, scope="durable"), RS.PENDING),
        # grounding hạ final → needs_confirmation mà không có mã: vẫn phải hỏi
        (item(T.DECISION, S.NEEDS_CONFIRMATION), RS.PENDING),
    ],
)
def test_initial_review_state(it, expected):
    assert initial_review_state(it) == expected


@pytest.mark.parametrize(
    ("type_", "start", "action", "status", "state"),
    [
        (T.DECISION, S.NEEDS_CONFIRMATION, A.CONFIRM, S.FINAL, RS.CONFIRMED),
        (T.DECISION, S.NEEDS_CONFIRMATION, A.REJECT, S.REJECTED, RS.REJECTED),
        (T.DECISION, S.NEEDS_CONFIRMATION, A.DEFER, S.DEFERRED, RS.DEFERRED),
        (T.TASK, S.NEEDS_CONFIRMATION, A.CONFIRM, S.OPEN, RS.CONFIRMED),
        (T.TASK, S.NEEDS_CONFIRMATION, A.REJECT, S.REJECTED, RS.REJECTED),
        (T.TASK, S.NEEDS_CONFIRMATION, A.DEFER, S.NEEDS_CONFIRMATION, RS.DEFERRED),
        (T.REQUEST, S.NEEDS_CONFIRMATION, A.CONFIRM, S.OPEN, RS.CONFIRMED),
        (T.REQUEST, S.OPEN, A.REJECT, S.REJECTED, RS.REJECTED),
        # type có "—" trong bảng: chỉ đổi review_state
        (T.BLOCKER, S.OPEN, A.CONFIRM, S.OPEN, RS.CONFIRMED),
        (T.OPTION, S.OPEN, A.REJECT, S.OPEN, RS.REJECTED),
    ],
)
def test_answer_follows_status_table(type_, start, action, status, state):
    out = apply_answer(item(type_, start, C.THREAD_UNMAPPED), action, thread="t")
    assert (out.status, out.review_state) == (status, state)


def test_confirm_durable_knowledge_keeps_noted_and_durable():
    k = item(T.KNOWLEDGE, S.NOTED, C.DURABLE_KNOWLEDGE, scope="durable")
    out = apply_answer(k, A.CONFIRM)
    assert (out.status, out.scope, out.review_state) == (S.NOTED, "durable", RS.CONFIRMED)


def test_reject_durable_knowledge_keeps_it_in_meeting_only():
    k = item(T.KNOWLEDGE, S.NOTED, C.DURABLE_KNOWLEDGE, scope="durable")
    out = apply_answer(k, A.REJECT)
    assert (out.status, out.scope, out.review_state) == (S.NOTED, "meeting", RS.REJECTED)


def test_confirm_task_without_owner_requires_choosing_one():
    t = item(T.TASK, S.NEEDS_CONFIRMATION, C.OWNER_MISSING)
    with pytest.raises(ValueError, match="người"):
        apply_answer(t, A.CONFIRM)
    out = apply_answer(t, A.CONFIRM, owner="Mi")
    assert (out.status, out.owner) == (S.OPEN, "Mi")


def test_confirm_vague_deadline_requires_a_date():
    t = item(T.TASK, S.OPEN, C.DEADLINE_VAGUE, owner="Mi")
    with pytest.raises(ValueError, match="ngày"):
        apply_answer(t, A.CONFIRM)
    assert apply_answer(t, A.CONFIRM, deadline=dt.date(2026, 11, 6)).deadline == dt.date(
        2026, 11, 6
    )


def test_confirm_unmapped_thread_requires_a_thread():
    b = item(T.BLOCKER, S.OPEN, C.THREAD_UNMAPPED)
    with pytest.raises(ValueError, match="chủ đề"):
        apply_answer(b, A.CONFIRM)
    assert apply_answer(b, A.CONFIRM, thread="tet-shipping").thread == "tet-shipping"


def test_answer_adds_reviewer_evidence_separate_from_transcript():
    at = dt.datetime(2026, 11, 2, 9, 0, tzinfo=dt.UTC)
    out = apply_answer(
        item(T.DECISION, S.NEEDS_CONFIRMATION, C.NOD_ONLY), A.CONFIRM, by="Nash", at=at
    )
    assert [e.kind for e in out.evidence] == ["transcript", "reviewer"]
    rev = out.evidence[-1]
    assert (rev.by, rev.at, rev.utt) == ("Nash", at, None)
