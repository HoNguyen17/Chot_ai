from pathlib import Path

from fastapi.testclient import TestClient

from chot.adapters.baselines import KeywordBaseline
from chot.adapters.parsing import parse_transcript
from chot.adapters.persistence import InMemoryRepository
from chot.api.deps import get_service
from chot.api.main import create_app
from chot.usecases.meetings import MeetingService


def _client():
    app = create_app()
    svc = MeetingService(InMemoryRepository(), KeywordBaseline(), parse_transcript)
    app.dependency_overrides[get_service] = lambda: svc
    return TestClient(app)


def test_full_flow(data_dir):
    c = _client()
    text = (data_dir / "raw" / "m01.txt").read_text(encoding="utf-8")

    r = c.post("/meetings", json={"transcript_text": text})
    assert r.status_code == 201
    body = r.json()
    mid = body["id"]
    assert body["ledger"]["items"]

    item_id = body["ledger"]["items"][0]["id"]
    r = c.patch(f"/meetings/{mid}/items/{item_id}", json={"status": "needs_confirmation"})
    assert r.status_code == 200

    # Còn mục "Cần xác nhận" chưa duyệt? Ở đây vừa sửa nên đã tính là duyệt → publish được.
    assert c.post(f"/meetings/{mid}/publish").status_code == 200

    md = c.get(f"/meetings/{mid}/export?format=md")
    assert md.status_code == 200 and "BIÊN BẢN HỌP" in md.text
    assert c.get(f"/meetings/{mid}/export?format=csv").text.startswith("id,task")
    assert c.get("/meetings").json()[0]["id"] == mid


def test_publish_blocked_until_needs_confirmation_reviewed():
    from chot.domain.models import Event, ExtractionResult
    from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor

    extraction = ExtractionResult(
        events=[
            Event(
                utt="u001",
                thread="t",
                kind="assign",
                speaker="Sếp",
                key="x",
                owner="An",
                content="Làm X",
                quote="An làm X nhé",
            )
        ]
    )  # An chỉ "Dạ vâng" → task Cần xác nhận
    app = create_app()
    svc = MeetingService(
        InMemoryRepository(), RulesLedgerBuilder(StaticExtractor(extraction)), parse_transcript
    )
    app.dependency_overrides[get_service] = lambda: svc
    c = TestClient(app)

    text = "# participants: Sếp (chủ trì); An\n[00:01] Sếp: An làm X nhé.\n[00:02] An: Dạ vâng."
    body = c.post("/meetings", json={"transcript_text": text, "meeting_id": "x1"}).json()
    mid, task = body["id"], body["ledger"]["items"][0]
    assert task["status"] == "needs_confirmation"
    assert c.post(f"/meetings/{mid}/publish").status_code == 409
    c.patch(f"/meetings/{mid}/items/{task['id']}", json={"approved": True})
    assert c.post(f"/meetings/{mid}/publish").status_code == 200


def test_bad_transcript_returns_422():
    assert _client().post("/meetings", json={"transcript_text": "rác"}).status_code == 422


def test_replay_builder_falls_back_to_keyword(data_dir, monkeypatch):
    from chot.api.deps import make_builder
    from chot.config import Settings

    monkeypatch.setenv("LEDGER_BUILDER", "replay")
    builder = make_builder(Settings())
    tr = parse_transcript((data_dir / "raw" / "m01.txt").read_text(encoding="utf-8"))
    assert builder.build(tr).generated_by.startswith("rules-v1+replay")
    other = parse_transcript("# meeting: zz\n[00:01] A: Chốt luôn.")
    assert builder.build(other).generated_by == "keyword-baseline"


DEMO_EVENTS = Path(__file__).resolve().parents[1] / "demo_events"


class FakeClient:
    """Client LLM giả: đếm số lần gọi, trả về không sự kiện nào."""

    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, prompt, schema):
        self.calls += 1
        return '{"threads": [], "events": []}'


def _llm_client(monkeypatch, **env):
    from chot.api.deps import make_builder
    from chot.config import Settings

    monkeypatch.setenv("LEDGER_BUILDER", "llm")
    monkeypatch.setenv("REPLAY_EVENTS_DIR", str(DEMO_EVENTS))
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    fake = FakeClient()
    app = create_app()
    svc = MeetingService(InMemoryRepository(), make_builder(Settings(), fake), parse_transcript)
    app.dependency_overrides[get_service] = lambda: svc
    return TestClient(app), fake


def test_rejects_transcript_over_max_chars(monkeypatch):
    monkeypatch.setenv("MAX_TRANSCRIPT_CHARS", "50")
    r = _client().post("/meetings", json={"transcript_text": "[00:01] A: " + "x" * 60})
    assert r.status_code == 413 and "tối đa 50" in r.json()["detail"]


