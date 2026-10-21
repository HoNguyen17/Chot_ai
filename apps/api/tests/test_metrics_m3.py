"""Chỉ số Mission 3: việc nhầm, nhất quán thread, câu hỏi mỗi buổi, phạm vi tri thức."""

from __future__ import annotations

from chot.eval.metrics import GoldMeeting, score_meeting, summarize


def _m(*items: dict) -> GoldMeeting:
    return GoldMeeting(meeting_id="t", items=[{"content": "", **i} for i in items])


def _score(pred: GoldMeeting, gold: GoldMeeting) -> dict:
    return summarize(score_meeting(pred, gold, None))


def test_false_action_counts_open_tasks_gold_did_not_accept():
    pred = _m(
        {"id": "T1", "type": "task", "status": "open", "evidence": ["u001"]},  # gold: open → đúng
        {"id": "T2", "type": "task", "status": "open", "evidence": ["u005"]},  # gold: nc → nhầm
        {
            "id": "T3",
            "type": "task",
            "status": "open",
            "evidence": ["u009"],
        },  # gold không có → nhầm
        {"id": "T4", "type": "task", "status": "needs_confirmation", "evidence": ["u012"]},
    )
    gold = _m(
        {"id": "T1", "type": "task", "status": "open", "evidence": ["u001"]},
        {"id": "T2", "type": "task", "status": "needs_confirmation", "evidence": ["u005"]},
        {"id": "T4", "type": "task", "status": "open", "evidence": ["u012"]},
    )
    assert _score(pred, gold)["false_action_rate"] == round(2 / 3, 3)


def test_false_action_is_none_without_open_tasks():
    pred = _m({"id": "D1", "type": "decision", "status": "final", "evidence": ["u001"]})
    assert _score(pred, pred)["false_action_rate"] is None


def test_thread_consistency_over_gold_pairs_sharing_a_thread():
    gold = _m(
        {"id": "D1", "type": "decision", "status": "final", "thread": "pay", "evidence": ["u010"]},
        {
            "id": "O1",
            "type": "option",
            "status": "superseded",
            "thread": "pay",
            "evidence": ["u002"],
        },
        {"id": "T1", "type": "task", "status": "open", "thread": "pay", "evidence": ["u011"]},
        {"id": "B1", "type": "blocker", "status": "open", "thread": "ui", "evidence": ["u020"]},
    )
    pred = _m(  # D1–O1 cùng thread; T1 bị tách sang thread khác → 1/3 cặp đúng
        {"id": "D1", "type": "decision", "status": "final", "thread": "a", "evidence": ["u010"]},
        {"id": "O1", "type": "option", "status": "superseded", "thread": "a", "evidence": ["u002"]},
        {"id": "T1", "type": "task", "status": "open", "thread": "b", "evidence": ["u011"]},
        {"id": "B1", "type": "blocker", "status": "open", "thread": "c", "evidence": ["u020"]},
    )
    assert _score(pred, gold)["thread_consistency"] == round(1 / 3, 3)


def test_thread_consistency_is_none_without_matched_pairs():
    gold = _m(
        {"id": "D1", "type": "decision", "status": "final", "thread": "x", "evidence": ["u1"]}
    )
    assert _score(gold, gold)["thread_consistency"] is None


def test_ledger_as_gold_keeps_thread():
    from chot.domain.models import Evidence, Item, Ledger
    from chot.eval.metrics import ledger_as_gold

    item = Item(
        id="D1",
        type="decision",
        thread="pay",
        content="x",
        status="final",
        evidence=[Evidence(utt="u001", quote="x")],
    )
    assert ledger_as_gold(Ledger(meeting_id="t", items=[item])).items[0].thread == "pay"


def test_questions_per_meeting_and_share_gold_agrees_need_asking():
    from chot.eval.metrics import Counts

    pred = _m(
        {"id": "D1", "type": "decision", "status": "needs_confirmation", "evidence": ["u001"]},
        {"id": "T1", "type": "task", "status": "needs_confirmation", "evidence": ["u005"]},
        {"id": "T2", "type": "task", "status": "open", "evidence": ["u009"]},
    )
    gold = _m(
        {"id": "D1", "type": "decision", "status": "needs_confirmation", "evidence": ["u001"]},
        {"id": "T1", "type": "task", "status": "open", "evidence": ["u005"]},
    )
    total = Counts()
    total.add(score_meeting(pred, gold, None))
    total.add(score_meeting(_m(), _m(), None))  # buổi thứ 2 không có câu hỏi nào
    s = summarize(total)
    assert s["questions_per_meeting"] == 1.0  # 2 câu hỏi / 2 buổi
    assert s["question_precision"] == 0.5  # chỉ D1 gold cũng cần xác nhận


def test_question_precision_is_none_without_questions():
    pred = _m({"id": "T1", "type": "task", "status": "open", "evidence": ["u001"]})
    s = _score(pred, pred)
    assert s["questions_per_meeting"] == 0.0 and s["question_precision"] is None


def test_knowledge_scope_only_counts_gold_items_with_scope():
    gold = _m(
        {"id": "K1", "type": "knowledge", "status": "open", "scope": "durable", "evidence": ["u1"]},
        {"id": "K2", "type": "knowledge", "status": "open", "scope": "meeting", "evidence": ["u2"]},
        {"id": "K3", "type": "knowledge", "status": "open", "evidence": ["u3"]},
    )
    pred = _m(  # M2 không có scope → coi như "meeting" (chưa có Kho tri thức)
        {"id": "K1", "type": "knowledge", "status": "open", "evidence": ["u1"]},
        {"id": "K2", "type": "knowledge", "status": "open", "evidence": ["u2"]},
        {"id": "K3", "type": "knowledge", "status": "open", "scope": "durable", "evidence": ["u3"]},
    )
    assert _score(pred, gold)["knowledge_scope_acc"] == 0.5


def test_knowledge_scope_is_none_when_gold_has_no_scope():
    gold = _m({"id": "K1", "type": "knowledge", "status": "open", "evidence": ["u1"]})
    assert _score(gold, gold)["knowledge_scope_acc"] is None
