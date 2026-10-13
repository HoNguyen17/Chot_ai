"""Luật suy trạng thái cuối — trái tim của sản phẩm.

LLM chỉ gán nhãn sự kiện cho từng câu. Trạng thái cuối (Đã chốt / Cần xác nhận / Bị thay thế /
Hoãn / Mở) được suy ra bằng code ở đây: dễ đoán, unit test được, không đổi khi đổi model.

Luật "Đã chốt" (PRD Q3) — một phương án chỉ FINAL khi đủ cả 3:
  1. Có sự kiện AGREE từ người chủ trì (người có thẩm quyền) và câu đó KHÔNG rào đón.
  2. Sau AGREE đó không có PROPOSE / REVISE / REOPEN / DEFER, hay OBJECT nhắm vào nó.
  3. Bằng chứng trỏ đúng câu AGREE sau cùng (grounding tầng 2 kiểm tra lại).
Thiếu bất kỳ điều nào → NEEDS_CONFIRMATION (nếu có đồng thuận) / DEFERRED / OPEN_QUESTION.
"""

from __future__ import annotations

from collections import defaultdict

from chot.domain.dates import extract_deadline_phrase, resolve_deadline
from chot.domain.enums import (
    DECISION_EVENTS,
    ID_PREFIX,
    STANDALONE_EVENTS,
    TASK_EVENTS,
    EventKind,
    ItemType,
    Status,
)
from chot.domain.models import Event, Evidence, ExtractionResult, Item, Ledger, Transcript
from chot.domain.text import is_backchannel, is_hedged

_CONTRADICTING = {EventKind.PROPOSE, EventKind.REVISE, EventKind.REOPEN, EventKind.DEFER}


class _Ids:
    def __init__(self) -> None:
        self._n: dict[ItemType, int] = defaultdict(int)

    def next(self, t: ItemType) -> str:
        self._n[t] += 1
        return f"{ID_PREFIX[t]}{self._n[t]}"


def _evidence(e: Event, tr: Transcript) -> Evidence:
    u = tr.utt(e.utt)
    quote = e.quote or (u.text if u else "")
    return Evidence(
        utt=e.utt,
        quote=quote,
        ts=u.ts_label if u else None,
        speaker=u.speaker if u else e.speaker,
    )


def _hedged(e: Event) -> bool:
    return e.hedged or is_hedged(e.quote)


def _option_content(events: list[Event], key: str | None) -> str:
    """Nội dung phương án = câu đề xuất GỐC (lần đầu được nêu), không phải câu nhắc lại."""
    for e in events:
        if e.key == key and e.kind in (EventKind.PROPOSE, EventKind.REVISE) and e.content:
            return e.content
    for e in events:
        if e.key == key and e.content:
            return e.content
    return key or ""


def resolve_thread(events: list[Event], tr: Transcript, thread_title: str, ids: _Ids) -> list[Item]:
    """Suy các mục Ledger từ chuỗi sự kiện quyết định của MỘT chủ đề."""
    evs = sorted(events, key=lambda e: tr.order(e.utt))
    agrees = [e for e in evs if e.kind == EventKind.AGREE]
    last_agree = agrees[-1] if agrees else None

    contradicted = False
    if last_agree:
        later = [e for e in evs if tr.order(e.utt) > tr.order(last_agree.utt)]
        contradicted = any(e.kind in _CONTRADICTING for e in later) or any(
            e.kind == EventKind.OBJECT and e.key in (None, last_agree.key) for e in later
        )

    thread_id = evs[0].thread if evs else None

    # Trường hợp 1: có đồng thuận cuối cùng, không bị lật → FINAL hoặc NEEDS_CONFIRMATION
    if last_agree and not contradicted:
        authority = last_agree.speaker in tr.chairs
        hedged = _hedged(last_agree)
        status = Status.FINAL if authority and not hedged else Status.NEEDS_CONFIRMATION
        flags = []
        if not authority:
            flags.append("người đồng ý không phải người chủ trì")
        if hedged:
            flags.append("đồng thuận có rào đón")
        if status == Status.FINAL and len(agrees) > 1:
            flags.append("đã đổi ý trong cuộc họp — xem timeline")

        chosen_key = last_agree.key
        option_items: list[Item] = []
        seen: set[str | None] = {chosen_key}
        for e in evs:
            if e.kind in (EventKind.PROPOSE, EventKind.REVISE) and e.key not in seen:
                seen.add(e.key)
                option_items.append(
                    Item(
                        id=ids.next(ItemType.OPTION),
                        type=ItemType.OPTION,
                        thread=thread_id,
                        content=_option_content(evs, e.key),
                        status=Status.SUPERSEDED if status == Status.FINAL else Status.OPEN,
                        evidence=[
                            _evidence(x, tr)
                            for x in evs
                            if x.key == e.key and x.kind in (EventKind.PROPOSE, EventKind.REVISE)
                        ],
                    )
                )
        chosen_proposals = [
            x
            for x in evs
            if x.key == chosen_key and x.kind in (EventKind.PROPOSE, EventKind.REVISE)
        ]
        decision = Item(
            id=ids.next(ItemType.DECISION),
            type=ItemType.DECISION,
            thread=thread_id,
            # Đã chốt → dùng lời chốt của chủ trì; chưa chốt → dùng nội dung phương án gốc.
            content=(last_agree.content or _option_content(evs, chosen_key))
            if status == Status.FINAL
            else (_option_content(evs, chosen_key) or last_agree.content),
            status=status,
            decided_by=last_agree.speaker,
            supersedes=[o.id for o in option_items] if status == Status.FINAL else [],
            # Bằng chứng: câu AGREE sau cùng đứng đầu, sau đó là câu đề xuất gốc.
            evidence=[_evidence(last_agree, tr)] + [_evidence(x, tr) for x in chosen_proposals[:1]],
            flags=flags,
        )
        return [decision, *option_items]

    # Trường hợp 2: có hoãn → DEFERRED (một mục cấp chủ đề)
    defers = [e for e in evs if e.kind == EventKind.DEFER]
    if defers:
        return [
            Item(
                id=ids.next(ItemType.DECISION),
                type=ItemType.DECISION,
                thread=thread_id,
                content=thread_title,
                status=Status.DEFERRED,
                evidence=[_evidence(e, tr) for e in defers],
                flags=["đã có đồng thuận nhưng bị lật lại"] if last_agree else [],
            )
        ]

    # Trường hợp 3: chưa ai đồng ý → câu hỏi mở
    firsts = [e for e in evs if e.kind in (EventKind.PROPOSE, EventKind.REVISE, EventKind.OBJECT)]
    return [
        Item(
            id=ids.next(ItemType.OPEN_QUESTION),
            type=ItemType.OPEN_QUESTION,
            thread=thread_id,
            content=thread_title,
            status=Status.OPEN,
            evidence=[_evidence(e, tr) for e in (firsts or evs)[:2]],
            flags=["chưa có đồng thuận"],
        )
    ]


