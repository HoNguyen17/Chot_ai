"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ItemCard } from "@/components/ItemCard";
import { api } from "@/lib/api";
import { SECTIONS } from "@/lib/labels";
import type { Meeting, Status } from "@/lib/types";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getMeeting(id).then(setMeeting).catch((e) => setError(String(e.message ?? e)));
  }, [id]);

  const review = useCallback(
    async (itemId: string, changes: { status?: Status; approved?: boolean }) => {
      setBusy(true);
      setError(null);
      try {
        setMeeting(await api.reviewItem(id, itemId, changes));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [id],
  );

  const grouped = useMemo(() => {
    if (!meeting) return [];
    return SECTIONS.map((s) => ({
      ...s,
      items: meeting.ledger.items.filter((i) => s.match(i.type, i.status)),
    })).filter((s) => s.items.length > 0);
  }, [meeting]);

  if (error && !meeting) return <p className="alert">{error}</p>;
  if (!meeting) return <p className="muted">Đang tải…</p>;

  const approved = new Set(meeting.approved);
  const pending = meeting.ledger.items.filter(
    (i) => i.status === "needs_confirmation" && !approved.has(i.id),
  ).length;
  const chair = meeting.participants.filter((p) => p.is_chair).map((p) => p.name).join(", ");
  const finals = meeting.ledger.items.filter((i) => i.type === "decision" && i.status === "final").length;
  const tasks = meeting.ledger.items.filter((i) => i.type === "task").length;

  async function publish() {
    setBusy(true);
    setError(null);
    try {
      setMeeting(await api.publish(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <p className="faint mono">
        {meeting.date} · chủ trì: {chair || "—"} · {meeting.ledger.generated_by}
      </p>
      <h1>{meeting.title ?? meeting.id}</h1>

      <div className="stats">
        <div className="stat"><b>{finals}</b><span>quyết định đã chốt</span></div>
        <div className="stat"><b>{tasks}</b><span>công việc</span></div>
        <div className="stat"><b>{pending}</b><span>chờ bạn xác nhận</span></div>
      </div>

      <div className="row" style={{ marginTop: 20 }}>
        <button className="btn btn-primary" onClick={publish} disabled={busy || meeting.published || pending > 0}>
          {meeting.published ? "Đã xuất bản" : pending > 0 ? `Còn ${pending} mục cần duyệt` : "Duyệt & xuất bản"}
        </button>
        <a className="btn" href={api.exportUrl(id, "md")}>Biên bản .md</a>
        <a className="btn" href={api.exportUrl(id, "csv")}>Task .csv</a>
        <a className="btn" href={api.exportUrl(id, "json")}>Ledger .json</a>
      </div>
      {error && <p className="alert" role="alert" style={{ marginTop: 12 }}>{error}</p>}

      {grouped.map((s) => (
        <section key={s.key} className="section" aria-labelledby={`h-${s.key}`}>
          <div className="section-head">
            <h2 id={`h-${s.key}`}>{s.title}</h2>
            <span className="count">{s.items.length}</span>
          </div>
          <p className="faint" style={{ marginTop: -8 }}>{s.hint}</p>
          {s.items.map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              approved={approved.has(item.id)}
              busy={busy}
              onReview={(changes) => review(item.id, changes)}
            />
          ))}
        </section>
      ))}

      <section className="section" aria-labelledby="h-transcript">
        <div className="section-head">
          <h2 id="h-transcript">Transcript</h2>
          <span className="count">{meeting.utterances.length} câu</span>
        </div>
        <div className="card transcript">
          {meeting.utterances.map((u) => (
            <div key={u.id} id={u.id} className="utt">
              <span className="mono faint">{formatTs(u.ts)}</span>
              <span>
                <span className="who">{u.speaker}:</span> {u.text}
              </span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function formatTs(sec: number) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return h ? `${String(h).padStart(2, "0")}:${mm}:${ss}` : `${mm}:${ss}`;
}
