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
from chot.domain.models import (
    Event,
    Evidence,
    ExtractionResult,
    Item,
    Ledger,
    TimelineEntry,
    Transcript,
    Utterance,
)
from chot.domain.reasons import Reason, flag
from chot.domain.reasons import ReasonCode as C
from chot.domain.status_table import check_status
from chot.domain.text import has_fallback, is_backchannel, is_durable, is_hearsay, is_hedged

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


def _timeline(evs: list[Event], tr: Transcript) -> list[TimelineEntry]:
    """Diễn biến của chủ đề theo thứ tự câu — dòng "Vì sao" (SPEC M3 §4.5)."""
    out = []
    for e in evs:
        u = tr.utt(e.utt)
        out.append(
            TimelineEntry(
                utt=e.utt,
                ts=u.ts_label if u else None,
                speaker=e.speaker,
                kind=e.kind,
                key=e.key,
                quote=e.quote or (u.text if u else ""),
            )
        )
    return out


def _with_reasons(reasons: list[Reason]) -> dict:
    """Mã lý do + chữ M2 sinh từ mã (export cũ không đổi)."""
    return {"reasons": reasons, "flags": [flag(r) for r in reasons]}


def _hedged(e: Event) -> bool:
    # Câu chốt kèm điều kiện dự phòng ("nếu … thì quay về A"): chỉ tin dấu hiệu trong văn bản,
    # vì LLM hay gắn hedged=true chỉ vì thấy chữ "nếu" (quy ước Nash 11).
    if has_fallback(e.quote):
        return is_hedged(e.quote)
    return e.hedged or is_hedged(e.quote)


def _effective_agree(agrees: list[Event], tr: Transcript) -> Event | None:
    """Agree sau cùng; nếu đó chỉ là người không chủ trì 'ok' theo CÙNG phương án mà chủ trì
    đã đồng ý trước đó, thì lấy agree của chủ trì (người khác hưởng ứng không làm yếu quyết định)."""
    if not agrees:
        return None
    last = agrees[-1]
    if last.speaker in tr.chairs:
        return last
    by_chair = [a for a in agrees if a.speaker in tr.chairs and a.key == last.key]
    return by_chair[-1] if by_chair else last


def _unresolved_co_chair(evs: list[Event], agree: Event, tr: Transcript) -> str | None:
    """Đồng chủ trì đã phản đối phương án được chọn mà chưa đồng ý lại (quy ước Nash 10)."""
    for chair in tr.chairs - {agree.speaker}:
        mine = [
            e
            for e in evs
            if e.speaker == chair
            and e.key in (None, agree.key)
            and e.kind in (EventKind.OBJECT, EventKind.AGREE)
        ]
        if mine and mine[-1].kind == EventKind.OBJECT:
            return chair
    return None


def _indirect_agree(evs: list[Event], tr: Transcript) -> tuple[Event, Utterance] | None:
    """Chủ trì chỉ 'Ừ.' ngay sau một đề xuất = đồng ý gián tiếp (quy ước Nash 5)."""
    for e in reversed([x for x in evs if x.kind in (EventKind.PROPOSE, EventKind.REVISE)]):
        u = tr.utt(e.utt)
        nxt = tr.utterances[u.index] if u and u.index < len(tr.utterances) else None  # index từ 1
        if nxt and nxt.speaker in tr.chairs and is_backchannel(nxt.text):
            return e, nxt
    return None


