"""Các interface (port) mà use case cần. Adapter nào cũng được, miễn đúng chữ ký."""

from __future__ import annotations

from typing import Protocol

from chot.domain.models import ExtractionResult, Ledger, Transcript


class EventExtractor(Protocol):
    name: str

    def extract(self, tr: Transcript) -> ExtractionResult: ...


class LedgerBuilder(Protocol):
    """Bất cứ thứ gì biến Transcript thành Ledger: pipeline chính hoặc baseline."""

    name: str

    def build(self, tr: Transcript) -> Ledger: ...
