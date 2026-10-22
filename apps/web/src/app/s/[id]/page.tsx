"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { TYPE_LABEL } from "@/lib/labels";
import type { Series } from "@/lib/types";

const TABS = [
  { key: "meetings", title: "Buổi họp" },
  { key: "knowledge", title: "Kho tri thức" },
  { key: "pending", title: "Việc treo" },
] as const;

export default function SeriesPage() {
  const { id } = useParams<{ id: string }>();
  const [series, setSeries] = useState<Series | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("meetings");

  useEffect(() => {
    api.getSeries(id).then(setSeries).catch((e) => setError(String(e.message ?? e)));
  }, [id]);

  if (error) return <p className="alert">{error}</p>;
  if (!series) return <p className="muted">Đang tải…</p>;

  const title = (meetingId: string) => series.meetings.find((m) => m.id === meetingId)?.title ?? "buổi họp";

  return (
    <>
      <p className="faint">Nhóm họp{series.read_only && " mẫu · chỉ xem"}</p>
      <h1>{series.name}</h1>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}>
            {t.title} <span className="count">{series[t.key].length}</span>
          </button>
        ))}
      </div>

      {tab === "meetings" && (
        <div className="stack">
          {series.meetings.length === 0 && <p className="muted">Chưa có buổi họp nào.</p>}
          {series.meetings.map((m) => (
            <Link key={m.id} href={`/m/${m.id}`} className="card list-row">
              <span>
                <span className="mono faint">{m.date ?? "—"}</span> <b>{m.title ?? "Buổi họp"}</b>
              </span>
              <span className={m.published ? "faint" : "ask"}>
                {m.published ? "✓ đã xuất bản" : `${m.needs_confirmation} mục cần xác nhận`}
              </span>
            </Link>
          ))}
        </div>
      )}

      {tab === "knowledge" && (
        <div className="stack">
          <p className="faint">Chỉ mục người duyệt đã xác nhận khi xuất bản.</p>
          {series.knowledge.map((k) => (
            <div key={k.meeting_id + k.item_id} className="card">
              <p className="item-content">{k.content}</p>
              <p className="faint">
                từ <Link href={`/m/${k.meeting_id}`}>{title(k.meeting_id)}</Link>
                {k.evidence[0]?.utt && <>, {k.evidence[0].utt}</>}
                {k.confirmed_by && <> · xác nhận bởi {k.confirmed_by}</>}
              </p>
            </div>
          ))}
        </div>
      )}

      {tab === "pending" && (
        <div className="stack">
          <p className="faint">Mục &quot;để họp sau&quot; → đưa vào agenda buổi tới.</p>
          {series.pending.map(({ meeting_id, item }) => (
            <Link key={meeting_id + item.id} href={`/m/${meeting_id}`} className="card list-row">
              <span>
                <span className="type-label">{TYPE_LABEL[item.type]}</span> {item.content}
              </span>
              <StatusBadge item={item} />
            </Link>
          ))}
        </div>
      )}

      {!series.read_only && (
        <Link href={`/?series=${series.id}`} className="btn btn-primary" style={{ marginTop: 24 }}>
          + Buổi họp mới
        </Link>
      )}
      <p className="faint" style={{ marginTop: 16 }}>
        Không cần đăng nhập: ai có link nhóm này thì xem được. Đừng chia sẻ link ra ngoài.
      </p>
    </>
  );
}
