"""Trạng thái cho phép theo từng type (SPEC M3 §4.1).

Mọi đổi trạng thái — bởi luật hay người duyệt — phải nằm trong ALLOWED[type].
Change Request cần type/trạng thái mới → sửa bảng này + test, không sửa luật.
"""

from __future__ import annotations

from chot.domain.enums import ItemType as T
from chot.domain.enums import Status as S

LABEL: dict[T, dict[S, str]] = {
    T.DECISION: {
        S.FINAL: "Đã chốt",
        S.NEEDS_CONFIRMATION: "Cần xác nhận",
        S.DEFERRED: "Hoãn",
        S.REJECTED: "Bị bác",
    },
    T.OPTION: {S.SUPERSEDED: "Bị thay thế", S.OPEN: "Còn treo", S.REJECTED: "Bị bác"},
    T.TASK: {S.OPEN: "Đã nhận", S.NEEDS_CONFIRMATION: "Cần xác nhận", S.REJECTED: "Bị bác"},
    T.BLOCKER: {S.OPEN: "Đang mở"},
    T.OPEN_QUESTION: {S.OPEN: "Đang mở"},
    T.REQUEST: {S.OPEN: "Đang mở", S.NEEDS_CONFIRMATION: "Cần xác nhận", S.REJECTED: "Bị bác"},
    T.KNOWLEDGE: {S.NOTED: "Ghi nhận"},
    T.FEEDBACK: {S.NOTED: "Ghi nhận"},
}
ALLOWED: dict[T, set[S]] = {t: set(labels) for t, labels in LABEL.items()}

# Type không có trong hai bảng dưới ("—" ở SPEC): trả lời chỉ đổi review_state, giữ status.
ON_CONFIRM: dict[T, S] = {T.DECISION: S.FINAL, T.TASK: S.OPEN, T.REQUEST: S.OPEN}
ON_REJECT: dict[T, S] = {T.DECISION: S.REJECTED, T.TASK: S.REJECTED, T.REQUEST: S.REJECTED}


def check_status(item_type: T, status: S) -> None:
    if status not in ALLOWED[item_type]:
        allowed = ", ".join(sorted(ALLOWED[item_type]))
        raise ValueError(
            f"Trạng thái '{status}' không hợp lệ cho loại '{item_type}' (cho phép: {allowed})"
        )