def test_llm_rate_limit_per_ip(monkeypatch):
    c, fake = _llm_client(monkeypatch, LLM_RATE_LIMIT_PER_HOUR="2")
    body = {"transcript_text": "[00:01] A: Chốt luôn.", "meeting_id": "zz1"}
    codes = [c.post("/meetings", json=body).status_code for _ in range(3)]
    assert codes == [201, 201, 429] and fake.calls == 2


def test_sample_meeting_replays_without_llm(monkeypatch, data_dir):
    c, fake = _llm_client(monkeypatch)
    text = (data_dir / "raw" / "m01.txt").read_text(encoding="utf-8")
    r = c.post("/meetings", json={"transcript_text": text, "meeting_id": "m01"})
    assert r.status_code == 201 and fake.calls == 0
    assert r.json()["ledger"]["generated_by"].startswith("rules-v1+replay")


CODE = "ma-truy-cap-16-ky-tu"


def test_new_transcript_requires_access_code(monkeypatch):
    c, fake = _llm_client(monkeypatch, LLM_ACCESS_CODE=CODE)
    body = {"transcript_text": "[00:01] A: Chốt luôn.", "meeting_id": "zz1"}
    assert c.post("/meetings", json=body).status_code == 401
    wrong = c.post("/meetings", json=body, headers={"X-Access-Code": "sai"})
    assert wrong.status_code == 401 and "mã truy cập" in wrong.json()["detail"]
    assert fake.calls == 0
    ok = c.post("/meetings", json=body, headers={"X-Access-Code": CODE})
    assert ok.status_code == 201 and fake.calls == 1


def test_sample_replays_without_access_code(monkeypatch, data_dir):
    c, fake = _llm_client(monkeypatch, LLM_ACCESS_CODE=CODE)
    text = (data_dir / "raw" / "m01.txt").read_text(encoding="utf-8")
    r = c.post("/meetings", json={"transcript_text": text, "meeting_id": "m01"})
    assert r.status_code == 201 and fake.calls == 0


def test_public_demo_without_code_refuses_llm(monkeypatch):
    c, fake = _llm_client(monkeypatch, PUBLIC_DEMO="true")
    body = {"transcript_text": "[00:01] A: Chốt luôn.", "meeting_id": "zz1"}
    r = c.post("/meetings", json=body, headers={"X-Access-Code": ""})
    assert r.status_code == 401 and fake.calls == 0


def test_meeting_id_cannot_escape_replay_dir(tmp_path):
    import pytest

    from chot.usecases.build_ledger import DirectoryReplayExtractor

    assert (
        _client()
        .post("/meetings", json={"transcript_text": "[00:01] A: x", "meeting_id": "../x"})
        .status_code
        == 422
    )
    (tmp_path / "secret.json").write_text('{"threads": [], "events": []}', encoding="utf-8")
    (tmp_path / "events").mkdir()
    tr = parse_transcript("# meeting: ../secret\n[00:01] A: x")
    with pytest.raises(LookupError):
        DirectoryReplayExtractor(tmp_path / "events").extract(tr)


def test_edited_sample_goes_to_llm(monkeypatch, data_dir):
    c, fake = _llm_client(monkeypatch)
    text = (data_dir / "raw" / "m01.txt").read_text(encoding="utf-8") + "\n[00:30:00] Hùng: Thêm."
    r = c.post("/meetings", json={"transcript_text": text, "meeting_id": "m01"})
    assert r.status_code == 201 and fake.calls == 1


def test_record_ids_are_random_not_meeting_id(data_dir):
    c = _client()
    text = (data_dir / "raw" / "m01.txt").read_text(encoding="utf-8")
    ids = {c.post("/meetings", json={"transcript_text": text}).json()["id"] for _ in range(2)}
    assert len(ids) == 2 and "m01" not in ids


def test_public_demo_hides_list_and_docs(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO", "true")
    c = _client()
    assert c.get("/meetings").status_code in (404, 405)
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


def test_rejects_oversized_body():
    r = _client().post("/meetings", json={"transcript_text": "x" * 200_000})
    assert r.status_code == 413 and "quá lớn" in r.json()["detail"]


def test_memory_repo_keeps_latest_records(monkeypatch, data_dir):
    from chot.adapters.persistence import memory

    monkeypatch.setattr(memory, "MAX_RECORDS", 2)
    repo = memory.InMemoryRepository()
    svc = MeetingService(repo, KeywordBaseline(), parse_transcript)
    text = (data_dir / "raw" / "m01.txt").read_text(encoding="utf-8")
    first, *_ = [svc.process(text).id for _ in range(3)]
    assert len(repo.list()) == 2 and repo.get(first) is None
