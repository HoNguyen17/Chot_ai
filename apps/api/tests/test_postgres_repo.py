"""PostgresRepository trên DB thật — chỉ chạy khi có TEST_DATABASE_URL (DB nháp, đã chạy 001 + 002).

Dữ liệu test ở lại DB (review_actions append-only, không xoá được) → đừng trỏ vào DB production.
"""

import os

import psycopg
import pytest
from test_api_series import EVENTS, TEXT

from chot.adapters.parsing import parse_transcript
from chot.adapters.persistence import PostgresRepository
from chot.usecases.build_ledger import RulesLedgerBuilder, StaticExtractor
from chot.usecases.meetings import MeetingService

DSN = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="cần TEST_DATABASE_URL (DB nháp)")


def test_round_trip_and_review_log_is_append_only():
    svc = MeetingService(
        PostgresRepository(DSN), RulesLedgerBuilder(StaticExtractor(EVENTS)), parse_transcript
    )
    series = svc.create_series("test P5")
    rec = svc.process(TEXT, series_id=series.id)
    ids = {i.content: i.id for i in rec.ledger.items}
    svc.answer(rec.id, ids["Mọi hoá đơn phải có mã PO"], "confirm")
    svc.answer(rec.id, ids["Khách chỉ dùng MoMo"], "reject")
    rec = svc.answer(rec.id, ids["Làm báo giá"], "defer")
    rec = svc.publish(rec.id)

    loaded = svc.repo.get(rec.id)
    assert loaded == rec and loaded.ledger.events == rec.ledger.events
    view = svc.series_view(series.id)
    assert [k.content for k in view.knowledge] == ["Mọi hoá đơn phải có mã PO"]
    with psycopg.connect(DSN, prepare_threshold=None) as conn, pytest.raises(psycopg.Error):
        conn.execute("update review_actions set field = 'x' where meeting_id = %s", (rec.id,))
