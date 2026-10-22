"""Use case cho vòng đời một cuộc họp: xử lý → duyệt → xuất bản."""

from __future__ import annotations

import datetime as dt
import secrets
import uuid
from collections.abc import Callable, Iterable

from pydantic import BaseModel, Field

from chot.domain.enums import ItemType, ReviewState, Status
from chot.domain.enums import ReviewAction as Action
from chot.domain.models import Evidence, Item, Ledger, Transcript
from chot.domain.review import apply_answer, initial_review_state
from chot.domain.status_table import check_status
from chot.usecases.ports import LedgerBuilder


class ReviewLogEntry(BaseModel):
    """Một dòng nhật ký duyệt — chỉ thêm, không sửa / xoá (nguồn cho "học từ sai sót")."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)  # chống ghi trùng khi lưu lại
    item_id: str
    field: str
    old: str | None
    new: str | None
    action: Action | None = None  # trả lời câu hỏi; None = sửa tay (PATCH)
    by: str | None = None
    at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def new_id() -> str:
    """Id cho link bí mật (nhóm họp, cuộc họp): 128 bit ngẫu nhiên, 22 ký tự."""
    return secrets.token_urlsafe(16)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class ReadOnly(PermissionError):
    """Nhóm họp chỉ xem (series mẫu) — không trả lời, sửa, xuất bản hay thêm buổi họp."""


class Published(Exception):
    """Cuộc họp đã xuất bản — khoá sửa."""


class Series(BaseModel):
    """Nhóm họp định kỳ. Ai có link (id) thì xem và sửa được — không có tài khoản ở M3."""

    id: str = Field(default_factory=new_id)
    name: str
    read_only: bool = False
    created_at: dt.datetime = Field(default_factory=_now)


class KnowledgeEntry(BaseModel):
    """Một mục trong Kho tri thức của nhóm họp — chỉ tri thức lâu dài đã được xác nhận."""

    series_id: str
    meeting_id: str
    item_id: str
    content: str
    evidence: list[Evidence] = Field(default_factory=list)
    confirmed_by: str | None = None
    confirmed_at: dt.datetime | None = None


class MeetingRecord(BaseModel):
    id: str = Field(default_factory=new_id)
    transcript: Transcript
    ledger: Ledger
    approved: set[str] = Field(default_factory=set)
    published: bool = False
    review_log: list[ReviewLogEntry] = Field(default_factory=list)
    created_at: dt.datetime = Field(default_factory=_now)
    series_id: str | None = None  # None = tạo qua POST /meetings (M2), không thuộc nhóm nào


class MeetingRepository:
    """Port lưu trữ: InMemoryRepository (test, không có DATABASE_URL) | PostgresRepository.

    `review_log` của record chỉ được thêm — repo không bao giờ sửa / xoá dòng đã lưu.
    """

    def save(self, record: MeetingRecord) -> None: ...
    def get(self, meeting_id: str) -> MeetingRecord | None: ...
    def list(self, series_id: str | None = None) -> list[MeetingRecord]: ...
    def save_series(self, series: Series) -> None: ...
    def get_series(self, series_id: str) -> Series | None: ...
    def add_knowledge(self, entries: list[KnowledgeEntry]) -> None:
        """Thêm vào Kho; trùng (meeting_id, item_id) thì ghi đè."""

    def knowledge(self, series_id: str) -> list[KnowledgeEntry]: ...


class SeriesView(BaseModel):
    series: Series
    meetings: list[MeetingRecord]
    knowledge: list[KnowledgeEntry]
    pending: list[tuple[str, Item]]  # (meeting_id, mục) — "Việc treo"


EDITABLE_FIELDS = {"status", "owner", "deadline", "content", "decided_by"}


READ_ONLY_MSG = "Nhóm họp mẫu chỉ để xem, không sửa được. Hãy tạo nhóm họp mới."


def _knowledge(series_id: str, meeting_id: str, item: Item) -> KnowledgeEntry:
    reviewer = next((e for e in reversed(item.evidence) if e.kind == "reviewer"), None)
    return KnowledgeEntry(
        series_id=series_id,
        meeting_id=meeting_id,
        item_id=item.id,
        content=item.content,
        evidence=item.evidence,
        confirmed_by=reviewer.by if reviewer else None,
        confirmed_at=reviewer.at if reviewer else None,
    )


TranscriptParser = Callable[[str, str | None], Transcript]


class MeetingService:
    def __init__(
        self, repo: MeetingRepository, builder: LedgerBuilder, parser: TranscriptParser
    ) -> None:
        self.repo = repo
        self.builder = builder
        self.parser = parser

    def process(
        self, transcript_text: str, meeting_id: str | None = None, series_id: str | None = None
    ) -> MeetingRecord:
        if series_id and self._series(series_id).read_only:  # kiểm trước khi tốn lượt LLM
            raise ReadOnly(READ_ONLY_MSG)
        tr = self.parser(transcript_text, meeting_id)
        record = self._record(tr, self.builder.build(tr), series_id)
        self.repo.save(record)
        return record

    @staticmethod
    def _record(tr: Transcript, ledger: Ledger, series_id: str | None) -> MeetingRecord:
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
        return MeetingRecord(transcript=tr, ledger=ledger, series_id=series_id)

    def create_series(self, name: str) -> Series:
        series = Series(name=name)
        self.repo.save_series(series)
        return series

    def seed_series(
        self, series: Series, transcripts: Iterable[str], builder: LedgerBuilder
    ) -> None:
        """Nạp nhóm họp mẫu (read_only) một lần; đã có thì bỏ qua."""
        # ponytail: 2 tiến trình khởi động cùng lúc có thể nạp trùng; 1 worker thì không sao
        if self.repo.get_series(series.id):
            return
        self.repo.save_series(series)
        for text in transcripts:
            tr = self.parser(text, None)
            self.repo.save(self._record(tr, builder.build(tr), series.id))

    def series_view(self, series_id: str) -> SeriesView:
        series = self._series(series_id)
        meetings = self.repo.list(series_id)
        pending = [
            (r.id, i)
            for r in meetings
            for i in r.ledger.items
            if i.review_state == ReviewState.DEFERRED
        ]
        return SeriesView(
            series=series,
            meetings=meetings,
            knowledge=self.repo.knowledge(series_id),
            pending=pending,
        )

    def review_item(self, meeting_id: str, item_id: str, changes: dict) -> MeetingRecord:
        record = self._require(meeting_id)
        self._check_writable(record)
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
        self._check_writable(record)
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
        """Khoá cuộc họp; tri thức lâu dài đã xác nhận vào Kho của nhóm. Gọi lại không nhân đôi."""
        record = self._require(meeting_id)
        self._check_writable(record, allow_published=True)
        pending = [i.id for i in record.ledger.items if i.review_state == ReviewState.PENDING]
        if pending:
            raise ValueError(f"Còn {len(pending)} câu hỏi chưa trả lời: {', '.join(pending)}")
        record.published = True
        self.repo.save(record)
        if record.series_id:
            self.repo.add_knowledge(
                [
                    _knowledge(record.series_id, record.id, i)
                    for i in record.ledger.items
                    if i.type == ItemType.KNOWLEDGE
                    and i.scope == "durable"
                    and i.review_state == ReviewState.CONFIRMED
                ]
            )
        return record

    def _check_writable(self, record: MeetingRecord, allow_published: bool = False) -> None:
        series = self.repo.get_series(record.series_id) if record.series_id else None
        if series and series.read_only:
            raise ReadOnly(READ_ONLY_MSG)
        if record.published and not allow_published:
            raise Published("Cuộc họp đã xuất bản, không sửa được nữa.")

    def _series(self, series_id: str) -> Series:
        series = self.repo.get_series(series_id)
        if series is None:
            raise KeyError("Không tìm thấy nhóm họp")
        return series

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
