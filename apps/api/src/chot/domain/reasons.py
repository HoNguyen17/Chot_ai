"""Mã lý do (SPEC M3 §4.2) thay cho flag chữ tự do.

Mỗi mã có hai cách hiển thị: câu HỎI cho người duyệt (chỉ mã thuộc ASKING) và FLAG ngắn
(giữ đúng chữ M2 để export .md/.csv/.json cũ không đổi). Chữ sinh từ mã + tham số, luật chỉ trả mã.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ReasonCode(StrEnum):
    # Mã hỏi: mục vào hàng đợi "Cần bạn trả lời"
    NOT_CHAIR = "NOT_CHAIR"
    HEDGED = "HEDGED"
    NOD_ONLY = "NOD_ONLY"
    CO_CHAIR_OBJECTION = "CO_CHAIR_OBJECTION"
    OWNER_MISSING = "OWNER_MISSING"
    OWNER_UNCONFIRMED = "OWNER_UNCONFIRMED"
    OWNER_DECLINED = "OWNER_DECLINED"
    OWNER_ABSENT = "OWNER_ABSENT"
    DEADLINE_VAGUE = "DEADLINE_VAGUE"
    DURABLE_KNOWLEDGE = "DURABLE_KNOWLEDGE"
    THREAD_UNMAPPED = "THREAD_UNMAPPED"
    # Mã thông tin: hiển thị trên mục, không chặn xuất bản
    FALLBACK_KEPT = "FALLBACK_KEPT"
    CHANGED_MIND = "CHANGED_MIND"
    NO_AGREEMENT = "NO_AGREEMENT"
    AGREEMENT_REVERSED = "AGREEMENT_REVERSED"


C = ReasonCode

_QUESTION = {
    C.NOT_CHAIR: "{chair} đã chốt {key} chưa?",
    C.HEDGED: "{speaker} nói '{quote}'. Đã chốt {key} chưa?",
    C.NOD_ONLY: "{chair} chỉ đáp 'Ừ.' sau đề xuất {key}. Đã chốt chưa?",
    C.CO_CHAIR_OBJECTION: (
        "{chair} chốt {key} nhưng {co_chair} đã phản đối và chưa đồng ý lại. Đã chốt chưa?"
    ),
    C.OWNER_MISSING: "Ai làm '{content}'?",
    C.OWNER_UNCONFIRMED: "{owner} đã nhận '{content}' chưa?",
    C.OWNER_DECLINED: "{owner} trì hoãn '{content}'. Vẫn giao cho {owner}?",
    C.OWNER_ABSENT: "{owner} vắng họp. Đã nhận '{content}' chưa?",
    C.DEADLINE_VAGUE: "Hạn '{deadline_text}' là ngày nào?",
    C.DURABLE_KNOWLEDGE: "Lưu vào Kho tri thức: '{content}'?",
    C.THREAD_UNMAPPED: "Mục này thuộc chủ đề nào?",
}
ASKING = frozenset(_QUESTION)

_FLAG = {
    C.NOT_CHAIR: "người đồng ý không phải người chủ trì",
    C.HEDGED: "đồng thuận có rào đón",
    C.NOD_ONLY: "chủ trì chỉ đáp 'Ừ.' — đồng ý gián tiếp, cần xác nhận",
    C.CO_CHAIR_OBJECTION: "đồng chủ trì {co_chair} đã phản đối, chưa đồng ý lại",
    C.OWNER_MISSING: "chưa rõ ai nhận việc",
    C.OWNER_UNCONFIRMED: "owner chưa xác nhận nhận việc",
    C.OWNER_DECLINED: "owner từ chối hoặc trì hoãn",
    C.OWNER_ABSENT: "owner '{owner}' vắng mặt — cần xác nhận lại với người đó",
    C.DEADLINE_VAGUE: "hạn chót chưa cụ thể",
    C.DURABLE_KNOWLEDGE: "tri thức dùng lâu dài — cần xác nhận trước khi vào Kho",
    C.THREAD_UNMAPPED: "chưa gắn được chủ đề",
    C.FALLBACK_KEPT: "có điều kiện quay lại phương án cũ — phương án cũ vẫn mở",
    C.CHANGED_MIND: "đã đổi ý trong cuộc họp — xem timeline",
    C.NO_AGREEMENT: "chưa có đồng thuận",
    C.AGREEMENT_REVERSED: "đã có đồng thuận nhưng bị lật lại",
}
_HEARSAY_WARNING = " Câu gốc có rào đón (nghe nói / chắc là) — kiểm tra lại trước khi lưu."


class Reason(BaseModel):
    code: ReasonCode
    params: dict[str, str | bool | None] = Field(default_factory=dict)

    @property
    def asking(self) -> bool:
        return self.code in ASKING


def question(r: Reason) -> str | None:
    """Câu hỏi cho người duyệt; mã thông tin → None."""
    if r.code not in ASKING:
        return None
    text = _QUESTION[r.code].format(**r.params)
    return text + _HEARSAY_WARNING if r.params.get("hearsay") else text


def flag(r: Reason) -> str:
    """Chữ ngắn kiểu M2 (field `flags` của API/export cũ)."""
    if r.code == C.OWNER_MISSING and r.params.get("name"):  # M2 tách 2 câu cho ca này
        return f"owner '{r.params['name']}' không có trong danh sách người tham gia"
    return _FLAG[r.code].format(**r.params)
