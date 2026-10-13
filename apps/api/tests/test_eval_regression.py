"""Hồi quy cho luật: với sự kiện "chuẩn" (oracle), luật phải tái tạo đúng đáp án.

Nếu test này đỏ sau khi bạn sửa luật → bạn vừa làm luật lệch khỏi hướng dẫn gán nhãn.
Lưu ý: đây KHÔNG đo chất lượng LLM (oracle do người viết). Chất lượng LLM đo bằng `make eval-llm`.
"""

from pathlib import Path

from chot.adapters.baselines import KeywordBaseline
from chot.adapters.parsing import parse_transcript_file
from chot.domain.models import ExtractionResult
from chot.eval.metrics import Counts, GoldMeeting, ledger_as_gold, score_meeting, summarize
from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor

FIX = Path(__file__).parent / "fixtures" / "oracle_events"


def _run(data_dir, make_builder):
    total = Counts()
    for gpath in sorted((data_dir / "answer_key").glob("m*.json")):
        gold = GoldMeeting.model_validate_json(gpath.read_text(encoding="utf-8"))
        tr = parse_transcript_file(data_dir / "raw" / f"{gold.meeting_id}.txt")
        ledger = make_builder(gold.meeting_id).build(tr)
        total.add(score_meeting(ledger_as_gold(ledger), gold, tr, ledger))
    return summarize(total)


def test_rules_reproduce_answer_key_from_oracle_events(data_dir):
    def make(mid):
        extraction = ExtractionResult.model_validate_json(
            (FIX / f"{mid}.json").read_text(encoding="utf-8")
        )
        return RulesLedgerBuilder(StaticExtractor(extraction))

    s = _run(data_dir, make)
    assert s["wrong_final_rate"] == 0.0
    assert s["final_state_accuracy"] == 1.0
    assert s["supersession_recall"] == 1.0
    assert s["item_precision"] == 1.0 and s["item_recall"] == 1.0
    assert s["grounding_tier1"] == 1.0


def test_keyword_baseline_records_intermediate_opinions_as_decisions(data_dir):
    """Bằng chứng cho giả thuyết #4: keyword không đủ."""
    s = _run(data_dir, lambda _: KeywordBaseline())
    assert s["wrong_final_rate"] > 0.3
    assert s["supersession_recall"] == 0.0