def _options(
    evs: list[Event],
    chosen_key: str | None,
    status: Status,
    tr: Transcript,
    ids: _Ids,
    timeline: list[TimelineEntry],
) -> list[Item]:
    """Mỗi phương án khác phương án được chọn → một mục option (giữ làm lịch sử)."""
    items: list[Item] = []
    seen: set[str | None] = {chosen_key}
    for e in evs:
        if e.kind in (EventKind.PROPOSE, EventKind.REVISE) and e.key not in seen:
            seen.add(e.key)
            items.append(
                Item(
                    id=ids.next(ItemType.OPTION),
                    type=ItemType.OPTION,
                    thread=e.thread,
                    content=_option_content(evs, e.key),
                    status=status,
                    evidence=[
                        _evidence(x, tr)
                        for x in evs
                        if x.key == e.key and x.kind in (EventKind.PROPOSE, EventKind.REVISE)
                    ],
                    timeline=timeline,
                )
            )
    return items


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
    last_agree = _effective_agree(agrees, tr)

    contradicted = False
    if last_agree:
        later = [e for e in evs if tr.order(e.utt) > tr.order(last_agree.utt)]
        contradicted = any(e.kind in _CONTRADICTING for e in later) or any(
            e.kind == EventKind.OBJECT and e.key in (None, last_agree.key) for e in later
        )

    thread_id = evs[0].thread if evs else None
    timeline = _timeline(evs, tr)

    # Trường hợp 1: có đồng thuận cuối cùng, không bị lật → FINAL hoặc NEEDS_CONFIRMATION
    if last_agree and not contradicted:
        authority = last_agree.speaker in tr.chairs
        hedged = _hedged(last_agree)
        co_chair = _unresolved_co_chair(evs, last_agree, tr) if authority else None
        # Câu "đồng ý" chỉ là "Ừ."/"Dạ." → đồng ý gián tiếp, không bao giờ FINAL (quy ước Nash 5)
        u = tr.utt(last_agree.utt)
        nod_only = is_backchannel(u.text if u else last_agree.quote)
        fallback = has_fallback(last_agree.quote)
        status = (
            Status.FINAL
            if authority and not hedged and not co_chair and not nod_only
            else Status.NEEDS_CONFIRMATION
        )
        chosen_key = last_agree.key
        chair = ", ".join(sorted(tr.chairs)) or "Chủ trì"
        reasons: list[Reason] = []
        if not authority:
            reasons.append(Reason(code=C.NOT_CHAIR, params={"chair": chair, "key": chosen_key}))
        if hedged:
            params = {"speaker": last_agree.speaker, "quote": last_agree.quote, "key": chosen_key}
            reasons.append(Reason(code=C.HEDGED, params=params))
        if nod_only:
            params = {"chair": last_agree.speaker, "key": chosen_key}
            reasons.append(Reason(code=C.NOD_ONLY, params=params))
        if co_chair:
            params = {"chair": last_agree.speaker, "co_chair": co_chair, "key": chosen_key}
            reasons.append(Reason(code=C.CO_CHAIR_OBJECTION, params=params))
        if fallback:
            reasons.append(Reason(code=C.FALLBACK_KEPT))
        # Có điều kiện quay lại → phương án cũ chưa bị loại hẳn (quy ước Nash 11)
        replaces = status == Status.FINAL and not fallback
        if status == Status.FINAL and len(agrees) > 1:
            reasons.append(Reason(code=C.CHANGED_MIND))

        option_items = _options(
            evs, chosen_key, Status.SUPERSEDED if replaces else Status.OPEN, tr, ids, timeline
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
            supersedes=[o.id for o in option_items] if replaces else [],
            # Bằng chứng: câu AGREE sau cùng đứng đầu, sau đó là câu đề xuất gốc.
            evidence=[_evidence(last_agree, tr)] + [_evidence(x, tr) for x in chosen_proposals[:1]],
            timeline=timeline,
            **_with_reasons(reasons),
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
                timeline=timeline,
                **_with_reasons([Reason(code=C.AGREEMENT_REVERSED)] if last_agree else []),
            )
        ]

    # Trường hợp 3: chủ trì chỉ "Ừ." ngay sau một đề xuất → đồng ý gián tiếp, CẦN XÁC NHẬN
    indirect = _indirect_agree(evs, tr)
    if indirect:
        proposal, nod = indirect
        others = _options(evs, proposal.key, Status.OPEN, tr, ids, timeline)
        decision = Item(
            id=ids.next(ItemType.DECISION),
            type=ItemType.DECISION,
            thread=thread_id,
            content=_option_content(evs, proposal.key),
            status=Status.NEEDS_CONFIRMATION,
            decided_by=nod.speaker,
            evidence=[
                Evidence(utt=nod.id, quote=nod.text, ts=nod.ts_label, speaker=nod.speaker),
                _evidence(proposal, tr),
            ],
            timeline=timeline,
            **_with_reasons(
                [Reason(code=C.NOD_ONLY, params={"chair": nod.speaker, "key": proposal.key})]
            ),
        )
        return [decision, *others]

    # Trường hợp 4: chưa ai đồng ý → câu hỏi mở
    firsts = [e for e in evs if e.kind in (EventKind.PROPOSE, EventKind.REVISE, EventKind.OBJECT)]
    return [
        Item(
            id=ids.next(ItemType.OPEN_QUESTION),
            type=ItemType.OPEN_QUESTION,
            thread=thread_id,
            content=thread_title,
            status=Status.OPEN,
            evidence=[_evidence(e, tr) for e in (firsts or evs)[:2]],
            **_with_reasons([Reason(code=C.NO_AGREEMENT)]),
        )
    ]


