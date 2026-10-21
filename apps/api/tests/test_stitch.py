"""Kiểm tra ghép họp dài L1–L3: không mất / trùng câu, evidence và tên nhất quán, luật chạy y như nguồn."""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

import pytest

from chot.adapters.parsing import parse_transcript, parse_transcript_file
from chot.domain.models import ExtractionResult
from chot.eval.metrics import GoldMeeting, ledger_as_gold, score_meeting, summarize
from chot.eval.stitch import Stitched
from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
ORACLE = Path(__file__).parent / "fixtures" / "oracle_events"
PLAN_IDS = ["L1", "L2", "L3"]
MIN_RETURN_GAP = 40


def _stitched(pid: str) -> Stitched:
    plan = json.loads((DATA / "long" / "plans" / f"{pid}.json").read_text(encoding="utf-8"))
    return Stitched(plan, DATA, ORACLE)


@pytest.fixture(scope="module", params=PLAN_IDS)
def st(request) -> Stitched:
    return _stitched(request.param)


def _source_utt(st: Stitched) -> dict[str, tuple[str, str]]:
    return {new: key for key, new in st.umap.items()}


def test_no_utterance_lost_or_duplicated(st: Stitched):
    sources = {s: parse_transcript_file(DATA / "raw" / f"{s}.txt") for s in st.sources}
    total = sum(len(t.utterances) for t in sources.values())
    tr = parse_transcript(st.transcript_text())  # parser M2 đọc được
    assert len(tr.utterances) == total == len(st.umap) == st.count
    assert [u.id for u in tr.utterances] == [f"u{i:03d}" for i in range(1, total + 1)]
    assert all(a.ts <= b.ts for a, b in zip(tr.utterances, tr.utterances[1:], strict=False))
    for (src, old), new in st.umap.items():  # câu mới = câu nguồn đã đổi tên, không đổi gì khác
        o = sources[src].utt(old)
        n = tr.utt(new)
        assert (n.speaker, n.text) == (st.sub[src](o.speaker), st.sub[src](o.text))


@pytest.mark.parametrize("folder", ["gold", "answer_key"])
def test_evidence_points_to_same_sentence(st: Stitched, folder: str):
    tr = parse_transcript(st.transcript_text())
    back = _source_utt(st)
    sources = {s: parse_transcript_file(DATA / "raw" / f"{s}.txt") for s in st.sources}
    for it in st.gold(DATA / folder)["items"]:
        srcs = set()
        for e in it["evidence"]:
            src, old = back[e]
            srcs.add(src)
            assert tr.utt(e).text == st.sub[src](sources[src].utt(old).text), it["id"]
        assert len(srcs) == 1 and it["id"].startswith(f"{srcs.pop()}."), it["id"]


def test_threads_never_shared_between_sources(st: Stitched):
    back = _source_utt(st)
    owner: dict[str, set[str]] = {}
    for it in st.gold(DATA / "gold")["items"]:
        owner.setdefault(it["thread"], set()).update(back[e][0] for e in it["evidence"])
    assert all(len(v) == 1 for v in owner.values()), {t: v for t, v in owner.items() if len(v) > 1}


def test_names_are_consistent(st: Stitched):
    target = {p.split(" (")[0] for p in st.plan["participants"] + st.plan["absent"]}
    tr = parse_transcript(st.transcript_text())
    back = _source_utt(st)
    leaked = []
    for u in tr.utterances:  # tên nguồn đã đổi không được còn sót trong câu của chính nguồn đó
        src = back[u.id][0]
        gone = set(st.plan["roster"][src]) - target
        text = f"{u.speaker}: {u.text}"
        leaked += [(u.id, n) for n in gone if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", text)]
    assert not leaked, leaked
    assert {u.speaker for u in tr.utterances} <= target
    for it in st.gold(DATA / "gold")["items"]:
        assert {it.get("owner"), it.get("decided_by")} - {None} <= target, it["id"]


def test_relative_deadlines_flagged_and_recomputed(st: Stitched):
    for it in st.gold(DATA / "gold")["items"]:
        phrase = it.get("deadline_text")
        if not phrase:
            continue
        if re.search(r"\d{1,2}/\d{1,2}", phrase):
            assert "needs_review" not in it, it["id"]
        elif it.get("deadline"):
            assert it["needs_review"] is True, it["id"]


def test_long_meeting_has_threads_that_return_after_gap(st: Stitched):
    """Mỗi cuộc ≥ 2 chủ đề bị cắt rồi quay lại sau ≥ 40 câu."""
    pos = {k: int(v[1:]) for k, v in st.umap.items()}
    blocks = st.plan["blocks"]
    span = [
        (b["source"], pos[(b["source"], b["from"])], pos[(b["source"], b["to"])]) for b in blocks
    ]
    returned = set()
    for it in st.gold(DATA / "gold")["items"]:
        utts = sorted(int(e[1:]) for e in it["evidence"])
        for a, b in itertools.pairwise(utts):
            same_block = any(lo <= a <= hi and lo <= b <= hi for _, lo, hi in span)
            if not same_block and b - a > MIN_RETURN_GAP:
                returned.add(it["thread"])
    assert len(returned) >= 2, returned


def test_oracle_events_replay_matches_stitched_answer_key(st: Stitched):
    """Ghép không đổi nghĩa: sự kiện chuẩn của nguồn + luật hiện tại = đáp án ghép."""
    tr = parse_transcript(st.transcript_text())
    extraction = ExtractionResult.model_validate(st.events())
    ledger = RulesLedgerBuilder(StaticExtractor(extraction)).build(tr)
    key = GoldMeeting.model_validate(st.gold(DATA / "answer_key"))
    s = summarize(score_meeting(ledger_as_gold(ledger), key, tr, ledger))
    assert s["wrong_final_rate"] == 0
    for k in (
        "final_state_accuracy",
        "item_precision",
        "item_recall",
        "status_accuracy_matched",
        "owner_accuracy",
        "deadline_accuracy",
        "grounding_tier1",
    ):
        assert s[k] == 1.0, (k, s[k])
    assert s["hallucinated_people"] == 0


@pytest.mark.parametrize(
    "path", sorted((DATA / "long" / "raw").glob("L*.txt")), ids=lambda p: p.stem
)
def test_parser_reads_long_transcripts(path: Path):
    tr = parse_transcript_file(path)
    assert tr.meeting_id == path.stem and len(tr.utterances) >= 140 and tr.chairs


def _plan_with(blocks: list[dict]) -> Stitched:
    plan = json.loads((DATA / "long" / "plans" / "L1.json").read_text(encoding="utf-8"))
    return Stitched({**plan, "blocks": blocks}, DATA, ORACLE)


def test_block_starting_with_backchannel_is_rejected():
    # m01 u003 = "Dạ." đáp lại u002; u009 = "Dạ vâng." — không được đứng đầu khối
    with pytest.raises(ValueError, match="phụ thuộc"):
        _plan_with(
            [
                {"source": "m02", "from": "u001", "to": "u005"},
                {"source": "m01", "from": "u003", "to": "u005"},
            ]
        )


def test_overlapping_blocks_are_rejected():
    with pytest.raises(ValueError, match="hai khối"):
        _plan_with(
            [
                {"source": "m01", "from": "u001", "to": "u014"},
                {"source": "m01", "from": "u010", "to": "u026"},
            ]
        )
