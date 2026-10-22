"""P5 (SPEC M3 §5–§6): nhóm họp bằng link bí mật, trả lời câu hỏi, Kho tri thức — InMemory."""

from fastapi.testclient import TestClient

from chot.adapters.parsing import parse_transcript
from chot.adapters.persistence import InMemoryRepository
from chot.api.deps import get_service
from chot.api.main import create_app
from chot.domain.models import Event, ExtractionResult
from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor
from chot.usecases.meetings import MeetingService

TEXT = "\n".join(
    [
        "# participants: Sếp (chủ trì); An; Bình",
        "[00:01] Sếp: Từ nay mọi hoá đơn phải có mã PO.",
        "[00:02] Bình: Nghe nói khách chỉ dùng MoMo.",
        "[00:03] Sếp: An làm báo giá nhé.",
        "[00:04] An: Dạ vâng.",
    ]
)
EVENTS = ExtractionResult(
    events=[
        Event(utt="u001", thread="hd", kind="info", speaker="Sếp", durable_hint=True,
              content="Mọi hoá đơn phải có mã PO", quote="Từ nay mọi hoá đơn phải có mã PO"),
        Event(utt="u002", thread="tt", kind="info", speaker="Bình", durable_hint=True, hedged=True,
              content="Khách chỉ dùng MoMo", quote="Nghe nói khách chỉ dùng MoMo"),
        Event(utt="u003", thread="bg", kind="assign", speaker="Sếp", key="bao-gia", owner="An",
              content="Làm báo giá", quote="An làm báo giá nhé"),
    ]
)  # fmt: skip


def _client() -> tuple[TestClient, MeetingService]:
    app = create_app()
    svc = MeetingService(
        InMemoryRepository(), RulesLedgerBuilder(StaticExtractor(EVENTS)), parse_transcript
    )
    app.dependency_overrides[get_service] = lambda: svc
    return TestClient(app), svc


def _meeting(c: TestClient) -> tuple[str, str, dict]:
    sid = c.post("/series", json={"name": "Weekly sync"}).json()["id"]
    r = c.post(f"/series/{sid}/meetings", json={"transcript_text": TEXT})
    assert r.status_code == 201, r.text
    body = r.json()
    return sid, body["id"], {i["content"]: i for i in body["ledger"]["items"]}


def test_series_id_is_secret_and_unknown_is_404():
    c, _ = _client()
    ids = [c.post("/series", json={"name": "Nhóm"}).json()["id"] for _ in range(2)]
    assert ids[0] != ids[1] and all(len(i) >= 16 for i in ids)
    assert c.get(f"/series/{ids[0]}").json()["name"] == "Nhóm"
    assert c.get("/series/khong-co").status_code == 404


def test_meeting_ids_are_secret_too():
    c, _ = _client()
    _, mid, _ = _meeting(c)
    assert len(mid) >= 16


def test_answer_then_publish_fills_knowledge_store_with_confirmed_only():
    c, _ = _client()
    sid, mid, items = _meeting(c)
    po, momo, task = (items[k] for k in ("Mọi hoá đơn phải có mã PO", "Khách chỉ dùng MoMo",
                                          "Làm báo giá"))  # fmt: skip
    body = c.get(f"/meetings/{mid}").json()
    assert {q["item_id"] for q in body["questions"]} == {po["id"], momo["id"], task["id"]}
    assert body["series_id"] == sid

    for item, action in ((po, "confirm"), (momo, "reject"), (task, "defer")):
        r = c.post(f"/meetings/{mid}/items/{item['id']}/answer", json={"action": action})
        assert r.status_code == 200, r.text
    assert c.get(f"/meetings/{mid}").json()["questions"] == []
    assert c.post(f"/meetings/{mid}/publish").status_code == 200
    assert c.post(f"/meetings/{mid}/publish").status_code == 200  # lần 2 không nhân đôi Kho

    series = c.get(f"/series/{sid}").json()
    assert [k["content"] for k in series["knowledge"]] == ["Mọi hoá đơn phải có mã PO"]
    assert series["knowledge"][0]["evidence"][0]["utt"] == "u001"
    assert [p["item"]["id"] for p in series["pending"]] == [task["id"]]
    assert [m["id"] for m in series["meetings"]] == [mid]