def resolve_task(events: list[Event], tr: Transcript, ids: _Ids) -> Item:
    """Một task chỉ OPEN (đã nhận) khi owner tự nhận hoặc trả lời cam kết không rào đón."""
    evs = sorted(events, key=lambda e: tr.order(e.utt))
    assign = next((e for e in evs if e.kind == EventKind.ASSIGN), evs[0])
    owner = assign.owner or (assign.speaker if assign.kind == EventKind.COMMIT else None)
    content = assign.content or assign.quote
    reasons: list[Reason] = []

    absent_owner = bool(owner) and owner not in tr.names and owner in tr.known_names
    if absent_owner:
        # Quy ước Nash 12: giữ tên người vắng mặt, nhưng họ chưa thể nhận việc trong họp
        reasons.append(Reason(code=C.OWNER_ABSENT, params={"owner": owner, "content": content}))
    elif owner and owner not in tr.names:
        reasons.append(Reason(code=C.OWNER_MISSING, params={"name": owner, "content": content}))
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

    who = {"owner": owner, "content": content}
    if owner is None or absent_owner:
        status = Status.NEEDS_CONFIRMATION
        if owner is None:
            reasons.append(Reason(code=C.OWNER_MISSING, params={"content": content}))
    elif declined:
        status = Status.NEEDS_CONFIRMATION
        reasons.append(Reason(code=C.OWNER_DECLINED, params=who))
    elif (self_assigned and not _hedged(assign)) or committed:
        status = Status.OPEN
    else:
        status = Status.NEEDS_CONFIRMATION
        reasons.append(Reason(code=C.OWNER_UNCONFIRMED, params=who))

    deadline_text = next((e.deadline_text for e in reversed(evs) if e.deadline_text), None) or next(
        (p for e in reversed(evs) if (p := extract_deadline_phrase(e.quote))), None
    )
    deadline = resolve_deadline(deadline_text, tr.date)
    if deadline_text and not deadline:
        reasons.append(Reason(code=C.DEADLINE_VAGUE, params={"deadline_text": deadline_text}))

    return Item(
        id=ids.next(ItemType.TASK),
        type=ItemType.TASK,
        thread=assign.thread,
        content=content,
        status=status,
        owner=owner,
        deadline=deadline,
        deadline_text=deadline_text,
        evidence=[_evidence(e, tr) for e in evs],
        **_with_reasons(reasons),
    )


def _standalone(e: Event, tr: Transcript, ids: _Ids) -> Item:
    """Vướng mắc / câu hỏi / yêu cầu: Đang mở. Tri thức / phản hồi: Ghi nhận (+ phạm vi)."""
    item_type = STANDALONE_EVENTS[e.kind]
    content = e.content or e.quote
    status = Status.NOTED if item_type in (ItemType.KNOWLEDGE, ItemType.FEEDBACK) else Status.OPEN
    extra: dict = {}
    if item_type == ItemType.KNOWLEDGE:
        text = e.quote or content
        durable = e.durable_hint or is_durable(text)
        extra["scope"] = "durable" if durable else "meeting"
        if durable:  # tri thức lâu dài luôn hỏi 1 lần trước khi vào Kho (SPEC M3 §4.3)
            params = {"content": content, "hearsay": is_hearsay(text)}
            extra |= _with_reasons([Reason(code=C.DURABLE_KNOWLEDGE, params=params)])
    return Item(
        id=ids.next(item_type),
        type=item_type,
        thread=e.thread,
        content=content,
        status=status,
        evidence=[_evidence(e, tr)],
        **extra,
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
        items.append(_standalone(e, tr, ids))

    items.sort(key=lambda i: min((tr.order(ev.utt) for ev in i.evidence), default=10**9))
    for i in items:
        check_status(i.type, i.status)
    return Ledger(
        meeting_id=tr.meeting_id,
        generated_by=generated_by,
        threads=extraction.threads,
        items=items,
    )
