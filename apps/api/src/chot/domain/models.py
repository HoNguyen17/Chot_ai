from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from chot.domain.enums import EventKind, ItemType, ReviewState, Status
from chot.domain.reasons import Reason
from chot.domain.status_table import LABEL


def format_ts(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class Participant(BaseModel):
    name: str
    role: str | None = None
    is_chair: bool = False


class Utterance(BaseModel):
    id: str  # "u001"
    index: int  # thứ tự trong cuộc họp, bắt đầu từ 1
    ts: int  # giây tính từ đầu cuộc họp
    speaker: str
    text: str

    @property
    def ts_label(self) -> str:
        return format_ts(self.ts)


class Transcript(BaseModel):
    meeting_id: str
    title: str | None = None
    date: dt.date | None = None
    participants: list[Participant] = Field(default_factory=list)
    absent: list[Participant] = Field(default_factory=list)
    utterances: list[Utterance] = Field(default_factory=list)

    def utt(self, utt_id: str) -> Utterance | None:
        return next((u for u in self.utterances if u.id == utt_id), None)

    def order(self, utt_id: str) -> int:
        u = self.utt(utt_id)
        return u.index if u else 10**9

    @property
    def chairs(self) -> set[str]:
        return {p.name for p in self.participants if p.is_chair}

    @property
    def names(self) -> set[str]:
        return {p.name for p in self.participants}

    @property
    def known_names(self) -> set[str]:
        """Người có tên trong header (dự họp + vắng mặt) — giao việc cho người vắng không phải bịa."""
        return self.names | {p.name for p in self.absent}


class Thread(BaseModel):
    id: str  # slug, vd "payment-gateway"
    title: str
    keys: list[str] = Field(default_factory=list)  # M3 lượt 1: phương án + việc của chủ đề
    utt_ids: list[str] = Field(default_factory=list)  # M3 lượt 1: các câu thuộc chủ đề
    mapped: bool = True  # False = lượt 2 dùng thread không có trong bản đồ → THREAD_UNMAPPED


class Event(BaseModel):
    """Một sự kiện gắn với một câu nói. Đây là output của LLM, input của luật."""

    utt: str
    thread: str
    kind: EventKind
    speaker: str
    key: str | None = None  # nhãn phương án (quyết định) hoặc nhãn việc (task)
    content: str = ""
    hedged: bool = False
    owner: str | None = None
    deadline_text: str | None = None
    quote: str = ""
    durable_hint: bool = False  # info: LLM gợi ý tri thức dùng lâu dài (code quyết scope)
    new_key: bool = False  # phương án mới chưa có trong bản đồ chủ đề (M3 lượt 2)


class Evidence(BaseModel):
    """Bằng chứng: câu trong transcript, hoặc câu trả lời của người duyệt (không có utt)."""

    utt: str | None = None
    quote: str = ""
    ts: str | None = None
    speaker: str | None = None
    kind: Literal["transcript", "reviewer"] = "transcript"
    by: str | None = None
    at: dt.datetime | None = None
    note: str | None = None


class TimelineEntry(BaseModel):
    """Một bước trong diễn biến của chủ đề — dòng "Vì sao" trên UI."""

    utt: str
    ts: str | None = None
    speaker: str
    kind: EventKind
    key: str | None = None
    quote: str = ""


class Item(BaseModel):
    id: str
    type: ItemType
    thread: str | None = None
    content: str
    status: Status
    owner: str | None = None
    decided_by: str | None = None
    deadline: dt.date | None = None
    deadline_text: str | None = None
    supersedes: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float | None = None
    flags: list[str] = Field(default_factory=list)  # chữ M2 sinh từ reasons (export cũ)
    reasons: list[Reason] = Field(default_factory=list)  # mã lý do (M3) — nguồn của câu hỏi
    review_state: ReviewState | None = None  # đặt khi cuộc họp vào duyệt (MeetingService)
    scope: Literal["meeting", "durable"] | None = None  # chỉ knowledge
    timeline: list[TimelineEntry] = Field(default_factory=list)  # decision / option

    @computed_field
    @property
    def status_label(self) -> str:
        """Nhãn UI theo type (bảng status_table) — web chỉ đọc, không chép bảng."""
        return LABEL[self.type].get(self.status, self.status.value)


class Ledger(BaseModel):
    meeting_id: str
    generated_by: str = "rules-v1"
    threads: list[Thread] = Field(default_factory=list)
    items: list[Item] = Field(default_factory=list)
    # Sự kiện LLM đã dùng để dựng ledger — lưu để replay khi sửa luật; không trả qua API.
    events: list[Event] = Field(default_factory=list, exclude=True)

    def by_status(self, status: Status) -> list[Item]:
        return [i for i in self.items if i.status == status]


class ExtractionResult(BaseModel):
    """Kết quả bước LLM: chủ đề + sự kiện. Không chứa trạng thái."""

    threads: list[Thread] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
