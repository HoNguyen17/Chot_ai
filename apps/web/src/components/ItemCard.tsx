"use client";

import { useState } from "react";
import { EVENT_VERB, TYPE_LABEL } from "@/lib/labels";
import type { Item } from "@/lib/types";
import { Quote, type OnQuote } from "./Quote";
import { StatusBadge } from "./StatusBadge";

function formatDate(iso: string) {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

const ANSWERED = new Set(["confirmed", "rejected", "deferred"]);

/** Một dòng "Kết quả": thu gọn mặc định, mở ra có bằng chứng, "Vì sao", sửa / hoàn tác. */
export function ItemCard({
  item,
  locked,
  busy,
  onQuote,
  onEdit,
  onUndo,
  onReject,
}: {
  item: Item;
  locked: boolean;
  busy: boolean;
  onQuote: OnQuote;
  onEdit: (content: string) => void;
  onUndo: () => void;
  onReject: () => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const deadline = item.deadline ? formatDate(item.deadline) : item.deadline_text;
  const answered = ANSWERED.has(item.review_state ?? "");

  return (
    <details className="result" data-status={item.status}>
      <summary>
        <span className="mono">{item.id}</span>
        <StatusBadge item={item} />
        <span className="result-content">{item.content}</span>
        {item.decided_by && <span className="faint">· chốt bởi {item.decided_by}</span>}
        {item.type === "task" && <span className="faint">· {item.owner ?? "chưa rõ ai làm"}</span>}
        {item.review_state === "deferred" && <span className="faint">· để họp sau</span>}
      </summary>

      <div className="result-body">
        <div className="meta">
          <span>{TYPE_LABEL[item.type]}</span>
          {deadline && (
            <span>
              Hạn: <b>{deadline}</b>
            </span>
          )}
        </div>

        {item.flags.length > 0 && (
          <ul className="flags">
            {item.flags.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        )}

        <div className="quotes" aria-label="Bằng chứng">
          {item.evidence.map((e, n) => (
            <Quote key={n} ev={e} onQuote={onQuote} />
          ))}
        </div>

        {item.timeline.length > 0 && (
          <div className="why">
            <p className="faint">Vì sao</p>
            <ol>
              {item.timeline.map((t) => (
                <li key={t.utt + t.kind}>
                  <button type="button" className="quote" onClick={() => onQuote(t.utt)}>
                    <span className="mono faint">{t.ts ?? t.utt}</span>
                    <span>
                      <b>{t.speaker}</b> {EVENT_VERB[t.kind] ?? t.kind}
                      {t.key && <> {t.key}</>}: <span className="q">{t.quote}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </div>
        )}

        {!locked && draft === null && (
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn btn-sm" disabled={busy} onClick={() => setDraft(item.content)}>
              Sửa
            </button>
            {answered ? (
              <button className="btn btn-sm" disabled={busy} onClick={onUndo}>
                Hoàn tác câu trả lời
              </button>
            ) : (
              item.status !== "rejected" && (
                <button className="btn btn-sm" disabled={busy} onClick={onReject}>
                  Không đúng — bác bỏ
                </button>
              )
            )}
          </div>
        )}
        {draft !== null && (
          <form
            className="row"
            style={{ marginTop: 12 }}
            onSubmit={(e) => {
              e.preventDefault();
              if (draft.trim()) onEdit(draft.trim());
              setDraft(null);
            }}
          >
            <input type="text" aria-label="Nội dung" value={draft} onChange={(e) => setDraft(e.target.value)} />
            <button className="btn btn-sm btn-primary" disabled={busy}>
              Lưu
            </button>
            <button type="button" className="btn btn-sm" onClick={() => setDraft(null)}>
              Huỷ
            </button>
          </form>
        )}
      </div>
    </details>
  );
}
