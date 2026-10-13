"""Pipeline chính: Transcript → (LLM) sự kiện → (luật) Ledger → (grounding) Ledger đã kiểm."""

from __future__ import annotations

from pathlib import Path

from chot.domain.grounding import GroundingReport, apply_grounding
from chot.domain.models import ExtractionResult, Ledger, Transcript
from chot.domain.status_rules import build_ledger
from chot.usecases.ports import EventExtractor


class RulesLedgerBuilder:
    name = "rules-v1"

    def __init__(self, extractor: EventExtractor) -> None:
        self.extractor = extractor
        self.last_extraction: ExtractionResult | None = None
        self.last_report: GroundingReport | None = None

    def build(self, tr: Transcript) -> Ledger:
        extraction = self.extractor.extract(tr)
        ledger = build_ledger(tr, extraction, generated_by=f"{self.name}+{self.extractor.name}")
        ledger, report = apply_grounding(ledger, tr)
        self.last_extraction, self.last_report = extraction, report
        return ledger


class StaticExtractor:
    """Trả về sự kiện có sẵn (đọc từ file). Dùng cho test và để replay kết quả LLM đã cache."""

    name = "static"

    def __init__(self, extraction: ExtractionResult) -> None:
        self.extraction = extraction

    def extract(self, tr: Transcript) -> ExtractionResult:
        return self.extraction


class DirectoryReplayExtractor:
    """Đọc sự kiện đã lưu ở <dir>/<meeting_id>.json (từ một lần chạy LLM trước, hoặc oracle).

    Cho phép demo / sửa luật mà không tốn token. Không có file → báo lỗi rõ ràng.
    """

    name = "replay"

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def extract(self, tr: Transcript) -> ExtractionResult:
        path = self.directory / f"{tr.meeting_id}.json"
        if not path.exists():
            raise LookupError(
                f"Không có sự kiện đã lưu cho cuộc họp '{tr.meeting_id}' trong {path.parent}"
            )
        return ExtractionResult.model_validate_json(path.read_text(encoding="utf-8"))
