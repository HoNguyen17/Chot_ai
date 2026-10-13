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
