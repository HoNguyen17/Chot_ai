"""Mã lý do (SPEC M3 §4.2): mỗi mã hỏi → một câu hỏi cụ thể; flag giữ đúng chữ M2 cho export cũ."""

import pytest

from chot.domain.reasons import ASKING, Reason, flag, question
from chot.domain.reasons import ReasonCode as C

QUESTIONS = [
    (C.NOT_CHAIR, {"chair": "Hùng", "key": "MoMo"}, "Hùng đã chốt MoMo chưa?"),
    (
        C.HEDGED,
        {"speaker": "Hùng", "quote": "tạm thời đi MoMo", "key": "MoMo"},
        "Hùng nói 'tạm thời đi MoMo'. Đã chốt MoMo chưa?",
    ),
    (
        C.NOD_ONLY,
        {"chair": "Thảo", "key": "Jira"},
        "Thảo chỉ đáp 'Ừ.' sau đề xuất Jira. Đã chốt chưa?",
    ),
    (
        C.CO_CHAIR_OBJECTION,
        {"chair": "Vân", "co_chair": "Khánh", "key": "TikTok Shop"},
        "Vân chốt TikTok Shop nhưng Khánh đã phản đối và chưa đồng ý lại. Đã chốt chưa?",
    ),
    (C.OWNER_MISSING, {"content": "gọi bên vận thăng"}, "Ai làm 'gọi bên vận thăng'?"),
    (
        C.OWNER_UNCONFIRMED,
        {"owner": "Hảo", "content": "gom review"},
        "Hảo đã nhận 'gom review' chưa?",
    ),
    (
        C.OWNER_DECLINED,
        {"owner": "Minh", "content": "so sánh phí VNPay"},
        "Minh trì hoãn 'so sánh phí VNPay'. Vẫn giao cho Minh?",
    ),
    (
        C.OWNER_ABSENT,
        {"owner": "Phong", "content": "duyệt hợp đồng"},
        "Phong vắng họp. Đã nhận 'duyệt hợp đồng' chưa?",
    ),
    (C.DEADLINE_VAGUE, {"deadline_text": "tuần sau"}, "Hạn 'tuần sau' là ngày nào?"),
    (
        C.DURABLE_KNOWLEDGE,
        {"content": "Mọi lô xuất kho phải có mã PO"},
        "Lưu vào Kho tri thức: 'Mọi lô xuất kho phải có mã PO'?",
    ),
    (C.THREAD_UNMAPPED, {}, "Mục này thuộc chủ đề nào?"),
]


@pytest.mark.parametrize(("code", "params", "expected"), QUESTIONS, ids=[q[0] for q in QUESTIONS])
def test_each_asking_code_renders_its_question(code, params, expected):
    assert question(Reason(code=code, params=params)) == expected


def test_all_asking_codes_are_covered():
    assert {q[0] for q in QUESTIONS} == ASKING


def test_hearsay_knowledge_question_carries_warning():
    q = question(
        Reason(code=C.DURABLE_KNOWLEDGE, params={"content": "Khách chỉ dùng MoMo", "hearsay": True})
    )
    assert q.startswith("Lưu vào Kho tri thức: 'Khách chỉ dùng MoMo'?") and "rào đón" in q


@pytest.mark.parametrize(
    "code", [C.FALLBACK_KEPT, C.CHANGED_MIND, C.NO_AGREEMENT, C.AGREEMENT_REVERSED]
)
def test_info_codes_ask_nothing(code):
    assert code not in ASKING and question(Reason(code=code)) is None


@pytest.mark.parametrize(
    ("reason", "legacy"),
    [
        (Reason(code=C.NOT_CHAIR), "người đồng ý không phải người chủ trì"),
        (Reason(code=C.HEDGED), "đồng thuận có rào đón"),
        (Reason(code=C.NOD_ONLY), "chủ trì chỉ đáp 'Ừ.' — đồng ý gián tiếp, cần xác nhận"),
        (
            Reason(code=C.CO_CHAIR_OBJECTION, params={"co_chair": "Khánh"}),
            "đồng chủ trì Khánh đã phản đối, chưa đồng ý lại",
        ),
        (Reason(code=C.FALLBACK_KEPT), "có điều kiện quay lại phương án cũ — phương án cũ vẫn mở"),
        (Reason(code=C.CHANGED_MIND), "đã đổi ý trong cuộc họp — xem timeline"),
        (Reason(code=C.AGREEMENT_REVERSED), "đã có đồng thuận nhưng bị lật lại"),
        (Reason(code=C.NO_AGREEMENT), "chưa có đồng thuận"),
        (
            Reason(code=C.OWNER_ABSENT, params={"owner": "Phong"}),
            "owner 'Phong' vắng mặt — cần xác nhận lại với người đó",
        ),
        (
            Reason(code=C.OWNER_MISSING, params={"name": "Tí"}),
            "owner 'Tí' không có trong danh sách người tham gia",
        ),
        (Reason(code=C.OWNER_MISSING), "chưa rõ ai nhận việc"),
        (Reason(code=C.OWNER_DECLINED), "owner từ chối hoặc trì hoãn"),
        (Reason(code=C.OWNER_UNCONFIRMED), "owner chưa xác nhận nhận việc"),
        (Reason(code=C.DEADLINE_VAGUE), "hạn chót chưa cụ thể"),
    ],
)
def test_flag_keeps_m2_text(reason, legacy):
    assert flag(reason) == legacy
