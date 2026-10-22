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


# ---- M3: mã lý do, timeline, tri thức (kết luận trạng thái không đổi so với M2) ----------------
from pathlib import Path  # noqa: E402

from chot.adapters.parsing import parse_transcript_file  # noqa: E402
from chot.domain.reasons import ReasonCode as C  # noqa: E402
from chot.domain.text import is_durable, is_hearsay  # noqa: E402

_ROOT = Path(__file__).resolve().parents[3]


def codes(item):
    return [r.code for r in item.reasons]


def test_co_chair_objection_gives_reason_with_names():
    tr = _tr(
        "[00:10] Bình: Em đề xuất B.",
        "[00:20] Hai: Anh thấy B rủi ro.",
        "[00:30] Sếp: Chị quyết đi B.",
        participants="Sếp (chủ trì); Hai (chủ trì); Bình",
    )
    (d,) = decisions(
        ledger_for(
            tr,
            [
                ev("u001", K.PROPOSE, "Bình", "B"),
                ev("u002", K.OBJECT, "Hai", "B", quote="B rủi ro"),
                ev("u003", K.AGREE, "Sếp", "B", quote="Chị quyết đi B"),
            ],
        )
    )
    (r,) = d.reasons
    assert r.code == C.CO_CHAIR_OBJECTION
    assert r.params == {"chair": "Sếp", "co_chair": "Hai", "key": "B"}


def test_m23_oracle_tiktok_decision_flags_co_chair_objection():
    tr = parse_transcript_file(_ROOT / "data" / "raw" / "m23.txt")
    extraction = ExtractionResult.model_validate_json(
        (Path(__file__).parent / "fixtures" / "oracle_events" / "m23.json").read_text(
            encoding="utf-8"
        )
    )
    tiktok = next(
        d for d in decisions(build_ledger(tr, extraction)) if "u006" in [e.utt for e in d.evidence]
    )
    assert tiktok.status == Status.NEEDS_CONFIRMATION and C.CO_CHAIR_OBJECTION in codes(tiktok)


def test_fallback_is_info_not_question():
    tr = _tr(
        "[00:10] An: Em đề xuất A.", "[00:20] Sếp: Chốt dùng B. Nếu thứ Năm B trễ thì quay lại A."
    )
    (d,) = decisions(
        ledger_for(
            tr,
            [
                ev("u001", K.PROPOSE, "An", "A"),
                ev(
                    "u002",
                    K.AGREE,
                    "Sếp",
                    "B",
                    quote="Chốt dùng B. Nếu thứ Năm B trễ thì quay lại A",
                ),
            ],
        )
    )
    assert d.status == Status.FINAL and codes(d) == [C.FALLBACK_KEPT]
    assert not any(r.asking for r in d.reasons)
    assert d.flags == [
        "có điều kiện quay lại phương án cũ — phương án cũ vẫn mở"
    ]  # export cũ giữ chữ


def test_hedged_and_nod_reasons_carry_question_params(mini):
    led = ledger_for(
        mini,
        [
            ev("u002", K.PROPOSE, "Bình", "B"),
            ev("u003", K.AGREE, "Sếp", "B", quote="Tạm thời đi B nhé"),
        ],
    )
    (r,) = decisions(led)[0].reasons
    assert r.code == C.HEDGED and r.params == {
        "speaker": "Sếp",
        "quote": "Tạm thời đi B nhé",
        "key": "B",
    }


def test_task_reasons_owner_absent_and_vague_deadline():
    tr = _tr("[00:10] Sếp: Chi làm báo cáo, tuần sau nộp.", absent="Chi (Kế toán)")
    led = ledger_for(
        tr,
        [
            ev(
                "u001",
                K.ASSIGN,
                "Sếp",
                "bao-cao",
                owner="Chi",
                content="Làm báo cáo",
                quote="Chi làm báo cáo, tuần sau nộp",
            )
        ],
    )
    (t,) = [i for i in led.items if i.type == ItemType.TASK]
    assert codes(t) == [C.OWNER_ABSENT, C.DEADLINE_VAGUE]
    assert t.reasons[0].params == {"owner": "Chi", "content": "Làm báo cáo"}
    assert t.reasons[1].params == {"deadline_text": "tuần sau"}


