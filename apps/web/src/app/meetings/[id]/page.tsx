"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ItemCard } from "@/components/ItemCard";
import { QuestionCard, type AnswerBody } from "@/components/QuestionCard";
import { TranscriptPane, type Focus } from "@/components/TranscriptPane";
import { api } from "@/lib/api";
import { RESULT_GROUPS, groupKey } from "@/lib/labels";
import type { Meeting } from "@/lib/types";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [focus, setFocus] = useState<Focus>(null);
  const [tab, setTab] = useState<"review" | "transcript">("review"); // chỉ dùng < 1024px

  useEffect(() => {
    api.getMeeting(id).then(setMeeting).catch((e) => setError(String(e.message ?? e)));
  }, [id]);

  /** Mọi thao tác ghi: API trả lại cả cuộc họp → thay state. */
  async function run(call: () => Promise<Meeting>) {
    setBusy(true);
    setError(null);
    try {
      setMeeting(await call());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function showQuote(utt: string) {
    setFocus({ utt });
    setTab("transcript");
  }

  const groups = useMemo(() => {
    if (!meeting) return [];
    const asked = new Set(meeting.questions.map((q) => q.item_id));
    const results = meeting.ledger.items.filter((i) => !asked.has(i.id));
    return RESULT_GROUPS.map((g) => ({ ...g, items: results.filter((i) => groupKey(i.type, i.status) === g.key) })).filter(
      (g) => g.items.length > 0,
    );
  }, [meeting]);

  if (error && !meeting) return <p className="alert">{error}</p>;
  if (!meeting) return <p className="muted">Đang tải…</p>;

  const items = meeting.ledger.items;
  const byId = new Map(items.map((i) => [i.id, i]));
  const people = [...meeting.participants, ...meeting.absent].map((p) => p.name);
  const chair = meeting.participants.filter((p) => p.is_chair).map((p) => p.name).join(", ");
  const n = meeting.questions.length;
  const count = (f: (i: (typeof items)[number]) => boolean) => items.filter(f).length;

  return (
    <div className="review-grid" data-tab={tab}>
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "review"} onClick={() => setTab("review")}>
          Duyệt
        </button>
        <button role="tab" aria-selected={tab === "transcript"} onClick={() => setTab("transcript")}>
          Transcript · {meeting.utterances.length} câu
        </button>
      </div>

      <div className="review-main">
        <p className="faint mono">
          {meeting.series_id && (
            <>
              <Link href={`/s/${meeting.series_id}`}>← Nhóm họp</Link> ·{" "}
            </>
          )}
          {meeting.date} · chủ trì: {chair || "—"} · {meeting.utterances.length} câu
        </p>
        <h1>{meeting.title ?? meeting.ledger.meeting_id}</h1>

        <div className="stats">
          <div className="stat"><b>{count((i) => i.type === "decision" && i.status === "final")}</b><span>đã chốt</span></div>
          <div className="stat"><b>{count((i) => i.type === "task" && i.status === "open")}</b><span>việc đã nhận</span></div>
          <div className="stat"><b>{n}</b><span>câu hỏi cho bạn</span></div>
          <div className="stat"><b>{count((i) => i.type === "knowledge")}</b><span>tri thức mới</span></div>
        </div>

        {error && <p className="alert" role="alert" style={{ marginTop: 12 }}>{error}</p>}

        {n > 0 && (
          <section className="section" aria-labelledby="h-ask">
            <div className="section-head">
              <h2 id="h-ask">Cần bạn trả lời</h2>
              <span className="count">{n}</span>
            </div>
            <div className="stack">
              {meeting.questions.map((q) => {
                const item = byId.get(q.item_id);
                return (
                  item && (
                    <QuestionCard
                      key={q.item_id}
                      q={q}
                      item={item}
                      people={people}
                      threads={meeting.ledger.threads}
                      busy={busy || meeting.published}
                      onAnswer={(body: AnswerBody) => run(() => api.answer(id, q.item_id, body))}
                      onQuote={showQuote}
                    />
                  )
                );
              })}
            </div>
          </section>
        )}

        <section className="section" aria-labelledby="h-results">
          <div className="section-head">
            <h2 id="h-results">Kết quả — tự chấp nhận</h2>
          </div>
          <p className="faint" style={{ marginTop: -8 }}>Bấm để mở. Vẫn sửa / hoàn tác được trước khi xuất bản.</p>
          {groups.map((g, k) => (
            <details key={g.key} className="group" open={k === 0}>
              <summary>
                {g.title} <span className="count">{g.items.length}</span>
              </summary>
              {g.items.map((item) => (
                <ItemCard
                  key={item.id}
                  item={item}
                  locked={meeting.published}
                  busy={busy}
                  onQuote={showQuote}
                  onEdit={(content) => run(() => api.reviewItem(id, item.id, { content }))}
                  onUndo={() => run(() => api.reviewItem(id, item.id, { approved: false }))}
                  onReject={() => run(() => api.answer(id, item.id, { action: "reject" }))}
                />
              ))}
            </details>
          ))}
        </section>

        <div className="publish-bar">
          <button
            className="btn btn-primary"
            onClick={() => run(() => api.publish(id))}
            disabled={busy || meeting.published || n > 0}
          >
            {meeting.published ? "✓ Đã xuất bản" : n > 0 ? `Còn ${n} câu hỏi` : "Xuất bản"}
          </button>
          <a className="btn btn-sm" href={api.exportUrl(id, "md")}>.md</a>
          <a className="btn btn-sm" href={api.exportUrl(id, "csv")}>.csv</a>
          <a className="btn btn-sm" href={api.exportUrl(id, "json")}>.json</a>
        </div>
      </div>

      <aside className="review-side">
        <TranscriptPane utterances={meeting.utterances} focus={focus} />
      </aside>
    </div>
  );
}
