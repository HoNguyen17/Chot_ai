"""Composition root: nơi DUY NHẤT nối adapter cụ thể vào use case."""

from __future__ import annotations

import hmac
import logging
import threading
import time
from collections import deque
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

from chot.adapters.baselines import KeywordBaseline
from chot.adapters.llm import (
    LLMClient,
    LLMEventExtractor,
    LLMTopicMapper,
    OpenAICompatibleClient,
)
from chot.adapters.parsing import parse_transcript
from chot.adapters.persistence import InMemoryRepository, PostgresRepository
from chot.config import Settings, get_settings
from chot.domain.models import Ledger, Transcript
from chot.usecases.build_ledger import (
    DirectoryReplayExtractor,
    RulesLedgerBuilder,
    TwoPassExtractor,
)
from chot.usecases.meetings import MeetingRepository, MeetingService, Series
from chot.usecases.ports import LedgerBuilder

log = logging.getLogger(__name__)


class FallbackBuilder:
    """Thử builder chính; nếu không có dữ liệu (LookupError) thì dùng builder dự phòng."""

    def __init__(self, primary: LedgerBuilder, fallback: LedgerBuilder) -> None:
        self.primary, self.fallback = primary, fallback
        self.name = f"{primary.name}|{fallback.name}"

    def build(self, tr: Transcript) -> Ledger:
        try:
            return self.primary.build(tr)
        except LookupError:
            return self.fallback.build(tr)


class ExactSampleReplay:
    """Chỉ replay khi transcript giống hệt mẫu đã lưu (<dir>/<id>.txt).

    Mẫu bị sửa (dù còn header `# meeting: m01`) → LookupError → FallbackBuilder gọi LLM,
    nên kết quả đã lưu không bị gán cho transcript khác và record mẫu không bị ghi đè.
    """

    def __init__(self, builder: LedgerBuilder, directory: str) -> None:
        self.builder, self.name = builder, builder.name
        self.samples = {
            p.stem: parse_transcript(p.read_text(encoding="utf-8"))
            for p in Path(directory).glob("*.txt")
        }

    def build(self, tr: Transcript) -> Ledger:
        if self.samples.get(tr.meeting_id) != tr:
            raise LookupError(f"'{tr.meeting_id}' không phải transcript mẫu nguyên văn")
        return self.builder.build(tr)


# IP và mã truy cập của request hiện tại — api/main.py đặt trước khi xử lý.
client_ip: ContextVar[str] = ContextVar("client_ip", default="?")
access_code: ContextVar[str] = ContextVar("access_code", default="")


class RateLimitExceeded(Exception):
    """Hết lượt gọi LLM trong cửa sổ hiện tại (theo IP hoặc toàn cục)."""


class AccessDenied(Exception):
    """Thiếu hoặc sai mã truy cập khi transcript cần gọi LLM."""


class RateLimiter:
    """Cửa sổ trượt: tối đa `per_key` lượt mỗi IP và `total` lượt toàn cục trong `window` giây."""

    # ponytail: in-memory, 1 instance — đổi sang Redis nếu scale
    def __init__(self, per_key: int, total: int, window: float = 3600.0) -> None:
        self.per_key, self.total, self.window = per_key, total, window
        self.hits: dict[str, deque[float]] = {}
        self.lock = threading.Lock()

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self.lock:
            for k, limit in (("*", self.total), (key, self.per_key)):
                q = self.hits.get(k, deque())
                while q and q[0] <= now - self.window:
                    q.popleft()
                if len(q) >= limit:
                    raise RateLimitExceeded("Hết lượt gọi LLM")
            # Chỉ tạo key khi lượt được chấp nhận → IP giả bị từ chối không làm phình bộ nhớ.
            for k in (key, "*"):
                self.hits.setdefault(k, deque()).append(now)


