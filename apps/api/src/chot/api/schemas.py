from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from chot.domain.models import Ledger, Participant, Utterance
from chot.usecases.meetings import MeetingRecord


class CreateMeetingIn(BaseModel):
    transcript_text: str = Field(min_length=1)
    meeting_id: str | None = None


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
        )
