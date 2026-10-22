"""Các interface (port) mà use case cần. Adapter nào cũng được, miễn đúng chữ ký."""

from __future__ import annotations

from typing import Protocol

from chot.domain.chunking import Chunk
from chot.domain.models import ExtractionResult, Ledger, Thread, Transcript


class EventExtractor(Protocol):
    name: str

    def extract(self, tr: Transcript) -> ExtractionResult: ...


class TopicMapper(Protocol):
    """Lượt 1 (M3): bản đồ chủ đề cho cả cuộc họp."""

    def map(self, tr: Transcript) -> list[Thread]: ...


class ChunkEventExtractor(EventExtractor, Protocol):
    """Lượt 2 (M3): sự kiện của một đoạn, theo bản đồ chủ đề."""

    def extract_chunk(
        self, tr: Transcript, threads: list[Thread], chunk: Chunk
    ) -> ExtractionResult: ...


class LedgerBuilder(Protocol):
    """Bất cứ thứ gì biến Transcript thành Ledger: pipeline chính hoặc baseline."""

    name: str

    def build(self, tr: Transcript) -> Ledger: ...