class LimitedBuilder:
    """Chỉ kiểm mã + tính lượt khi thật sự gọi builder bên trong (LLM) — replay thì không.

    `code` = mã truy cập cấu hình; `required` = bắt buộc có mã (demo công khai), nên
    quên đặt mã thì từ chối hết thay vì để lộ key.
    """

    def __init__(
        self,
        builder: LedgerBuilder,
        limiter: RateLimiter,
        code: str | None = None,
        required: bool = False,
    ) -> None:
        self.builder, self.limiter, self.name = builder, limiter, builder.name
        self.code, self.required = code, required

    def build(self, tr: Transcript) -> Ledger:
        # Kiểm mã trước khi tính lượt → đoán sai không ăn vào lượt của người dùng thật.
        if self.code or self.required:
            given = access_code.get().encode()
            if not self.code or not hmac.compare_digest(given, self.code.encode()):
                raise AccessDenied("Thiếu hoặc sai mã truy cập")
        self.limiter.hit(client_ip.get())
        return self.builder.build(tr)


def make_extractor(settings: Settings, client: LLMClient) -> TwoPassExtractor:
    return TwoPassExtractor(
        LLMTopicMapper(client),
        LLMEventExtractor(client),
        size=settings.chunk_size,
        context=settings.chunk_context,
        max_concurrency=settings.llm_max_concurrency,
    )


def make_builder(settings: Settings, client: LLMClient | None = None) -> LedgerBuilder:
    if settings.ledger_builder == "llm":
        client = client or OpenAICompatibleClient(
            model=settings.llm_model, api_key=settings.llm_api_key, base_url=settings.llm_base_url
        )
        limiter = RateLimiter(settings.llm_rate_limit_per_hour, settings.llm_global_limit_per_hour)
        llm = LimitedBuilder(
            RulesLedgerBuilder(make_extractor(settings, client)),
            limiter,
            code=settings.llm_access_code,
            required=settings.public_demo,
        )
        replay = RulesLedgerBuilder(DirectoryReplayExtractor(settings.replay_events_dir))
        return FallbackBuilder(ExactSampleReplay(replay, settings.replay_events_dir), llm)
    if settings.ledger_builder == "replay":
        replay = RulesLedgerBuilder(DirectoryReplayExtractor(settings.replay_events_dir))
        return FallbackBuilder(replay, KeywordBaseline())
    return KeywordBaseline()


def make_repo(settings: Settings) -> MeetingRepository:
    """Có DATABASE_URL → Postgres (Supabase), không có → RAM. Không in DSN ra log."""
    if settings.database_url:
        return PostgresRepository(settings.database_url)
    return InMemoryRepository()


# Nhóm họp mẫu: chỉ xem, id công khai (không cần bí mật vì không sửa được).
SAMPLE_SERIES_ID = "mau-chot-m01-m05"
LONG_SAMPLE_SERIES_ID = "mau-chot-hop-dai"
SAMPLE_SERIES = (
    (SAMPLE_SERIES_ID, "Nhóm họp mẫu (m01–m05)", ("m01", "m02", "m03", "m04", "m05")),
    # Họp dài 148–200 câu: sự kiện của run M3 20261021-153854-llm-m3-long-c100-r2
    (LONG_SAMPLE_SERIES_ID, "Nhóm họp mẫu — họp dài (L1–L4)", ("L1", "L2", "L3", "L4")),
)


def seed_sample_series(svc: MeetingService, events_dir: str) -> None:
    """Nạp các nhóm mẫu bằng replay sự kiện đã lưu — không bao giờ gọi LLM."""
    builder = RulesLedgerBuilder(DirectoryReplayExtractor(events_dir))
    for series_id, name, meetings in SAMPLE_SERIES:
        paths = [Path(events_dir) / f"{m}.txt" for m in meetings]
        if missing := [p.name for p in paths if not p.exists()]:
            log.warning(
                "Không nạp nhóm mẫu %s: thiếu %s trong REPLAY_EVENTS_DIR", series_id, missing
            )
            continue
        svc.seed_series(
            Series(id=series_id, name=name, read_only=True),
            [p.read_text(encoding="utf-8") for p in paths],
            builder,
        )


@lru_cache
def get_service() -> MeetingService:
    settings = get_settings()
    svc = MeetingService(
        repo=make_repo(settings), builder=make_builder(settings), parser=parse_transcript
    )
    seed_sample_series(svc, settings.replay_events_dir)
    return svc
