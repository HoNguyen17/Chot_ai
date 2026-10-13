from __future__ import annotations

from chot.usecases.meetings import MeetingRecord, MeetingRepository


class InMemoryRepository(MeetingRepository):
    """Lưu trong RAM — đủ cho demo và test. Restart server là mất."""

    def __init__(self) -> None:
        self._data: dict[str, MeetingRecord] = {}

    def save(self, record: MeetingRecord) -> None:
        self._data[record.id] = record

    def get(self, meeting_id: str) -> MeetingRecord | None:
        return self._data.get(meeting_id)

    def list(self) -> list[MeetingRecord]:
        return sorted(self._data.values(), key=lambda r: r.created_at, reverse=True)
