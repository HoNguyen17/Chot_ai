"""Gộp kết quả theo đoạn (SPEC M3 §3.4): bỏ câu ngữ cảnh, nối theo thứ tự câu, THREAD_UNMAPPED."""

from chot.domain.enums import EventKind as K
from chot.domain.models import Event, ExtractionResult, Participant, Thread, Transcript, Utterance
from chot.domain.reasons import ReasonCode as C
from chot.usecases.build_ledger import RulesLedgerBuilder, TwoPassExtractor

TR = Transcript(
    meeting_id="x",
    participants=[Participant(name="Bách", is_chair=True), Participant(name="Hạnh")],
    utterances=[
        Utterance(id=f"u{i:03d}", index=i, ts=i, speaker="Hạnh", text=f"vướng mắc số {i}")
        for i in range(1, 8)
    ],
)
MAP = [Thread(id="ship", title="Vận chuyển", keys=["biển"], utt_ids=["u001"])]


def ev(utt: str, thread: str = "ship", key: str | None = None, kind=K.BLOCKER) -> Event:
    n = int(utt[1:])
    return Event(
        utt=utt, thread=thread, kind=kind, speaker="Hạnh", key=key, quote=f"vướng mắc số {n}"
    )


class FakeMapper:
    def __init__(self) -> None:
        self.calls = 0

    def map(self, tr):
        self.calls += 1
        return [t.model_copy(deep=True) for t in MAP]


class FakeExtractor:
    """Trả sự kiện cho mọi câu nó thấy (cả câu ngữ cảnh — như LLM gán nhầm)."""

    name = "fake"

    def __init__(self, extra: dict[str, list[Event]] | None = None) -> None:
        self.single, self.chunks, self.extra = 0, [], extra or {}

    def extract(self, tr):
        self.single += 1
        return ExtractionResult(events=[ev(u.id) for u in tr.utterances])

    def extract_chunk(self, tr, threads, chunk):
        self.chunks.append(chunk)
        seen = [*chunk.context_ids, *chunk.label_ids]
        events = [ev(u) for u in seen] + self.extra.get(chunk.label_ids[0], [])
        return ExtractionResult(
            threads=[Thread(id="lạ", title="Chủ đề lạ")], events=list(reversed(events))
        )


def two_pass(extractor: FakeExtractor, size: int = 3) -> tuple[TwoPassExtractor, FakeMapper]:
    mapper = FakeMapper()
    return TwoPassExtractor(mapper, extractor, size=size, context=1, max_concurrency=2), mapper


def test_short_transcript_skips_topic_map_and_calls_once():
    fake = FakeExtractor()
    tp, mapper = two_pass(fake, size=7)
    tp.extract(TR)
    assert (mapper.calls, fake.single, fake.chunks) == (0, 1, [])


def test_one_call_per_chunk_and_context_events_dropped_in_utterance_order():
    fake = FakeExtractor()
    tp, mapper = two_pass(fake)
    out = tp.extract(TR)
    assert mapper.calls == 1 and len(fake.chunks) == 3
    assert [e.utt for e in out.events] == [f"u{i:03d}" for i in range(1, 8)]


def test_unknown_thread_kept_and_flagged_unmapped_item_asks():
    fake = FakeExtractor(extra={"u004": [ev("u005", thread="lạ")]})
    tp, _ = two_pass(fake)
    out = tp.extract(TR)
    assert {t.id: t.mapped for t in out.threads} == {"ship": True, "lạ": False}
    assert next(t for t in out.threads if t.id == "lạ").title == "Chủ đề lạ"

    ledger = RulesLedgerBuilder(tp).build(TR)
    codes = {i.thread: [r.code for r in i.reasons] for i in ledger.items}
    assert C.THREAD_UNMAPPED in codes["lạ"]
    assert C.THREAD_UNMAPPED not in codes["ship"]


def test_unknown_key_added_to_topic_map():
    fake = FakeExtractor(extra={"u001": [ev("u002", key="hàng không", kind=K.PROPOSE)]})
    tp, _ = two_pass(fake)
    out = tp.extract(TR)
    assert out.threads[0].keys == ["biển", "hàng không"]