def test_decision_timeline_lists_thread_events_in_order(mini):
    led = ledger_for(
        mini,
        [
            ev("u002", K.PROPOSE, "Bình", "B", quote="đề xuất B"),
            ev("u001", K.PROPOSE, "An", "A", quote="đề xuất A"),
            ev("u005", K.AGREE, "Sếp", "B", quote="Chốt dùng B"),
        ],
    )
    (d,) = decisions(led)
    assert [(t.utt, t.kind, t.key) for t in d.timeline] == [
        ("u001", K.PROPOSE, "A"),
        ("u002", K.PROPOSE, "B"),
        ("u005", K.AGREE, "B"),
    ]
    assert d.timeline[0].speaker == "An" and d.timeline[2].quote == "Chốt dùng B"
    (opt,) = [i for i in led.items if i.type == ItemType.OPTION]
    assert opt.timeline == d.timeline


def _knowledge(quote, **kw):
    tr = _tr(f"[00:10] Sếp: {quote}")
    led = ledger_for(tr, [ev("u001", K.INFO, "Sếp", content=quote, quote=quote, **kw)])
    (k,) = led.items
    return k


def test_knowledge_is_noted_with_meeting_scope_by_default():
    k = _knowledge("Đơn Tết năm nay khoảng 120 pallet.")
    assert k.type == ItemType.KNOWLEDGE and k.status == Status.NOTED
    assert k.scope == "meeting" and k.reasons == []


def test_durable_knowledge_always_asks():
    k = _knowledge("Từ nay mọi lô hàng xuất kho phải có mã PO của khách.")
    assert k.scope == "durable" and codes(k) == [C.DURABLE_KNOWLEDGE]
    assert k.reasons[0].params["hearsay"] is False


def test_hearsay_knowledge_is_durable_but_warned():
    k = _knowledge("Nghe nói khách bên Đà Nẵng chỉ nhận hàng đường bộ.")
    assert k.scope == "durable" and k.reasons[0].params["hearsay"] is True


def test_llm_durable_hint_marks_durable():
    assert _knowledge("Kho Bình Dương đóng cửa Chủ nhật.", durable_hint=True).scope == "durable"


def test_feedback_is_noted():
    tr = _tr("[00:10] An: Khách khen mẫu mới.")
    (f,) = ledger_for(
        tr, [ev("u001", K.FEEDBACK, "An", content="Khách khen", quote="Khách khen mẫu mới")]
    ).items
    assert f.status == Status.NOTED


def test_durable_and_hearsay_signals():
    assert is_durable("Từ giờ hoá đơn bắt buộc có mã PO")
    assert is_durable("Quy định công ty: vi phạm lần đầu phạt 500 nghìn")
    assert is_durable("Khách bên đó chỉ dùng MoMo")
    assert not is_durable("Ok anh, em gửi luôn")
    assert not is_durable("Đơn Tết năm nay 120 pallet")
    assert is_hearsay("Nghe nói khách chỉ dùng MoMo") and is_hearsay("Hình như kho đóng Chủ nhật")
    assert not is_hearsay("Khách chỉ dùng MoMo")


def test_every_needs_confirmation_item_asks_on_oracle_set():
    fix = Path(__file__).parent / "fixtures" / "oracle_events"
    for p in sorted(fix.glob("m*.json")):
        tr = parse_transcript_file(_ROOT / "data" / "raw" / f"{p.stem}.txt")
        led = build_ledger(tr, ExtractionResult.model_validate_json(p.read_text(encoding="utf-8")))
        for i in led.items:
            if i.status == Status.NEEDS_CONFIRMATION:
                assert any(r.asking for r in i.reasons), (p.stem, i.id, i.flags)


# --- P4: luật chặn chốt nhầm còn lại trên họp dài (Nash duyệt 22/10/2026) ---


