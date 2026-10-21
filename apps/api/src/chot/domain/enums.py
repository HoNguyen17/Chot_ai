from enum import StrEnum


class ItemType(StrEnum):
    """8 loại thông tin trong Ledger."""

    DECISION = "decision"
    OPTION = "option"  # phương án không được chọn, giữ làm lịch sử
    TASK = "task"
    BLOCKER = "blocker"
    OPEN_QUESTION = "open_question"
    KNOWLEDGE = "knowledge"
    REQUEST = "request"
    FEEDBACK = "feedback"


class Status(StrEnum):
    """Trạng thái cuối của một mục sau khi họp kết thúc."""

    FINAL = "final"  # Đã chốt: cam kết rõ, không rào đón, từ người có thẩm quyền, không bị lật
    NEEDS_CONFIRMATION = "needs_confirmation"  # Cần xác nhận: tạm chốt, mơ hồ, owner chưa nhận
    SUPERSEDED = "superseded"  # Bị thay thế bởi một quyết định đã chốt
    REJECTED = "rejected"  # Bị bác (chỉ người duyệt gán thủ công ở v1)
    DEFERRED = "deferred"  # Hoãn sang lần sau / chờ người khác quyết
    OPEN = "open"  # Đang mở: task đã nhận, blocker, câu hỏi, phương án còn treo
    NOTED = "noted"  # Ghi nhận: tri thức, phản hồi (M3)


class ReviewState(StrEnum):
    """Trạng thái duyệt của một mục (M3) — tách khỏi Status: duyệt không tự đổi kết luận."""

    AUTO_ACCEPTED = "auto_accepted"  # không có mã lý do hỏi → không cần người trả lời
    PENDING = "pending"  # đang chờ người duyệt trả lời
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DEFERRED = "deferred"  # để họp sau → "Việc treo"


class ReviewAction(StrEnum):
    CONFIRM = "confirm"
    REJECT = "reject"
    DEFER = "defer"


class EventKind(StrEnum):
    """Sự kiện ở cấp từng câu nói. LLM gán nhãn, code suy trạng thái."""

    # Chuỗi quyết định
    PROPOSE = "propose"
    REVISE = "revise"  # đề xuất thay thế / quay lại phương án khác
    OBJECT = "object"
    AGREE = "agree"
    DEFER = "defer"
    REOPEN = "reopen"  # "thôi khoan" — huỷ đồng thuận trước đó
    # Công việc
    ASSIGN = "assign"
    COMMIT = "commit"
    DECLINE = "decline"
    # Thông tin khác
    BLOCKER = "blocker"
    QUESTION = "question"
    INFO = "info"
    REQUEST = "request"
    FEEDBACK = "feedback"


DECISION_EVENTS = frozenset(
    {
        EventKind.PROPOSE,
        EventKind.REVISE,
        EventKind.OBJECT,
        EventKind.AGREE,
        EventKind.DEFER,
        EventKind.REOPEN,
    }
)
TASK_EVENTS = frozenset({EventKind.ASSIGN, EventKind.COMMIT, EventKind.DECLINE})
STANDALONE_EVENTS = {
    EventKind.BLOCKER: ItemType.BLOCKER,
    EventKind.QUESTION: ItemType.OPEN_QUESTION,
    EventKind.INFO: ItemType.KNOWLEDGE,
    EventKind.REQUEST: ItemType.REQUEST,
    EventKind.FEEDBACK: ItemType.FEEDBACK,
}

ID_PREFIX = {
    ItemType.DECISION: "D",
    ItemType.OPTION: "O",
    ItemType.TASK: "T",
    ItemType.BLOCKER: "B",
    ItemType.OPEN_QUESTION: "Q",
    ItemType.KNOWLEDGE: "K",
    ItemType.REQUEST: "R",
    ItemType.FEEDBACK: "F",
}
