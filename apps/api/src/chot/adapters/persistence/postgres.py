"""PostgresRepository — Supabase / Postgres 15+. Schema: db/migrations/001_init.sql + 002_m3.sql.

- Transcript, sự kiện, bản đồ chủ đề: ghi 1 lần khi tạo (đủ để replay khi sửa luật).
- Mục (items): xoá + chèn lại mỗi lần lưu, trong cùng transaction.
- review_actions: chỉ chèn (`entry_id` chống trùng); DB có trigger chặn sửa / xoá.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from chot.domain.models import Event, Item, Ledger, Participant, Thread, Transcript, Utterance
from chot.usecases.meetings import (
    KnowledgeEntry,
    MeetingRecord,
    MeetingRepository,
    ReviewLogEntry,
    Series,
)

_ITEM_JSON = ["reasons", "timeline", "evidence"]
_ITEM_COLS = (
    "id type status thread content owner decided_by deadline deadline_text supersedes flags "
    "confidence review_state scope"
).split()


class PostgresRepository(MeetingRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn  # không bao giờ in / log

    def _conn(self) -> psycopg.Connection[dict[str, Any]]:
        # Pooler Supabase (transaction mode) không hỗ trợ prepared statement → prepare_threshold=None
        # ponytail: 1 kết nối / thao tác; thêm psycopg_pool khi độ trễ thành vấn đề
        return psycopg.connect(self._dsn, prepare_threshold=None, row_factory=dict_row)

    # --- cuộc họp ---------------------------------------------------------------------------

    def save(self, record: MeetingRecord) -> None:
        with self._conn() as conn:
            # Khoá dòng meeting: 2 request lưu cùng cuộc họp chạy lần lượt.
            # ponytail: mục thì người lưu sau thắng; nhật ký duyệt vẫn đủ nhờ entry_id
            exists = conn.execute(
                "select 1 from meetings where id = %s for update", (record.id,)
            ).fetchone()
            if exists:
                conn.execute(
                    "update meetings set published = %s, published_at = case when %s "
                    "then coalesce(published_at, now()) end where id = %s",
                    (record.published, record.published, record.id),
                )
            else:
                _insert_meeting(conn, record)
            conn.execute("delete from items where meeting_id = %s", (record.id,))
            with conn.cursor() as cur:
                cur.executemany(
                    f"insert into items (meeting_id, idx, approved, {', '.join(_ITEM_COLS)}, "
                    f"{', '.join(_ITEM_JSON)}) values (%s, %s, %s"
                    + ", %s" * (len(_ITEM_COLS) + len(_ITEM_JSON))
                    + ")",
                    [_item_row(record, n, i) for n, i in enumerate(record.ledger.items)],
                )
                cur.executemany(
                    "insert into review_actions (meeting_id, entry_id, item_id, field, old_value, "
                    "new_value, action, reviewer, at) values (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "on conflict (entry_id) do nothing",
                    [
                        (record.id, e.id, e.item_id, e.field, e.old, e.new, e.action, e.by, e.at)
                        for e in record.review_log
                    ],
                )

    def get(self, meeting_id: str) -> MeetingRecord | None:
        with self._conn() as conn:
            return _load(conn, meeting_id)

    def list(self, series_id: str | None = None) -> list[MeetingRecord]:
        with self._conn() as conn:
            rows = conn.execute(
                "select id from meetings where %(s)s::text is null or series_id = %(s)s "
                "order by created_at desc",
                {"s": series_id},
            ).fetchall()
            # ponytail: N+1 truy vấn trên 1 kết nối; đủ cho nhóm họp vài chục buổi
            return [r for row in rows if (r := _load(conn, row["id"]))]

    # --- nhóm họp + Kho tri thức ----------------------------------------------------------

    def save_series(self, series: Series) -> None:
        with self._conn() as conn:
            conn.execute(
                "insert into meeting_series (id, name, read_only, created_at) "
                "values (%s, %s, %s, %s) on conflict (id) do nothing",
                (series.id, series.name, series.read_only, series.created_at),
            )

    def get_series(self, series_id: str) -> Series | None:
        with self._conn() as conn:
            row = conn.execute(
                "select id, name, read_only, created_at from meeting_series where id = %s",
                (series_id,),
            ).fetchone()
        return Series(**row) if row else None

    def add_knowledge(self, entries: list[KnowledgeEntry]) -> None:
        if not entries:
            return
        with self._conn() as conn, conn.cursor() as cur:
            cur.executemany(
                "insert into knowledge (series_id, meeting_id, item_id, content, evidence, "
                "confirmed_by, confirmed_at) values (%s, %s, %s, %s, %s, %s, %s) "
                "on conflict (meeting_id, item_id) do update set content = excluded.content, "
                "evidence = excluded.evidence, confirmed_by = excluded.confirmed_by, "
                "confirmed_at = excluded.confirmed_at",
                [
                    (
                        e.series_id,
                        e.meeting_id,
                        e.item_id,
                        e.content,
                        Jsonb([ev.model_dump(mode="json") for ev in e.evidence]),
                        e.confirmed_by,
                        e.confirmed_at,
                    )
                    for e in entries
                ],
            )

    def knowledge(self, series_id: str) -> list[KnowledgeEntry]:
        with self._conn() as conn:
            rows = conn.execute(
                "select series_id, meeting_id, item_id, content, evidence, confirmed_by, "
                "confirmed_at from knowledge where series_id = %s order by id",
                (series_id,),
            ).fetchall()
        return [KnowledgeEntry(**r) for r in rows]


def _insert_meeting(conn: psycopg.Connection, record: MeetingRecord) -> None:
    tr, ledger = record.transcript, record.ledger
    conn.execute(
        "insert into meetings (id, series_id, source_id, title, meeting_date, generated_by, "
        "published, published_at, created_at) values (%s, %s, %s, %s, %s, %s, %s, "
        "case when %s then now() end, %s)",
        (
            record.id,
            record.series_id,
            tr.meeting_id,
            tr.title,
            tr.date,
            ledger.generated_by,
            record.published,
            record.published,
            record.created_at,
        ),
    )
    conn.execute(
        "insert into topic_maps (meeting_id, threads) values (%s, %s)",
        (record.id, Jsonb([t.model_dump(mode="json") for t in ledger.threads])),
    )
    with conn.cursor() as cur:
        people = [(p, False) for p in tr.participants] + [(p, True) for p in tr.absent]
        cur.executemany(
            "insert into participants (meeting_id, idx, name, role, is_chair, absent) "
            "values (%s, %s, %s, %s, %s, %s) on conflict do nothing",
            [(record.id, n, p.name, p.role, p.is_chair, a) for n, (p, a) in enumerate(people)],
        )
        cur.executemany(
            "insert into utterances (meeting_id, id, idx, ts_seconds, speaker, text) "
            "values (%s, %s, %s, %s, %s, %s)",
            [(record.id, u.id, u.index, u.ts, u.speaker, u.text) for u in tr.utterances],
        )
        cur.executemany(
            "insert into events (meeting_id, utt_id, thread, kind, speaker, key, content, hedged, "
            "owner, deadline_text, quote, durable_hint, new_key) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (record.id, e.utt, e.thread, e.kind, e.speaker, e.key, e.content, e.hedged,
                 e.owner, e.deadline_text, e.quote, e.durable_hint, e.new_key)
                for e in ledger.events
            ],
        )  # fmt: skip


def _item_row(record: MeetingRecord, n: int, item: Item) -> tuple[object, ...]:
    data = item.model_dump(mode="json")
    return (
        record.id,
        n,
        item.id in record.approved,
        *(data[c] for c in _ITEM_COLS),
        *(Jsonb(data[c]) for c in _ITEM_JSON),
    )


def _load(conn: psycopg.Connection, meeting_id: str) -> MeetingRecord | None:
    m = conn.execute("select * from meetings where id = %s", (meeting_id,)).fetchone()
    if not m:
        return None

    def rows(sql: str) -> list[dict[str, Any]]:
        return conn.execute(sql, (meeting_id,)).fetchall()

    people = rows(
        "select name, role, is_chair, absent from participants where meeting_id = %s order by idx"
    )
    utts = rows(
        "select id, idx as index, ts_seconds as ts, speaker, text from utterances "
        "where meeting_id = %s order by idx"
    )
    events = rows(
        "select utt_id as utt, thread, kind, speaker, key, content, hedged, owner, deadline_text, "
        "quote, durable_hint, new_key from events where meeting_id = %s order by id"
    )
    tmap = rows("select threads from topic_maps where meeting_id = %s")
    items = rows("select * from items where meeting_id = %s order by idx")
    reviews = rows(
        "select entry_id as id, item_id, field, old_value as old, new_value as new, action, "
        "reviewer as by, at from review_actions where meeting_id = %s order by id"
    )
    source = m["source_id"] or m["id"]
    tr = Transcript(
        meeting_id=source,
        title=m["title"],
        date=m["meeting_date"],
        participants=[Participant(**_pick(p, "name role is_chair")) for p in people if not p["absent"]],
        absent=[Participant(**_pick(p, "name role is_chair")) for p in people if p["absent"]],
        utterances=[Utterance(**u) for u in utts],
    )  # fmt: skip
    ledger = Ledger(
        meeting_id=source,
        generated_by=m["generated_by"],
        threads=[Thread(**t) for t in (tmap[0]["threads"] if tmap else [])],
        items=[Item(**_pick(i, " ".join(_ITEM_COLS + _ITEM_JSON))) for i in items],
        events=[Event(**e) for e in events],
    )
    return MeetingRecord(
        id=m["id"],
        series_id=m["series_id"],
        transcript=tr,
        ledger=ledger,
        approved={i["id"] for i in items if i["approved"]},
        published=m["published"],
        review_log=[ReviewLogEntry(**r) for r in reviews],
        created_at=m["created_at"],
    )


def _pick(row: dict[str, Any], cols: str) -> dict[str, Any]:
    return {c: row[c] for c in cols.split()}
