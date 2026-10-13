"""Unit test cho luật suy trạng thái (PRD mục 6, Q3). Không cần LLM."""

from chot.domain.enums import EventKind as K
from chot.domain.enums import ItemType, Status
from chot.domain.models import Event, ExtractionResult, Thread
from chot.domain.status_rules import build_ledger


def ev(utt, kind, speaker, key=None, thread="t", **kw):
    return Event(utt=utt, thread=thread, kind=kind, speaker=speaker, key=key, **kw)


def ledger_for(tr, events):
    return build_ledger(
        tr, ExtractionResult(threads=[Thread(id="t", title="Chủ đề")], events=events)
    )


def decisions(ledger):
    return [i for i in ledger.items if i.type == ItemType.DECISION]


def test_a_then_b_final_supersedes_a(mini):
    led = ledger_for(
        mini,
        [
            ev("u001", K.PROPOSE, "An", "A", content="Dùng A"),
            ev("u002", K.PROPOSE, "Bình", "B", content="Dùng B"),
            ev("u003", K.AGREE, "Sếp", "B", quote="Tạm thời đi B nhé"),
            ev("u005", K.AGREE, "Sếp", "B", quote="Chốt dùng B", content="Dùng B"),
        ],
    )
    (d,) = decisions(led)
    assert d.status == Status.FINAL and d.content == "Dùng B" and d.decided_by == "Sếp"
    assert d.evidence[0].utt == "u005"  # bằng chứng là câu chốt sau cùng
    (opt,) = [i for i in led.items if i.type == ItemType.OPTION]
    assert opt.content == "Dùng A" and opt.status == Status.SUPERSEDED
    assert d.supersedes == [opt.id]


def test_tentative_never_reconfirmed_needs_confirmation(mini):
    led = ledger_for(
        mini,
        [
            ev("u001", K.PROPOSE, "An", "A"),
            ev("u002", K.PROPOSE, "Bình", "B"),
            ev("u003", K.AGREE, "Sếp", "B", quote="Tạm thời đi B nhé"),
        ],
    )
    (d,) = decisions(led)
    assert d.status == Status.NEEDS_CONFIRMATION
    # Chưa có quyết định cuối → phương án A vẫn mở, KHÔNG bị gắn "bị thay thế"
    assert all(i.status == Status.OPEN for i in led.items if i.type == ItemType.OPTION)


def test_agreement_by_non_chair_is_not_final(mini):
    led = ledger_for(
        mini, [ev("u002", K.PROPOSE, "Bình", "B"), ev("u004", K.AGREE, "An", "B", quote="Dạ")]
    )
    assert decisions(led)[0].status == Status.NEEDS_CONFIRMATION


def test_reopen_after_agree_then_defer(mini):
    led = ledger_for(
        mini,
        [
            ev("u001", K.PROPOSE, "An", "A"),
            ev("u003", K.AGREE, "Sếp", "A", quote="đi B"),
            ev("u004", K.REOPEN, "Sếp"),
            ev("u005", K.DEFER, "Sếp"),
        ],
    )
    (d,) = decisions(led)
    assert d.status == Status.DEFERRED


def test_objection_after_agree_then_reaffirm_stays_final(mini):
    led = ledger_for(
        mini,
        [
            ev("u003", K.AGREE, "Sếp", "B", quote="đi B nhé"),
            ev("u004", K.OBJECT, "An", "B"),
            ev("u005", K.AGREE, "Sếp", "B", quote="Chốt dùng B"),
        ],
    )
    assert decisions(led)[0].status == Status.FINAL


def test_no_agreement_becomes_open_question(mini):
    led = ledger_for(mini, [ev("u001", K.PROPOSE, "An", "A"), ev("u002", K.OBJECT, "Bình", "A")])
    (q,) = led.items
    assert q.type == ItemType.OPEN_QUESTION and q.status == Status.OPEN


def test_task_commit_vs_backchannel_vs_decline(mini):
    led = ledger_for(
        mini,
        [
            ev("u006", K.ASSIGN, "Sếp", "x", owner="An", deadline_text="thứ Sáu", content="Việc X"),
            ev("u007", K.COMMIT, "An", "x", owner="An", quote="Dạ vâng."),  # backchannel
            ev("u008", K.ASSIGN, "Sếp", "y", owner="Bình", content="Việc Y"),
            ev("u009", K.DECLINE, "Bình", "y", owner="Bình", quote="để em xem lại"),
            ev(
                "u010",
                K.ASSIGN,
                "Bình",
                "z",
                owner="Bình",
                content="Tài liệu Z",
                quote="Em sẽ viết tài liệu Z cuối tuần này",
            ),
        ],
    )
    tasks = {i.content: i for i in led.items if i.type == ItemType.TASK}
    assert tasks["Việc X"].status == Status.NEEDS_CONFIRMATION
    assert str(tasks["Việc X"].deadline) == "2026-10-09"
    assert tasks["Việc Y"].status == Status.NEEDS_CONFIRMATION
    assert tasks["Tài liệu Z"].status == Status.OPEN  # tự nhận, không rào đón
    assert str(tasks["Tài liệu Z"].deadline) == "2026-10-11"


def test_unknown_owner_is_dropped_not_invented(mini):
    led = ledger_for(mini, [ev("u006", K.ASSIGN, "Sếp", "x", owner="Người Lạ", content="Việc X")])
    (t,) = led.items
    assert t.owner is None and t.status == Status.NEEDS_CONFIRMATION
    assert any("không có trong danh sách" in f for f in t.flags)


# --- P3 vòng 2: quy ước Nash 5/10/11/12 + agree của người không chủ trì ---
from chot.adapters.parsing import parse_transcript  # noqa: E402


