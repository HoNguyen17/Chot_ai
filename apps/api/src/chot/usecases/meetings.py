"""Use case cho vòng đời một cuộc họp: xử lý → duyệt → xuất bản."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Callable

from pydantic import BaseModel, Field

from chot.domain.enums import ReviewAction as Action
from chot.domain.enums import ReviewState, Status
from chot.domain.models import Item, Ledger, Transcript
from chot.domain.review import apply_answer, initial_review_state
from chot.domain.status_table import check_status
from chot.usecases.ports import LedgerBuilder


class ReviewLogEntry(BaseModel):
    """Một dòng nhật ký duyệt — chỉ thêm, không sửa / xoá (nguồn cho "học từ sai sót")."""

    item_id: str
    field: str
    old: str | None
    new: str | None
    action: Action | None = None  # trả lời câu hỏi; None = sửa tay (PATCH)
    by: str | None = None
    at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))


def _text(value: object) -> str | None:
    return None if value is None else str(value)


class MeetingRecord(BaseModel):
    id: str
    transcript: Transcript
    ledger: Ledger
    approved: set[str] = Field(default_factory=set)
    published: bool = False
    review_log: list[ReviewLogEntry] = Field(default_factory=list)
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
        # Sau grounding: mục không có câu hỏi → tự chấp nhận, còn lại vào hàng đợi trả lời
        ledger = ledger.model_copy(
            update={
                "items": [
                    i.model_copy(update={"review_state": initial_review_state(i)})
                    for i in ledger.items
                ]
            }
        )
        # id record ngẫu nhiên, tách khỏi meeting_id (dùng cho replay): không đoán được,
        # hai người cùng chọn mẫu m01 không ghi đè record của nhau.
        record = MeetingRecord(id=uuid.uuid4().hex[:12], transcript=tr, ledger=ledger)
        self.repo.save(record)
        return record

    def review_item(self, meeting_id: str, item_id: str, changes: dict) -> MeetingRecord:
        record = self._require(meeting_id)
        item = self._item(record, item_id)
        update = {}
        for field, value in changes.items():
            if field == "approved":  # đường M2 cho UI cũ: duyệt = xác nhận, không đổi status
                (record.approved.add if value else record.approved.discard)(item_id)
                state = ReviewState.CONFIRMED if value else initial_review_state(item)
                record.review_log.append(
                    ReviewLogEntry(
                        item_id=item_id,
                        field="review_state",
                        old=item.review_state,
                        new=state,
                        action=Action.CONFIRM if value else None,
                    )
                )
                record.ledger = self._replace(
                    record, item.model_copy(update={"review_state": state})
                )
                item = self._item(record, item_id)
                continue
            if field not in EDITABLE_FIELDS:
                raise ValueError(f"Không được sửa trường {field}")
            if field == "status":
                value = Status(value)
                check_status(item.type, value)
            if field == "deadline" and isinstance(value, str):
                value = dt.date.fromisoformat(value) if value else None
            record.review_log.append(
                ReviewLogEntry(
                    item_id=item_id, field=field, old=str(getattr(item, field)), new=str(value)
                )
            )
            update[field] = value
        if update:
            # người đã sửa = người đã duyệt mục đó
            update["review_state"] = ReviewState.CONFIRMED
            record.ledger = self._replace(record, item.model_copy(update=update))
            record.approved.add(item_id)
        self.repo.save(record)
        return record

    def answer(
        self,
        meeting_id: str,
        item_id: str,
        action: Action,
        owner: str | None = None,
        deadline: dt.date | None = None,
        thread: str | None = None,
        by: str = "reviewer",
    ) -> MeetingRecord:
        """Trả lời câu hỏi của một mục: Xác nhận / Bác bỏ / để họp sau (SPEC M3 §4.4)."""
        record = self._require(meeting_id)
        item = self._item(record, item_id)
        if owner and owner not in record.transcript.known_names:
            raise ValueError(f"'{owner}' không có trong cuộc họp")
        new = apply_answer(
            item, Action(action), owner=owner, deadline=deadline, thread=thread, by=by
        )
        # 1 dòng cho câu trả lời (status) + 1 dòng cho mỗi trường người duyệt sửa kèm
        record.review_log += [
            ReviewLogEntry(
                item_id=item_id,
                field=f,
                old=_text(getattr(item, f)),
                new=_text(getattr(new, f)),
                action=action,
                by=by,
            )
            for f in ("status", "owner", "deadline", "thread", "scope")
            if f == "status" or getattr(item, f) != getattr(new, f)
        ]
        record.ledger = self._replace(record, new)
        self.repo.save(record)
        return record

    def publish(self, meeting_id: str) -> MeetingRecord:
        record = self._require(meeting_id)
        pending = [i.id for i in record.ledger.items if i.review_state == ReviewState.PENDING]
        if pending:
            raise ValueError(f"Còn {len(pending)} câu hỏi chưa trả lời: {', '.join(pending)}")
        record.published = True
        self.repo.save(record)
        return record

    @staticmethod
    def _replace(record: MeetingRecord, new: Item) -> Ledger:
        items = [new if i.id == new.id else i for i in record.ledger.items]
        return record.ledger.model_copy(update={"items": items})

    @staticmethod
    def _item(record: MeetingRecord, item_id: str) -> Item:
        item = next((i for i in record.ledger.items if i.id == item_id), None)
        if item is None:
            raise KeyError(f"Không có mục {item_id}")
        return item

    def _require(self, meeting_id: str) -> MeetingRecord:
        record = self.repo.get(meeting_id)
        if record is None:
            raise KeyError(f"Không có cuộc họp {meeting_id}")
        return record