def resolve_task(events: list[Event], tr: Transcript, ids: _Ids) -> Item:
    """Một task chỉ OPEN (đã nhận) khi owner tự nhận hoặc trả lời cam kết không rào đón."""
    evs = sorted(events, key=lambda e: tr.order(e.utt))
    assign = next((e for e in evs if e.kind == EventKind.ASSIGN), evs[0])
    owner = assign.owner or (assign.speaker if assign.kind == EventKind.COMMIT else None)
    flags: list[str] = []

    if owner and owner not in tr.names:
        flags.append(f"owner '{owner}' không có trong danh sách người tham gia")
        owner = None

    self_assigned = owner is not None and assign.speaker == owner
    replies = [
        e
        for e in evs
        if e.speaker == owner
        and e.kind in (EventKind.COMMIT, EventKind.DECLINE)
        and tr.order(e.utt) >= tr.order(assign.utt)
    ]
    committed = any(
        e.kind == EventKind.COMMIT and not _hedged(e) and not is_backchannel(e.quote)
        for e in replies
    )
    declined = any(e.kind == EventKind.DECLINE for e in replies)

    if owner is None:
        status = Status.NEEDS_CONFIRMATION
        flags.append("chưa rõ ai nhận việc")
    elif declined:
        status = Status.NEEDS_CONFIRMATION
        flags.append("owner từ chối hoặc trì hoãn")
    elif (self_assigned and not _hedged(assign)) or committed:
        status = Status.OPEN
    else:
        status = Status.NEEDS_CONFIRMATION
        flags.append("owner chưa xác nhận nhận việc")

    deadline_text = next((e.deadline_text for e in reversed(evs) if e.deadline_text), None) or next(
        (p for e in reversed(evs) if (p := extract_deadline_phrase(e.quote))), None
    )
    deadline = resolve_deadline(deadline_text, tr.date)
    if deadline_text and not deadline:
        flags.append("hạn chót chưa cụ thể")

    return Item(
        id=ids.next(ItemType.TASK),
        type=ItemType.TASK,
        thread=assign.thread,
        content=assign.content or assign.quote,
        status=status,
        owner=owner,
        deadline=deadline,
        deadline_text=deadline_text,
        evidence=[_evidence(e, tr) for e in evs],
        flags=flags,
    )


def build_ledger(
    tr: Transcript, extraction: ExtractionResult, generated_by: str = "rules-v1"
) -> Ledger:
    ids = _Ids()
    titles = {t.id: t.title for t in extraction.threads}
    events = [e for e in extraction.events if tr.utt(e.utt) is not None]

    by_thread: dict[str, list[Event]] = defaultdict(list)
    tasks: dict[tuple[str, str], list[Event]] = defaultdict(list)
    standalone: list[Event] = []
    for e in events:
        if e.kind in DECISION_EVENTS:
            by_thread[e.thread].append(e)
        elif e.kind in TASK_EVENTS:
            tasks[(e.thread, e.key or e.utt)].append(e)
        elif e.kind in STANDALONE_EVENTS:
            standalone.append(e)

    items: list[Item] = []
    decision_threads = set(by_thread)
    for thread_id, evs in by_thread.items():
        items += resolve_thread(evs, tr, titles.get(thread_id, thread_id), ids)
    for evs in tasks.values():
        items.append(resolve_task(evs, tr, ids))
    for e in standalone:
        # Câu hỏi nằm trong một chủ đề quyết định đã được xử lý ở resolve_thread.
        if e.kind == EventKind.QUESTION and e.thread in decision_threads:
            continue
        items.append(
            Item(
                id=ids.next(STANDALONE_EVENTS[e.kind]),
                type=STANDALONE_EVENTS[e.kind],
                thread=e.thread,
                content=e.content or e.quote,
                status=Status.OPEN,
                evidence=[_evidence(e, tr)],
            )
        )

    items.sort(key=lambda i: min((tr.order(ev.utt) for ev in i.evidence), default=10**9))
    return Ledger(
        meeting_id=tr.meeting_id,
        generated_by=generated_by,
        threads=extraction.threads,
        items=items,
    )
