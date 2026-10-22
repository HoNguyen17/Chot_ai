from __future__ import annotations

from chot.usecases.meetings import KnowledgeEntry, MeetingRecord, MeetingRepository, Series

MAX_RECORDS = 500  # demo công khai: RAM có trần


class InMemoryRepository(MeetingRepository):
    """Lưu trong RAM — đủ cho demo và test. Restart là mất; vượt MAX_RECORDS thì xoá cũ nhất
    (trừ cuộc họp của nhóm mẫu read_only)."""

    def __init__(self) -> None:
        self._data: dict[str, MeetingRecord] = {}
        self._series: dict[str, Series] = {}
        self._knowledge: dict[tuple[str, str], KnowledgeEntry] = {}

    def save(self, record: MeetingRecord) -> None:
        if record.id not in self._data and len(self._data) >= MAX_RECORDS:
            # dict giữ thứ tự chèn → cũ nhất trước
            old = next((k for k, r in self._data.items() if not self._pinned(r)), None)
            if old:
                del self._data[old]
        self._data[record.id] = record

    def _pinned(self, record: MeetingRecord) -> bool:
        series = self._series.get(record.series_id or "")
        return bool(series and series.read_only)

    def get(self, meeting_id: str) -> MeetingRecord | None:
        return self._data.get(meeting_id)

    def list(self, series_id: str | None = None) -> list[MeetingRecord]:
        records = [r for r in self._data.values() if series_id in (None, r.series_id)]
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def save_series(self, series: Series) -> None:
        self._series[series.id] = series

    def get_series(self, series_id: str) -> Series | None:
        return self._series.get(series_id)

    def add_knowledge(self, entries: list[KnowledgeEntry]) -> None:
        for e in entries:
            self._knowledge[(e.meeting_id, e.item_id)] = e

    def knowledge(self, series_id: str) -> list[KnowledgeEntry]:
        return [e for e in self._knowledge.values() if e.series_id == series_id]
