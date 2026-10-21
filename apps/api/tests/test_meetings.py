"""Use case duyệt cuộc họp (M3): trả lời câu hỏi, nhật ký append-only, khoá xuất bản khi còn câu hỏi."""

import pytest

from chot.adapters.parsing import parse_transcript
from chot.adapters.persistence import InMemoryRepository
from chot.domain.enums import ReviewAction as A
from chot.domain.enums import ReviewState as RS
from chot.domain.enums import Status as S
from chot.domain.models import Event, ExtractionResult
from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor
from chot.usecases.meetings import MeetingService

TEXT = (
    "# participants: Sếp (chủ trì); An; Bình\n"
    "[00:01] An: Em đề xuất dùng A.\n"
    "[00:02] Sếp: Ừ.\n"
    "[00:03] Sếp: Ai đó gọi bên in tem nhé.\n"
    "[00:04] Sếp: Chốt dùng kho Bình Dương."
)
EVENTS = [
    Event(utt="u001", thread="a", kind="propose", speaker="An", key="A", content="Dùng A"),
    Event(
        utt="u003", thread="b", kind="assign", speaker="Sếp", key="tem", content="Gọi bên in tem"
    ),
    Event(
        utt="u004", thread="c", kind="propose", speaker="Sếp", key="BD", content="Kho Bình Dương"
    ),
    Event(
        utt="u004",
        thread="c",
        kind="agree",
        speaker="Sếp",
        key="BD",
        quote="Chốt dùng kho Bình Dương",
    ),
]


@pytest.fixture
def svc():
    builder = RulesLedgerBuilder(StaticExtractor(ExtractionResult(events=EVENTS)))
    return MeetingService(InMemoryRepository(), builder, parse_transcript)


def _items(record):
    return {i.content: i for i in record.ledger.items}


def test_process_sets_review_state(svc):
    items = _items(svc.process(TEXT))
    assert items["Dùng A"].review_state == RS.PENDING  # NOD_ONLY
    assert items["Gọi bên in tem"].review_state == RS.PENDING  # OWNER_MISSING
    assert items["Kho Bình Dương"].review_state == RS.AUTO_ACCEPTED


def test_answer_changes_status_and_logs_append_only(svc):
    rec = svc.process(TEXT)
    d = _items(rec)["Dùng A"]
    rec = svc.answer(rec.id, d.id, A.CONFIRM, by="Nash")
    assert (_items(rec)["Dùng A"].status, _items(rec)["Dùng A"].review_state) == (
        S.FINAL,
        RS.CONFIRMED,
    )
    rec = svc.answer(rec.id, d.id, A.DEFER, by="Nash")
    log = [(a.item_id, a.action, a.old, a.new, a.by) for a in rec.review_log]
    assert log == [
        (d.id, A.CONFIRM, S.NEEDS_CONFIRMATION, S.FINAL, "Nash"),
        (d.id, A.DEFER, S.FINAL, S.DEFERRED, "Nash"),
    ]


def test_answer_rejects_owner_outside_meeting(svc):
    rec = svc.process(TEXT)
    t = _items(rec)["Gọi bên in tem"]
    with pytest.raises(ValueError, match="không có trong cuộc họp"):
        svc.answer(rec.id, t.id, A.CONFIRM, owner="Người lạ")
    rec = svc.answer(rec.id, t.id, A.CONFIRM, owner="Bình")
    assert _items(rec)["Gọi bên in tem"].owner == "Bình"


def test_publish_locked_while_pending_and_deferred_does_not_block(svc):
    rec = svc.process(TEXT)
    d, t = _items(rec)["Dùng A"], _items(rec)["Gọi bên in tem"]
    with pytest.raises(ValueError, match="2 câu hỏi"):
        svc.publish(rec.id)
    svc.answer(rec.id, d.id, A.DEFER)
    with pytest.raises(ValueError, match="1 câu hỏi"):
        svc.publish(rec.id)
    svc.answer(rec.id, t.id, A.DEFER)
    assert svc.publish(rec.id).published


def test_legacy_approved_still_unlocks_publish(svc):
    rec = svc.process(TEXT)
    for i in rec.ledger.items:
        svc.review_item(rec.id, i.id, {"approved": True})
    rec = svc.publish(rec.id)
    assert (
        rec.published and _items(rec)["Dùng A"].status == S.NEEDS_CONFIRMATION
    )  # không đổi status


def test_manual_status_edit_must_stay_in_table(svc):
    rec = svc.process(TEXT)
    t = _items(rec)["Gọi bên in tem"]
    with pytest.raises(ValueError, match="không hợp lệ"):
        svc.review_item(rec.id, t.id, {"status": "final"})


TEXT_K = TEXT + "\n[00:05] An: Từ nay mọi hoá đơn phải có mã PO."
EVENTS_K = [
    *EVENTS,
    Event(
        utt="u005",
        thread="d",
        kind="info",
        speaker="An",
        content="Hoá đơn phải có PO",
        quote="Từ nay mọi hoá đơn phải có mã PO",
    ),
]


def test_export_handles_noted_and_reviewer_evidence():
    from chot.adapters.export import to_markdown_minutes

    builder = RulesLedgerBuilder(StaticExtractor(ExtractionResult(events=EVENTS_K)))
    svc = MeetingService(InMemoryRepository(), builder, parse_transcript)
    rec = svc.process(TEXT_K)
    k = _items(rec)["Hoá đơn phải có PO"]
    rec = svc.answer(rec.id, k.id, A.CONFIRM, by="Nash")
    md = to_markdown_minutes(rec.transcript, rec.ledger)
    assert "Hoá đơn phải có PO" in md and "None" not in md


def test_answer_logs_every_changed_field(svc):
    rec = svc.process(TEXT)
    t = _items(rec)["Gọi bên in tem"]
    rec = svc.answer(rec.id, t.id, A.CONFIRM, owner="Bình", by="Nash")
    log = [(a.field, a.old, a.new, a.action) for a in rec.review_log]
    assert log == [
        ("status", S.NEEDS_CONFIRMATION, S.OPEN, A.CONFIRM),
        ("owner", None, "Bình", A.CONFIRM),
    ]


def test_owner_given_on_reject_is_ignored(svc):
    rec = svc.process(TEXT)
    t = _items(rec)["Gọi bên in tem"]
    rec = svc.answer(rec.id, t.id, A.REJECT, owner="Bình")
    assert _items(rec)["Gọi bên in tem"].owner is None


def test_legacy_approved_is_logged(svc):
    rec = svc.process(TEXT)
    d = _items(rec)["Dùng A"]
    rec = svc.review_item(rec.id, d.id, {"approved": True})
    assert [(a.field, a.new, a.action) for a in rec.review_log] == [
        ("review_state", RS.CONFIRMED, A.CONFIRM)
    ]
