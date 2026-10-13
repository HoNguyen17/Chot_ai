"""PostgresRepository — VIỆC NGÀY 2 (xem CLAUDE.md > Việc tiếp theo).

Schema: db/migrations/001_init.sql. Gợi ý cài đặt:
- save(): upsert `meetings`, xoá + chèn lại `utterances`, `items`, `evidence` trong 1 transaction.
- get(): đọc lại và dựng MeetingRecord.
- review_log → bảng `review_actions` (append-only, không xoá).
Kết nối: DATABASE_URL (Supabase dùng connection string dạng postgresql://…?sslmode=require).
"""

from __future__ import annotations

from chot.usecases.meetings import MeetingRecord, MeetingRepository


class PostgresRepository(MeetingRepository):
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        raise NotImplementedError("PostgresRepository: làm ở Ngày 2. Tạm dùng InMemoryRepository.")

    def save(self, record: MeetingRecord) -> None:  # pragma: no cover
        raise NotImplementedError

    def get(self, meeting_id: str) -> MeetingRecord | None:  # pragma: no cover
        raise NotImplementedError

    def list(self) -> list[MeetingRecord]:  # pragma: no cover
        raise NotImplementedError
