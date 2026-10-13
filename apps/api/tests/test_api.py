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
    assert body["id"] == "m01" and body["ledger"]["items"]

    item_id = body["ledger"]["items"][0]["id"]
    r = c.patch(f"/meetings/m01/items/{item_id}", json={"status": "needs_confirmation"})
    assert r.status_code == 200

    # Còn mục "Cần xác nhận" chưa duyệt? Ở đây vừa sửa nên đã tính là duyệt → publish được.
    assert c.post("/meetings/m01/publish").status_code == 200

    md = c.get("/meetings/m01/export?format=md")
    assert md.status_code == 200 and "BIÊN BẢN HỌP" in md.text
    assert c.get("/meetings/m01/export?format=csv").text.startswith("id,task")
    assert c.get("/meetings").json()[0]["id"] == "m01"


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
    task = body["ledger"]["items"][0]
    assert task["status"] == "needs_confirmation"
    assert c.post("/meetings/x1/publish").status_code == 409
    c.patch(f"/meetings/x1/items/{task['id']}", json={"approved": True})
    assert c.post("/meetings/x1/publish").status_code == 200


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
