"""T1 / T2 (SPEC M3 §8.3): replay sự kiện của run M3 đã chọn (data/long/events_m3) — 0 token.

Sự kiện là output LLM thật (hai lượt, chia đoạn). Test đỏ = luật hoặc prompt hỏng, không nới test.
"""

from pathlib import Path

import pytest

from chot.adapters.parsing import parse_transcript_file
from chot.domain.enums import ItemType as T
from chot.domain.enums import ReviewState as RS
from chot.domain.enums import Status as S
from chot.domain.models import ExtractionResult, Item, Ledger
from chot.domain.reasons import ReasonCode as C
from chot.domain.review import initial_review_state
from chot.eval.metrics import GoldMeeting, ledger_as_gold, score_meeting
from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor

ROOT = Path(__file__).resolve().parents[3] / "data"
EVENTS = ROOT / "long" / "events_m3"


def replay(meeting: str, raw: Path) -> tuple[Ledger, object]:
    tr = parse_transcript_file(raw / f"{meeting}.txt")
    events = ExtractionResult.model_validate_json(
        (EVENTS / f"{meeting}.json").read_text(encoding="utf-8")
    )
    ledger = RulesLedgerBuilder(StaticExtractor(events)).build(tr)
    items = [i.model_copy(update={"review_state": initial_review_state(i)}) for i in ledger.items]
    return ledger.model_copy(update={"items": items}), tr


def pick(ledger: Ledger, type_: T, utts: set[str]) -> Item:
    """Mục cùng type có nhiều câu bằng chứng trùng `utts` nhất."""
    best = max(
        (i for i in ledger.items if i.type == type_),
        key=lambda i: len({e.utt for e in i.evidence} & utts),
    )
    assert {e.utt for e in best.evidence} & utts, f"không có {type_} nào ở {utts}"
    return best


def codes(item: Item) -> set[C]:
    return {r.code for r in item.reasons}


@pytest.fixture(scope="module")
def l4() -> tuple[Ledger, object]:
    return replay("L4", ROOT / "long" / "raw")


def test_t1_m01_alone_and_inside_l1_agree():
    alone, _ = replay("m01", ROOT / "raw")
    inside, _ = replay("L1", ROOT / "long" / "raw")
    # gold m01: D1 MoMo (u019, u005), O1 VNPay (u002, u017) → trong L1: u063/u005, u002/u061
    for type_, status, utts_alone, utts_l1 in [
        (T.DECISION, S.FINAL, {"u019", "u005"}, {"u063", "u005"}),
        (T.OPTION, S.SUPERSEDED, {"u002", "u017"}, {"u002", "u061"}),
    ]:
        a, b = pick(alone, type_, utts_alone), pick(inside, type_, utts_l1)
        assert (a.status, b.status) == (status, status), (a.content, b.content)
        assert codes(a) == codes(b)


def test_t2_l4_no_wrong_final(l4):
    ledger, tr = l4
    gold = GoldMeeting.model_validate_json(
        (ROOT / "long" / "gold" / "L4.json").read_text(encoding="utf-8")
    )
    counts = score_meeting(ledger_as_gold(ledger), gold, tr, ledger)
    assert counts.pred_final_wrong == 0, counts.errors


def test_t2_l4_ok_vay_di_at_chunk_start_is_final(l4):
    assert pick(l4[0], T.DECISION, {"u071"}).status == S.FINAL


@pytest.mark.xfail(
    strict=True,
    reason="Run c100-r2: LLM gán 'Ai đó gửi lại bản vẽ…' (u124) vào mã câu u121 → grounding "
    "loại task đúng luật. Run c70-r2 bắt được OWNER_MISSING. Nash duyệt xfail 22/10/2026.",
)
def test_t2_l4_task_without_owner_asks_who(l4):
    assert C.OWNER_MISSING in codes(pick(l4[0], T.TASK, {"u124", "u121", "u198"}))


def test_t2_l4_sea_route_keeps_road_fallback(l4):
    assert C.FALLBACK_KEPT in codes(pick(l4[0], T.DECISION, {"u114", "u115"}))


def test_t2_l4_no_knowledge_enters_store_without_confirmation(l4):
    """Tri thức lâu dài (kể cả tin đồn u040) luôn phải chờ người duyệt — không auto_accepted."""
    durable = [i for i in l4[0].items if i.type == T.KNOWLEDGE and i.scope == "durable"]
    assert all(i.review_state == RS.PENDING for i in durable)