def _tr(*lines, participants="Sếp (chủ trì); An; Bình", absent=None):
    head = ["# meeting: t2", "# date: 2026-10-05", f"# participants: {participants}"]
    if absent:
        head.append(f"# absent: {absent}")
    return parse_transcript("\n".join(head + list(lines)))


def test_non_chair_same_key_agree_after_chair_keeps_final(mini):
    led = ledger_for(
        mini,
        [
            ev("u001", K.PROPOSE, "An", "A"),
            ev("u002", K.PROPOSE, "Bình", "B"),
            ev("u005", K.AGREE, "Sếp", "B", quote="Chốt dùng B"),
            ev("u006", K.AGREE, "An", "B", quote="An làm việc X"),  # người khác "ok" theo
        ],
    )
    (d,) = decisions(led)
    assert d.status == Status.FINAL and d.decided_by == "Sếp"


def test_non_chair_other_key_agree_after_chair_still_blocks(mini):
    led = ledger_for(
        mini,
        [
            ev("u001", K.PROPOSE, "An", "A"),
            ev("u005", K.AGREE, "Sếp", "B", quote="Chốt dùng B"),
            ev("u006", K.AGREE, "An", "A", quote="An làm việc X"),
        ],
    )
    assert decisions(led)[0].status == Status.NEEDS_CONFIRMATION


def test_co_chair_objection_not_withdrawn_needs_confirmation():
    tr = _tr(
        "[00:10] An: Em đề xuất A.",
        "[00:20] Bình: Em đề xuất B.",
        "[00:30] Hai: Anh thấy B rủi ro.",
        "[00:40] Sếp: Chị quyết đi B.",
        "[00:50] Hai: Ok, anh đồng ý đi B.",
        participants="Sếp (chủ trì); Hai (chủ trì); An; Bình",
    )
    evs = [
        ev("u001", K.PROPOSE, "An", "A"),
        ev("u002", K.PROPOSE, "Bình", "B"),
        ev("u003", K.OBJECT, "Hai", "B", quote="B rủi ro"),
        ev("u004", K.AGREE, "Sếp", "B", quote="Chị quyết đi B"),
    ]
    (d,) = decisions(ledger_for(tr, evs))
    assert d.status == Status.NEEDS_CONFIRMATION
    assert any("đồng chủ trì" in f for f in d.flags)
    # đồng chủ trì đồng ý lại bằng lời rõ ràng (không phải "Ờ.") → final
    evs.append(ev("u005", K.AGREE, "Hai", "B", quote="anh đồng ý đi B"))
    (d,) = decisions(ledger_for(tr, evs))
    assert d.status == Status.FINAL


def test_fallback_decision_is_final_and_old_option_stays_open():
    tr = _tr(
        "[00:10] An: Em đề xuất giữ A.",
        "[00:20] Bình: Em đề xuất B.",
        "[00:30] Sếp: Chốt dùng B. Nếu thứ Năm B giao trễ thì quay lại A.",
    )
    led = ledger_for(
        tr,
        [
            ev("u001", K.PROPOSE, "An", "A", content="Giữ A"),
            ev("u002", K.PROPOSE, "Bình", "B"),
            # LLM tự đặt hedged=true vì có "Nếu" — luật vẫn coi là chốt
            ev(
                "u003",
                K.AGREE,
                "Sếp",
                "B",
                hedged=True,
                quote="Chốt dùng B. Nếu thứ Năm B giao trễ thì quay lại A",
            ),
        ],
    )
    (d,) = decisions(led)
    assert d.status == Status.FINAL
    (opt,) = [i for i in led.items if i.type == ItemType.OPTION]
    assert opt.status == Status.OPEN and d.supersedes == []


def test_chair_backchannel_after_proposal_is_indirect_agreement():
    tr = _tr("[00:10] An: Em đề xuất chuyển sang A.", "[00:20] Sếp: Ừ.")
    (d,) = decisions(ledger_for(tr, [ev("u001", K.PROPOSE, "An", "A", content="Chuyển sang A")]))
    assert d.status == Status.NEEDS_CONFIRMATION and d.decided_by == "Sếp"
    assert d.content == "Chuyển sang A" and [e.utt for e in d.evidence] == ["u002", "u001"]


def test_non_chair_backchannel_after_proposal_stays_open_question():
    tr = _tr("[00:10] An: Em đề xuất chuyển sang A.", "[00:20] Bình: Dạ.")
    led = ledger_for(tr, [ev("u001", K.PROPOSE, "An", "A")])
    assert decisions(led) == [] and led.items[0].type == ItemType.OPEN_QUESTION


def test_absent_owner_kept_and_needs_confirmation():
    tr = _tr("[00:10] Sếp: Chi làm báo cáo, thứ Sáu nộp.", absent="Chi (Kế toán)")
    led = ledger_for(
        tr, [ev("u001", K.ASSIGN, "Sếp", "bao-cao", owner="Chi", quote="Chi làm báo cáo")]
    )
    (t,) = [i for i in led.items if i.type == ItemType.TASK]
    assert t.owner == "Chi" and t.status == Status.NEEDS_CONFIRMATION
    assert any("vắng mặt" in f for f in t.flags)


def test_agree_label_on_bare_backchannel_is_only_indirect():
    # LLM đôi khi gán agree cho "Ừ." dù prompt cấm — luật không được tin thành FINAL
    tr = _tr("[00:10] An: Em đề xuất chuyển sang A.", "[00:20] Sếp: Ừ.")
    led = ledger_for(
        tr, [ev("u001", K.PROPOSE, "An", "A"), ev("u002", K.AGREE, "Sếp", "A", quote="Ừ")]
    )
    (d,) = decisions(led)
    assert d.status == Status.NEEDS_CONFIRMATION
    assert any("gián tiếp" in f for f in d.flags)
