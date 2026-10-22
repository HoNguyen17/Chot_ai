"""Trạng thái theo type (SPEC M3 §4.1) — bảng là nguồn sự thật, CR đổi bảng chứ không đổi luật."""

import pytest

from chot.domain.enums import ItemType as T
from chot.domain.enums import Status as S
from chot.domain.status_table import ALLOWED, LABEL, ON_CONFIRM, ON_REJECT, check_status


def test_allowed_matches_spec_table():
    assert ALLOWED == {
        T.DECISION: {S.FINAL, S.NEEDS_CONFIRMATION, S.DEFERRED, S.REJECTED},
        T.OPTION: {S.SUPERSEDED, S.OPEN, S.REJECTED},
        T.TASK: {S.OPEN, S.NEEDS_CONFIRMATION, S.REJECTED},
        T.BLOCKER: {S.OPEN},
        T.OPEN_QUESTION: {S.OPEN},
        T.REQUEST: {S.OPEN, S.NEEDS_CONFIRMATION, S.REJECTED},
        T.KNOWLEDGE: {S.NOTED},
        T.FEEDBACK: {S.NOTED},
    }


def test_confirm_and_reject_targets_match_spec():
    assert ON_CONFIRM == {T.DECISION: S.FINAL, T.TASK: S.OPEN, T.REQUEST: S.OPEN}
    assert ON_REJECT == {T.DECISION: S.REJECTED, T.TASK: S.REJECTED, T.REQUEST: S.REJECTED}


def test_ui_labels_follow_type():
    assert LABEL[T.TASK][S.OPEN] == "Đã nhận"
    assert LABEL[T.REQUEST][S.OPEN] == "Đang mở"
    assert LABEL[T.OPTION][S.OPEN] == "Còn treo"
    assert LABEL[T.KNOWLEDGE][S.NOTED] == "Ghi nhận"
    assert all(set(LABEL[t]) == ALLOWED[t] for t in T)


def test_status_outside_table_is_rejected():
    with pytest.raises(ValueError, match="không hợp lệ"):
        check_status(T.KNOWLEDGE, S.FINAL)
    check_status(T.DECISION, S.FINAL)  # hợp lệ → không lỗi


def test_item_carries_ui_label_for_api():
    from chot.domain.models import Item

    task = Item(id="T1", type=T.TASK, content="x", status=S.OPEN)
    note = Item(id="K1", type=T.KNOWLEDGE, content="x", status=S.NOTED)
    assert task.model_dump()["status_label"] == "Đã nhận"
    assert note.model_dump()["status_label"] == "Ghi nhận"
    assert Item(**task.model_dump()) == task  # đọc lại (Postgres / JSON) không vỡ
