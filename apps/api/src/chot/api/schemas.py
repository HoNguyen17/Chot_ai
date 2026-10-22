from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from chot.domain.enums import ItemType, ReviewAction, ReviewState, Status
from chot.domain.models import Item, Ledger, Participant, Utterance
from chot.domain.reasons import ReasonCode, question
from chot.usecases.meetings import KnowledgeEntry, MeetingRecord, Series, SeriesView


class CreateMeetingIn(BaseModel):
    transcript_text: str = Field(min_length=1)
    meeting_id: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{1,64}$")


class CreateSeriesIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class AnswerIn(BaseModel):
    action: ReviewAction
    owner: str | None = Field(None, max_length=200)
    deadline: dt.date | None = None
    thread: str | None = Field(None, max_length=200)


class ReviewItemIn(BaseModel):
    status: str | None = None
    owner: str | None = None
    deadline: str | None = None
    content: str | None = None
    decided_by: str | None = None
    approved: bool | None = None

    def changes(self) -> dict:
        return self.model_dump(exclude_unset=True)


class MeetingSummaryOut(BaseModel):
    id: str
    title: str | None
    date: dt.date | None
    items: int
    needs_confirmation: int
    published: bool

    @classmethod
    def from_record(cls, r: MeetingRecord) -> MeetingSummaryOut:
        return cls(
            id=r.id,
            title=r.transcript.title,
            date=r.transcript.date,
            items=len(r.ledger.items),
            needs_confirmation=len(r.ledger.by_status(Status.NEEDS_CONFIRMATION)),
            published=r.published,
        )


class QuestionOut(BaseModel):
    """Một thẻ trong hàng đợi "Cần bạn trả lời" — 1 thẻ / mục đang chờ."""

    item_id: str
    type: ItemType
    codes: list[ReasonCode]
    texts: list[str]


NO_CODE_QUESTION = "Mục này cần xác nhận — có đúng như vậy không?"


def questions(ledger: Ledger) -> list[QuestionOut]:
    out: list[QuestionOut] = []
    for i in ledger.items:
        if i.review_state != ReviewState.PENDING:
            continue
        asking = [r for r in i.reasons if r.asking]
        out.append(
            QuestionOut(
                item_id=i.id,
                type=i.type,
                codes=[r.code for r in asking],  # codes[k] ↔ texts[k]
                # needs_confirmation không mã (grounding hạ cấp) vẫn cần 1 câu hỏi
                texts=[question(r) or "" for r in asking] or [NO_CODE_QUESTION],
            )
        )
    return out


class MeetingOut(BaseModel):
    id: str
    title: str | None
    date: dt.date | None
    participants: list[Participant]
    absent: list[Participant]
    utterances: list[Utterance]
    ledger: Ledger
    approved: list[str]
    published: bool
    series_id: str | None
    questions: list[QuestionOut]

    @classmethod
    def from_record(cls, r: MeetingRecord) -> MeetingOut:
        tr = r.transcript
        return cls(
            id=r.id,
            title=tr.title,
            date=tr.date,
            participants=tr.participants,
            absent=tr.absent,
            utterances=tr.utterances,
            ledger=r.ledger,
            approved=sorted(r.approved),
            published=r.published,
            series_id=r.series_id,
            questions=questions(r.ledger),
        )


class PendingOut(BaseModel):
    meeting_id: str
    item: Item


class SeriesOut(Series):
    meetings: list[MeetingSummaryOut] = Field(default_factory=list)
    knowledge: list[KnowledgeEntry] = Field(default_factory=list)
    pending: list[PendingOut] = Field(default_factory=list)  # "Việc treo"

    @classmethod
    def from_view(cls, v: SeriesView) -> SeriesOut:
        return cls(
            **v.series.model_dump(),
            meetings=[MeetingSummaryOut.from_record(r) for r in v.meetings],
            knowledge=v.knowledge,
            pending=[PendingOut(meeting_id=m, item=i) for m, i in v.pending],
        )