def test_chair_ok_on_a_task_is_not_a_decision():
    """LLM gán `agree` cho câu chủ trì gật đầu một việc vừa nhận (cùng key với assign)."""
    tr = _tr(
        "[00:10] An: Dạ, vậy em soạn tin nhắn giải thích gửi đại lý.",
        "[00:20] Sếp: Ừ, gửi trước khi áp dụng.",
    )
    led = ledger_for(
        tr,
        [
            ev("u001", K.ASSIGN, "An", "tin-nhan", owner="An", quote="em soạn tin nhắn"),
            ev("u002", K.AGREE, "Sếp", "tin-nhan", quote="Ừ, gửi trước khi áp dụng"),
        ],
    )
    assert decisions(led) == []
    assert [i.type for i in led.items] == [ItemType.TASK]


def test_agree_on_a_key_that_is_also_an_option_stays_a_decision():
    tr = _tr("[00:10] An: Em đề xuất A, em làm luôn.", "[00:20] Sếp: Chốt A.")
    led = ledger_for(
        tr,
        [
            ev("u001", K.PROPOSE, "An", "A"),
            ev("u001", K.ASSIGN, "An", "A", owner="An"),
            ev("u002", K.AGREE, "Sếp", "A", quote="Chốt A"),
        ],
    )
    assert [d.status for d in decisions(led)] == [Status.FINAL]


def test_fallback_kept_when_co_chair_agrees_after_conditional_decision():
    tr = _tr(
        "[00:10] An: Em đề xuất đi đường bộ.",
        "[00:20] Bình: Em đề xuất đường biển.",
        "[00:30] Sếp: Vậy chốt nhé: đi đường biển. Nếu tới 15/11 chưa có chỗ thì quay về đường bộ.",
        "[00:40] Hạnh: Ok, chị đồng ý.",
        participants="Sếp (chủ trì); Hạnh (đồng chủ trì); An; Bình",
    )
    led = ledger_for(
        tr,
        [
            ev("u001", K.PROPOSE, "An", "bộ"),
            ev("u002", K.PROPOSE, "Bình", "biển"),
            # LLM chỉ chép đoạn ngắn nhất — mệnh đề "Nếu…" nằm ngoài quote
            ev("u003", K.AGREE, "Sếp", "biển", quote="Vậy chốt nhé: đi đường biển"),
            ev("u004", K.AGREE, "Hạnh", "biển", quote="Ok, chị đồng ý"),
        ],
    )
    (d,) = decisions(led)
    assert d.status == Status.FINAL and C.FALLBACK_KEPT in codes(d)
    (opt,) = [i for i in led.items if i.type == ItemType.OPTION]
    assert opt.status == Status.OPEN and d.supersedes == []


def test_chair_decision_followed_by_commit_stays_a_decision():
    """m04: chủ trì quyết trước, người làm nhận sau (cùng key) → vẫn là quyết định."""
    tr = _tr(
        "[00:10] Sếp: Từ tuần sau xưởng làm thêm ca tối thứ Bảy.",
        "[00:20] An: Dạ, em sắp xếp người.",
    )
    led = ledger_for(
        tr,
        [
            ev("u001", K.AGREE, "Sếp", "ca-toi", quote="Từ tuần sau xưởng làm thêm ca tối thứ Bảy"),
            ev("u002", K.COMMIT, "An", "ca-toi", owner="An", quote="em sắp xếp người"),
        ],
    )
    assert [d.status for d in decisions(led)] == [Status.FINAL]


def test_restating_a_previous_meeting_decision_is_not_a_new_decision():
    """m24 (gold Nash): "vẫn ở bản 3.3 như đã chốt" nhắc lại quyết định họp trước, không phải mới."""
    tr = _tr(
        "[00:10] An: Khách hỏi đưa báo cáo vào bản 3.2 luôn được không.",
        "[00:20] Sếp: Không, báo cáo vẫn ở bản 3.3 như đã chốt.",
    )
    led = ledger_for(tr, [ev("u002", K.AGREE, "Sếp", "bao-cao-3.3", quote="vẫn ở bản 3.3")])
    assert decisions(led) == []
