from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from chot.domain.enums import EventKind, ItemType, Status


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


class Thread(BaseModel):
    id: str  # slug, vd "payment-gateway"
    title: str


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


class Evidence(BaseModel):
    utt: str
    quote: str
    ts: str | None = None
    speaker: str | None = None


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
    flags: list[str] = Field(default_factory=list)  # lý do hạ trạng thái, cảnh báo cho người duyệt


class Ledger(BaseModel):
    meeting_id: str
    generated_by: str = "rules-v1"
    threads: list[Thread] = Field(default_factory=list)
    items: list[Item] = Field(default_factory=list)

    def by_status(self, status: Status) -> list[Item]:
        return [i for i in self.items if i.status == status]


class ExtractionResult(BaseModel):
    """Kết quả bước LLM: chủ đề + sự kiện. Không chứa trạng thái."""

    threads: list[Thread] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
