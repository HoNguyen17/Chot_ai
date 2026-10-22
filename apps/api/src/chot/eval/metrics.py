"""Ghép cặp mục dự đoán ↔ mục gold và tính các chỉ số trong PRD mục 5.

Ghép cặp: cùng NHÓM loại + có ít nhất 1 mã câu bằng chứng trùng nhau (chọn cặp trùng nhiều nhất).
Nhóm: {decision, option, open_question} | {task} | {blocker} | {knowledge} | {request, feedback}.
Không ghép theo nội dung chữ vì cách diễn đạt luôn khác nhau; bằng chứng là thứ ổn định.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, model_validator

from chot.domain.enums import ItemType, Status
from chot.domain.grounding import quote_in_utterance
from chot.domain.models import Ledger, Transcript

GROUP = {
    ItemType.DECISION: "decision",
    ItemType.OPTION: "decision",
    ItemType.OPEN_QUESTION: "decision",
    ItemType.TASK: "task",
    ItemType.BLOCKER: "blocker",
    ItemType.KNOWLEDGE: "knowledge",
    ItemType.REQUEST: "input",
    ItemType.FEEDBACK: "input",
}


class GoldItem(BaseModel):
    id: str
    type: ItemType
    status: Status
    content: str = ""
    thread: str | None = None
    owner: str | None = None
    decided_by: str | None = None
    deadline: dt.date | None = None
    deadline_text: str | None = None
    evidence: list[str] = Field(default_factory=list)
    note: str | None = None
    scope: str | None = None  # knowledge: "meeting" | "durable" (M3); thiếu = không chấm

    @model_validator(mode="after")
    def _legacy_noted(self) -> GoldItem:
        """Gold M2 ghi tri thức / phản hồi là `open`; M3 gọi là `noted` — cùng nghĩa."""
        if self.type in (ItemType.KNOWLEDGE, ItemType.FEEDBACK) and self.status == Status.OPEN:
            self.status = Status.NOTED
        return self


class GoldMeeting(BaseModel):
    meeting_id: str
    labeler: str | None = None
    items: list[GoldItem]


def ledger_as_gold(ledger: Ledger) -> GoldMeeting:
    """Cho phép so 2 Ledger bất kỳ (vd nhãn của bạn vs đáp án) bằng cùng một hàm."""
    return GoldMeeting(
        meeting_id=ledger.meeting_id,
        items=[
            GoldItem(
                id=i.id,
                type=i.type,
                status=i.status,
                content=i.content,
                thread=i.thread,
                owner=i.owner,
                decided_by=i.decided_by,
                deadline=i.deadline,
                deadline_text=i.deadline_text,
                evidence=[e.utt for e in i.evidence],
            )
            for i in ledger.items
        ],
    )


@dataclass
class Counts:
    pred_final: int = 0
    pred_final_wrong: int = 0
    gold_final: int = 0
    gold_final_hit: int = 0
    gold_superseded: int = 0
    gold_superseded_hit: int = 0
    pred_items: int = 0
    gold_items: int = 0
    matched: int = 0
    status_correct: int = 0
    tasks_matched: int = 0
    owner_correct: int = 0
    deadline_correct: int = 0
    quotes_total: int = 0
    quotes_valid: int = 0
    hallucinated_people: int = 0
    pred_task_open: int = 0
    pred_task_open_wrong: int = 0
    thread_pairs: int = 0
    thread_pairs_same: int = 0
    meetings: int = 0
    questions: int = 0
    questions_gold_agree: int = 0
    scope_total: int = 0
    scope_correct: int = 0
    by_group: dict[str, list[int]] = field(default_factory=dict)  # group -> [pred, gold, matched]
    errors: list[str] = field(default_factory=list)

    def add(self, other: Counts) -> None:
        for k, v in vars(other).items():
            if isinstance(v, int):
                setattr(self, k, getattr(self, k) + v)
        for g, (p, gd, m) in other.by_group.items():
            cur = self.by_group.setdefault(g, [0, 0, 0])
            cur[0] += p
            cur[1] += gd
            cur[2] += m
        self.errors += other.errors


def _ratio(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def score_meeting(
    pred: GoldMeeting, gold: GoldMeeting, tr: Transcript | None, pred_ledger: Ledger | None = None
) -> Counts:
    c = Counts(pred_items=len(pred.items), gold_items=len(gold.items), meetings=1)

    # 1) Ghép cặp tham lam theo số câu bằng chứng trùng nhau; hoà → ưu tiên cùng type
    pairs: dict[str, str] = {}  # gold_id -> pred_id
    used: set[str] = set()
    for g in gold.items:
        best, best_score = None, (0, False)
        for p in pred.items:
            if p.id in used or GROUP[p.type] != GROUP[g.type]:
                continue
            score = (len(set(p.evidence) & set(g.evidence)), p.type == g.type)
            if score[0] and score > best_score:
                best, best_score = p, score
        if best:
            pairs[g.id] = best.id
            used.add(best.id)
    pmap = {p.id: p for p in pred.items}
    gmap = {g.id: g for g in gold.items}
    gold_by_pred = {pid: gmap[gid] for gid, pid in pairs.items()}
    c.matched = len(pairs)

    for grp in set(GROUP.values()):
        p_n = sum(GROUP[p.type] == grp for p in pred.items)
        g_n = sum(GROUP[g.type] == grp for g in gold.items)
        m_n = sum(GROUP[gmap[gid].type] == grp for gid in pairs)
        if p_n or g_n:
            c.by_group[grp] = [p_n, g_n, m_n]

    # 2) North-star: tỷ lệ chốt nhầm
    for p in pred.items:
        if p.type == ItemType.DECISION and p.status == Status.FINAL:
            c.pred_final += 1
            g = gold_by_pred.get(p.id)
            if not g or g.status != Status.FINAL:
                c.pred_final_wrong += 1
                c.errors.append(
                    f"[{pred.meeting_id}] CHỐT NHẦM {p.id} ({', '.join(p.evidence)}): {p.content[:70]}"
                    + (f" — gold: {g.status}" if g else " — gold: không có")
                )

    # 2b) Việc nhầm (M3): task "Đã nhận" mà gold không coi là việc đã nhận
    # 2c) Câu hỏi cho người dùng (M2: mục needs_confirmation) và bao nhiêu câu gold cũng cần hỏi
    for p in pred.items:
        g = gold_by_pred.get(p.id)
        if p.status == Status.NEEDS_CONFIRMATION:
            c.questions += 1
            c.questions_gold_agree += bool(g and g.status == Status.NEEDS_CONFIRMATION)
        if p.type == ItemType.TASK and p.status == Status.OPEN:
            c.pred_task_open += 1
            if not g or g.status != Status.OPEN:
                c.pred_task_open_wrong += 1
                c.errors.append(
                    f"[{pred.meeting_id}] VIỆC NHẦM {p.id} ({', '.join(p.evidence)}): {p.content[:70]}"
                    + (f" — gold: {g.status}" if g else " — gold: không có")
                )

    # 3) Trạng thái cuối, supersession, owner, deadline
    for g in gold.items:
        p = pmap.get(pairs.get(g.id, ""))
        if g.type == ItemType.DECISION and g.status == Status.FINAL:
            c.gold_final += 1
            if p and p.type == ItemType.DECISION and p.status == Status.FINAL:
                c.gold_final_hit += 1
            else:
                c.errors.append(f"[{gold.meeting_id}] BỎ SÓT QUYẾT ĐỊNH {g.id}: {g.content[:70]}")
        if g.status == Status.SUPERSEDED:
            c.gold_superseded += 1
            if p and p.status == Status.SUPERSEDED:
                c.gold_superseded_hit += 1
        if p is None:
            continue
        if g.type == ItemType.KNOWLEDGE and g.scope:
            c.scope_total += 1
            c.scope_correct += (p.scope or "meeting") == g.scope  # M2 chưa có Kho → "meeting"
        if p.status == g.status:
            c.status_correct += 1
        if g.type == ItemType.TASK:
            c.tasks_matched += 1
            if (p.owner or None) == (g.owner or None):
                c.owner_correct += 1
            else:
                c.errors.append(
                    f"[{gold.meeting_id}] SAI OWNER {g.id}: dự đoán {p.owner} / gold {g.owner}"
                )
            if p.deadline == g.deadline:
                c.deadline_correct += 1
            else:
                c.errors.append(
                    f"[{gold.meeting_id}] SAI HẠN {g.id}: dự đoán {p.deadline} / gold {g.deadline}"
                )

    # 3b) Nhất quán thread (M3): cặp mục gold cùng thread → hệ thống có giữ cùng thread không
    matched = [(g, pmap[pairs[g.id]]) for g in gold.items if g.id in pairs and g.thread]
    for i, (g1, p1) in enumerate(matched):
        for g2, p2 in matched[i + 1 :]:
            if g1.thread == g2.thread:
                c.thread_pairs += 1
                c.thread_pairs_same += bool(p1.thread) and p1.thread == p2.thread

    # 4) Grounding tầng 1 + người bịa
    if tr and pred_ledger:
        for item in pred_ledger.items:
            for ev in item.evidence:
                c.quotes_total += 1
                u = tr.utt(ev.utt)
                c.quotes_valid += bool(u and quote_in_utterance(ev.quote, u.text))
            for person in (item.owner, item.decided_by):
                if person and person not in tr.known_names:
                    c.hallucinated_people += 1
    return c


def summarize(c: Counts) -> dict:
    groups = {
        g: {"precision": _ratio(m, p), "recall": _ratio(m, gd), "pred": p, "gold": gd}
        for g, (p, gd, m) in sorted(c.by_group.items())
    }
    return {
        "wrong_final_rate": _ratio(c.pred_final_wrong, c.pred_final),
        "false_action_rate": _ratio(c.pred_task_open_wrong, c.pred_task_open),
        "thread_consistency": _ratio(c.thread_pairs_same, c.thread_pairs),
        "questions_per_meeting": _ratio(c.questions, c.meetings),
        "question_precision": _ratio(c.questions_gold_agree, c.questions),
        "knowledge_scope_acc": _ratio(c.scope_correct, c.scope_total),
        "final_state_accuracy": _ratio(c.gold_final_hit, c.gold_final),
        "supersession_recall": _ratio(c.gold_superseded_hit, c.gold_superseded),
        "item_precision": _ratio(c.matched, c.pred_items),
        "item_recall": _ratio(c.matched, c.gold_items),
        "status_accuracy_matched": _ratio(c.status_correct, c.matched),
        "owner_accuracy": _ratio(c.owner_correct, c.tasks_matched),
        "deadline_accuracy": _ratio(c.deadline_correct, c.tasks_matched),
        "grounding_tier1": _ratio(c.quotes_valid, c.quotes_total),
        "hallucinated_people": c.hallucinated_people,
        "counts": {
            "pred_final": c.pred_final,
            "pred_final_wrong": c.pred_final_wrong,
            "gold_final": c.gold_final,
            "pred_items": c.pred_items,
            "gold_items": c.gold_items,
            "matched": c.matched,
        },
        "by_group": groups,
    }


TARGETS = {
    "wrong_final_rate": ("≤", 0.05),
    "final_state_accuracy": ("≥", 0.90),
    "supersession_recall": ("≥", 0.80),
    "owner_accuracy": ("≥", 0.90),
    "deadline_accuracy": ("≥", 0.85),
    "grounding_tier1": ("≥", 1.0),
}


def render_table(summary: dict, title: str) -> str:
    rows = [f"### {title}", "", "| Chỉ số | Giá trị | Mục tiêu | Đạt? |", "|---|---|---|---|"]
    for key, (op, target) in TARGETS.items():
        v = summary.get(key)
        ok = "—" if v is None else ("✅" if (v <= target if op == "≤" else v >= target) else "❌")
        rows.append(f"| {key} | {'-' if v is None else v} | {op} {target} | {ok} |")
    rows.append(
        f"| item_precision / recall | {summary['item_precision']} / {summary['item_recall']} | — | — |"
    )
    for key in (
        "false_action_rate",
        "thread_consistency",
        "questions_per_meeting",
        "question_precision",
        "knowledge_scope_acc",
    ):  # M3, chưa có mục tiêu
        v = summary.get(key)
        rows.append(f"| {key} | {'-' if v is None else v} | — | — |")
    rows.append(
        f"| hallucinated_people | {summary['hallucinated_people']} | 0 | "
        f"{'✅' if summary['hallucinated_people'] == 0 else '❌'} |"
    )
    return "\n".join(rows)
