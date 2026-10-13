from __future__ import annotations

from chot.usecases.meetings import MeetingRecord, MeetingRepository

MAX_RECORDS = 500  # demo công khai: RAM có trần


class InMemoryRepository(MeetingRepository):
    """Lưu trong RAM — đủ cho demo và test. Restart là mất; vượt MAX_RECORDS thì xoá cũ nhất."""

    def __init__(self) -> None:
        self._data: dict[str, MeetingRecord] = {}

    def save(self, record: MeetingRecord) -> None:
        if record.id not in self._data and len(self._data) >= MAX_RECORDS:
            del self._data[next(iter(self._data))]  # dict giữ thứ tự chèn → cũ nhất
        self._data[record.id] = record

    def get(self, meeting_id: str) -> MeetingRecord | None:
        return self._data.get(meeting_id)

    def list(self) -> list[MeetingRecord]:
        return sorted(self._data.values(), key=lambda r: r.created_at, reverse=True)
