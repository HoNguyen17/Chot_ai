"""Composition root: nơi DUY NHẤT nối adapter cụ thể vào use case."""

from __future__ import annotations

from functools import lru_cache

from chot.adapters.baselines import KeywordBaseline
from chot.adapters.llm import LLMEventExtractor, OpenAICompatibleClient
from chot.adapters.parsing import parse_transcript
from chot.adapters.persistence import InMemoryRepository
from chot.config import Settings, get_settings
from chot.domain.models import Ledger, Transcript
from chot.usecases.build_ledger import DirectoryReplayExtractor, RulesLedgerBuilder
from chot.usecases.meetings import MeetingService
from chot.usecases.ports import LedgerBuilder


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


def make_builder(settings: Settings) -> LedgerBuilder:
    if settings.ledger_builder == "llm":
        client = OpenAICompatibleClient(
            model=settings.llm_model, api_key=settings.llm_api_key, base_url=settings.llm_base_url
        )
        return RulesLedgerBuilder(LLMEventExtractor(client))
    if settings.ledger_builder == "replay":
        replay = RulesLedgerBuilder(DirectoryReplayExtractor(settings.replay_events_dir))
        return FallbackBuilder(replay, KeywordBaseline())
    return KeywordBaseline()


@lru_cache
def get_service() -> MeetingService:
    settings = get_settings()
    return MeetingService(
        repo=InMemoryRepository(), builder=make_builder(settings), parser=parse_transcript
    )
