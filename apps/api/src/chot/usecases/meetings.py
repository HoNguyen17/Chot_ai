"""Use case cho vòng đời một cuộc họp: xử lý → duyệt → xuất bản."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Callable

from pydantic import BaseModel, Field

from chot.domain.enums import Status
from chot.domain.models import Item, Ledger, Transcript
from chot.usecases.ports import LedgerBuilder


class ReviewAction(BaseModel):
    item_id: str
    field: str
    old: str | None
    new: str | None
    at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))


class MeetingRecord(BaseModel):
    id: str
    transcript: Transcript
    ledger: Ledger
    approved: set[str] = Field(default_factory=set)
    published: bool = False
    review_log: list[ReviewAction] = Field(default_factory=list)
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))


class MeetingRepository:
    """Port lưu trữ. v1: InMemoryRepository. Ngày 2: PostgresRepository (db/migrations)."""

    def save(self, record: MeetingRecord) -> None: ...
    def get(self, meeting_id: str) -> MeetingRecord | None: ...
    def list(self) -> list[MeetingRecord]: ...


EDITABLE_FIELDS = {"status", "owner", "deadline", "content", "decided_by"}


TranscriptParser = Callable[[str, str | None], Transcript]


class MeetingService:
    def __init__(
        self, repo: MeetingRepository, builder: LedgerBuilder, parser: TranscriptParser
    ) -> None:
        self.repo = repo
        self.builder = builder
        self.parser = parser

    def process(self, transcript_text: str, meeting_id: str | None = None) -> MeetingRecord:
        tr = self.parser(transcript_text, meeting_id)
        ledger = self.builder.build(tr)
        # id record ngẫu nhiên, tách khỏi meeting_id (dùng cho replay): không đoán được,
        # hai người cùng chọn mẫu m01 không ghi đè record của nhau.
        record = MeetingRecord(id=uuid.uuid4().hex[:12], transcript=tr, ledger=ledger)
        self.repo.save(record)
        return record

    def review_item(self, meeting_id: str, item_id: str, changes: dict) -> MeetingRecord:
        record = self._require(meeting_id)
        items = {i.id: i for i in record.ledger.items}
        if item_id not in items:
            raise KeyError(f"Không có mục {item_id}")
        item: Item = items[item_id]
        update = {}
        for field, value in changes.items():
            if field == "approved":
                (record.approved.add if value else record.approved.discard)(item_id)
                continue
            if field not in EDITABLE_FIELDS:
                raise ValueError(f"Không được sửa trường {field}")
            if field == "status":
                value = Status(value)
            if field == "deadline" and isinstance(value, str):
                value = dt.date.fromisoformat(value) if value else None
            record.review_log.append(
                ReviewAction(
                    item_id=item_id, field=field, old=str(getattr(item, field)), new=str(value)
                )
            )
            update[field] = value
        if update:
            new_item = item.model_copy(update=update)
            record.ledger = record.ledger.model_copy(
                update={"items": [new_item if i.id == item_id else i for i in record.ledger.items]}
            )
            record.approved.add(item_id)  # người đã sửa = người đã duyệt mục đó
        self.repo.save(record)
        return record

    def publish(self, meeting_id: str) -> MeetingRecord:
        record = self._require(meeting_id)
        pending = [
            i.id
            for i in record.ledger.items
            if i.status == Status.NEEDS_CONFIRMATION and i.id not in record.approved
        ]
        if pending:
            raise ValueError(
                f"Còn {len(pending)} mục 'Cần xác nhận' chưa duyệt: {', '.join(pending)}"
            )
        record.published = True
        self.repo.save(record)
        return record

    def _require(self, meeting_id: str) -> MeetingRecord:
        record = self.repo.get(meeting_id)
        if record is None:
            raise KeyError(f"Không có cuộc họp {meeting_id}")
        return record
