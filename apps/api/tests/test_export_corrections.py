import datetime as dt
import json

from test_api_series import EVENTS, TEXT

from chot.adapters.parsing import parse_transcript
from chot.adapters.persistence import InMemoryRepository
from chot.eval.export_corrections import export_corrections
from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor
from chot.usecases.meetings import MeetingService


def test_exports_rejections_and_manual_fixes_only(tmp_path):
    svc = MeetingService(
        InMemoryRepository(), RulesLedgerBuilder(StaticExtractor(EVENTS)), parse_transcript
    )
    rec = svc.process(TEXT)
    ids = {i.content: i.id for i in rec.ledger.items}
    svc.answer(rec.id, ids["Mọi hoá đơn phải có mã PO"], "confirm")
    svc.answer(rec.id, ids["Khách chỉ dùng MoMo"], "reject")
    svc.review_item(rec.id, ids["Làm báo giá"], {"owner": "Bình"})

    assert export_corrections(svc.repo, tmp_path) == 2
    cases = json.loads((tmp_path / f"{rec.id}.json").read_text(encoding="utf-8"))
    assert {(c["item"]["id"], c["field"]) for c in cases} == {
        (ids["Khách chỉ dùng MoMo"], "status"),
        (ids["Làm báo giá"], "owner"),
    }
    owner = next(c for c in cases if c["field"] == "owner")
    assert (owner["old"], owner["new"]) == ("An", "Bình")
    assert owner["evidence"][0]["quote"]  # câu gốc để Nash gán nhãn lại


def test_owner_changed_while_confirming_is_a_correction_but_filling_a_gap_is_not(tmp_path):
    svc = MeetingService(
        InMemoryRepository(), RulesLedgerBuilder(StaticExtractor(EVENTS)), parse_transcript
    )
    rec = svc.process(TEXT)
    task = next(i.id for i in rec.ledger.items if i.content == "Làm báo giá")
    svc.answer(rec.id, task, "confirm", owner="Bình", deadline=dt.date(2026, 11, 1))

    assert export_corrections(svc.repo, tmp_path) == 1  # owner An → Bình; hạn trống → điền
    case = json.loads((tmp_path / f"{rec.id}.json").read_text(encoding="utf-8"))[0]
    assert (case["field"], case["old"], case["new"]) == ("owner", "An", "Bình")
