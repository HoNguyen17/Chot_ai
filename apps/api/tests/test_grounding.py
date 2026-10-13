from chot.domain.enums import ItemType, Status
from chot.domain.grounding import apply_grounding
from chot.domain.models import Evidence, Item, Ledger


def _ledger(tr, *items):
    return Ledger(meeting_id=tr.meeting_id, items=list(items))


def test_tier1_drops_fabricated_quote(mini):
    item = Item(
        id="D1",
        type=ItemType.DECISION,
        content="Dùng B",
        status=Status.FINAL,
        decided_by="Sếp",
        evidence=[Evidence(utt="u005", quote="Chốt dùng C luôn")],  # không có trong câu u005
    )
    led, report = apply_grounding(_ledger(mini, item), mini)
    assert led.items == [] and report.items_dropped == ["D1"]
    assert report.tier1_rate == 0.0


def test_tier2_downgrades_final_from_non_chair(mini):
    item = Item(
        id="D1",
        type=ItemType.DECISION,
        content="Dùng A",
        status=Status.FINAL,
        decided_by="An",
        evidence=[Evidence(utt="u001", quote="Em đề xuất dùng A")],
    )
    led, report = apply_grounding(_ledger(mini, item), mini)
    assert led.items[0].status == Status.NEEDS_CONFIRMATION
    assert report.items_downgraded == ["D1"]


def test_tier2_downgrades_final_whose_evidence_is_hedged(mini):
    item = Item(
        id="D1",
        type=ItemType.DECISION,
        content="Dùng B",
        status=Status.FINAL,
        decided_by="Sếp",
        evidence=[Evidence(utt="u003", quote="Tạm thời đi B nhé")],
    )
    led, _ = apply_grounding(_ledger(mini, item), mini)
    assert led.items[0].status == Status.NEEDS_CONFIRMATION


def test_valid_final_passes(mini):
    item = Item(
        id="D1",
        type=ItemType.DECISION,
        content="Dùng B",
        status=Status.FINAL,
        decided_by="Sếp",
        evidence=[Evidence(utt="u005", quote="chốt dùng b")],  # khác hoa/thường vẫn khớp
    )
    led, report = apply_grounding(_ledger(mini, item), mini)
    assert led.items[0].status == Status.FINAL and report.tier1_rate == 1.0


def test_tier2_keeps_absent_owner():
    # Quy tắc 12: người vắng mặt có tên trong header — không phải người bịa
    from chot.adapters.parsing import parse_transcript

    tr = parse_transcript(
        "# participants: Sếp (chủ trì); An\n# absent: Chi (Kế toán)\n[00:01] Sếp: Chi làm báo cáo nhé."
    )
    item = Item(
        id="T1",
        type=ItemType.TASK,
        content="Làm báo cáo",
        status=Status.NEEDS_CONFIRMATION,
        owner="Chi",
        evidence=[Evidence(utt="u001", quote="Chi làm báo cáo nhé")],
    )
    led, _ = apply_grounding(_ledger(tr, item), tr)
    assert led.items[0].owner == "Chi"