def test_answer_validates_input():
    c, _ = _client()
    _, mid, items = _meeting(c)
    url = f"/meetings/{mid}/items/{items['Làm báo giá']['id']}/answer"
    assert c.post(url, json={"action": "xoa"}).status_code == 422
    assert c.post(url, json={"action": "confirm", "owner": "Người lạ"}).status_code == 422
    assert c.post(f"/meetings/{mid}/items/X9/answer", json={"action": "confirm"}).status_code == 404


def test_published_meeting_is_locked():
    c, _ = _client()
    _, mid, items = _meeting(c)
    for item in items.values():
        c.post(f"/meetings/{mid}/items/{item['id']}/answer", json={"action": "defer"})
    assert c.post(f"/meetings/{mid}/publish").status_code == 200
    any_id = next(iter(items.values()))["id"]
    r = c.post(f"/meetings/{mid}/items/{any_id}/answer", json={"action": "confirm"})
    assert r.status_code == 409 and "xuất bản" in r.json()["detail"]
    assert c.patch(f"/meetings/{mid}/items/{any_id}", json={"content": "x"}).status_code == 409


def test_review_log_is_append_only(data_dir):
    c, svc = _client()
    _, mid, items = _meeting(c)
    task = items["Làm báo giá"]["id"]
    c.post(f"/meetings/{mid}/items/{task}/answer", json={"action": "confirm"})
    before = [e.model_dump() for e in svc.repo.get(mid).review_log]
    c.patch(f"/meetings/{mid}/items/{task}", json={"owner": "Bình"})
    after = [e.model_dump() for e in svc.repo.get(mid).review_log]
    assert len(after) > len(before) and after[: len(before)] == before
    for method in ("put", "delete"):
        assert getattr(c, method)(f"/meetings/{mid}/items/{task}").status_code == 405


def test_sample_series_is_read_only(monkeypatch):
    from chot.api import deps

    monkeypatch.setenv("LEDGER_BUILDER", "keyword")
    deps.get_service.cache_clear()
    try:
        c = TestClient(create_app())
        series = c.get(f"/series/{deps.SAMPLE_SERIES_ID}").json()
        assert series["read_only"] and len(series["meetings"]) == 5
        mid = series["meetings"][0]["id"]
        ledger = c.get(f"/meetings/{mid}").json()["ledger"]
        assert ledger["generated_by"].startswith("rules-v1+replay")
        item = ledger["items"][0]["id"]
        blocked = [
            c.post(f"/meetings/{mid}/items/{item}/answer", json={"action": "confirm"}),
            c.patch(f"/meetings/{mid}/items/{item}", json={"content": "x"}),
            c.post(f"/meetings/{mid}/publish"),
            c.post(f"/series/{deps.SAMPLE_SERIES_ID}/meetings", json={"transcript_text": TEXT}),
        ]
        assert [r.status_code for r in blocked] == [403] * 4
        assert "chỉ để xem" in blocked[0].json()["detail"]
    finally:
        deps.get_service.cache_clear()


def test_create_series_is_rate_limited(monkeypatch):
    monkeypatch.setenv("SERIES_RATE_LIMIT_PER_HOUR", "2")
    c, _ = _client()
    codes = [c.post("/series", json={"name": "x"}).status_code for _ in range(3)]
    assert codes == [201, 201, 429]


def test_meeting_list_never_shows_series_meetings():
    c, _ = _client()
    _meeting(c)  # thuộc nhóm (link bí mật)
    solo = c.post("/meetings", json={"transcript_text": TEXT}).json()["id"]
    assert [m["id"] for m in c.get("/meetings").json()] == [solo]


def test_long_sample_series_replays_l1_to_l4(monkeypatch):
    from chot.api import deps

    monkeypatch.setenv("LEDGER_BUILDER", "keyword")
    deps.get_service.cache_clear()
    try:
        c = TestClient(create_app())
        series = c.get(f"/series/{deps.LONG_SAMPLE_SERIES_ID}").json()
        assert series["read_only"] and len(series["meetings"]) == 4
        l1 = next(m for m in series["meetings"] if m["title"].startswith("Họp tuần liên phòng"))
        items = c.get(f"/meetings/{l1['id']}").json()["ledger"]["items"]
        # T1: quyết định MoMo của khối m01 vẫn Đã chốt khi nằm trong họp dài
        assert any(i["type"] == "decision" and i["status"] == "final" and "MoMo" in i["content"]
                   for i in items)  # fmt: skip
    finally:
        deps.get_service.cache_clear()
