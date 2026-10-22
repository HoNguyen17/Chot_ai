"""Pipeline chính: Transcript → (LLM) sự kiện → (luật) Ledger → (grounding) Ledger đã kiểm."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from chot.domain.chunking import Chunk, chunk
from chot.domain.grounding import GroundingReport, apply_grounding
from chot.domain.models import ExtractionResult, Item, Ledger, Thread, Transcript
from chot.domain.reasons import Reason, ReasonCode, flag
from chot.domain.status_rules import build_ledger
from chot.usecases.ports import ChunkEventExtractor, EventExtractor, TopicMapper

log = logging.getLogger(__name__)


def _unmapped(item: Item) -> Item:
    r = Reason(code=ReasonCode.THREAD_UNMAPPED)
    return item.model_copy(update={"reasons": [*item.reasons, r], "flags": [*item.flags, flag(r)]})


class RulesLedgerBuilder:
    name = "rules-v1"

    def __init__(self, extractor: EventExtractor) -> None:
        self.extractor = extractor
        self.last_extraction: ExtractionResult | None = None
        self.last_report: GroundingReport | None = None

    def build(self, tr: Transcript) -> Ledger:
        extraction = self.extractor.extract(tr)
        ledger = build_ledger(tr, extraction, generated_by=f"{self.name}+{self.extractor.name}")
        # thread lượt 2 tự đặt, không có trong bản đồ → hỏi người duyệt, không âm thầm bỏ
        unmapped = {t.id for t in extraction.threads if not t.mapped}
        items = [_unmapped(i) if i.thread in unmapped else i for i in ledger.items]
        ledger, report = apply_grounding(
            ledger.model_copy(update={"items": items, "events": extraction.events}), tr
        )
        self.last_extraction, self.last_report = extraction, report
        return ledger


def merge(
    tr: Transcript, threads: list[Thread], chunks: list[Chunk], results: list[ExtractionResult]
) -> ExtractionResult:
    """Gộp sự kiện các đoạn: chỉ giữ câu được gán nhãn của đoạn, nối theo thứ tự câu.

    Thread lạ → thêm với `mapped=False`; key lạ → thêm vào bản đồ (ghi log).
    """
    kept = []
    for c, r in zip(chunks, results, strict=True):
        labels = set(c.label_ids)  # câu ngữ cảnh / mã câu bịa → bỏ
        kept += [e for e in r.events if e.utt in labels]
    events = sorted(kept, key=lambda e: tr.order(e.utt))
    by_id = {t.id: t.model_copy(deep=True) for t in threads}
    titles = {t.id: t.title for r in results for t in r.threads}
    for e in events:
        if e.thread not in by_id:
            log.info("%s: thread '%s' ngoài bản đồ (%s)", tr.meeting_id, e.thread, e.utt)
            title = titles.get(e.thread, e.thread)
            by_id[e.thread] = Thread(id=e.thread, title=title, mapped=False)
        t = by_id[e.thread]
        if e.key and e.key not in t.keys:
            log.info("%s: thêm key '%s' vào '%s' (%s)", tr.meeting_id, e.key, t.id, e.utt)
            t.keys.append(e.key)
    return ExtractionResult(threads=list(by_id.values()), events=events)


class TwoPassExtractor:
    """Extractor M3: bản đồ chủ đề (lượt 1) → sự kiện theo đoạn song song (lượt 2) → gộp.

    Transcript ≤ `size` câu → 1 lần gọi, không bản đồ (hành vi M2).
    """

    def __init__(
        self,
        mapper: TopicMapper,
        extractor: ChunkEventExtractor,
        size: int,
        context: int,
        max_concurrency: int,
    ) -> None:
        self.mapper, self.extractor = mapper, extractor
        self.size, self.context, self.max_concurrency = size, context, max_concurrency
        self.name = f"{extractor.name}-2pass"

    def extract(self, tr: Transcript) -> ExtractionResult:
        if len(tr.utterances) <= self.size:
            return self.extractor.extract(tr)
        threads = self.mapper.map(tr)
        chunks = chunk(tr.utterances, self.size, self.context)
        with ThreadPoolExecutor(self.max_concurrency) as pool:
            results = list(pool.map(lambda c: self.extractor.extract_chunk(tr, threads, c), chunks))
        return merge(tr, threads, chunks, results)


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
        path = (self.directory / f"{tr.meeting_id}.json").resolve()
        if not path.is_relative_to(self.directory.resolve()) or not path.exists():
            raise LookupError(
                f"Không có sự kiện đã lưu cho cuộc họp '{tr.meeting_id}' trong {path.parent}"
            )
        return ExtractionResult.model_validate_json(path.read_text(encoding="utf-8"))
