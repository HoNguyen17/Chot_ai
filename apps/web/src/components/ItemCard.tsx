"use client";

import { STATUS_LABEL, TYPE_LABEL } from "@/lib/labels";
import type { Item, Status } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

const REVIEWABLE: Status[] = ["final", "needs_confirmation", "deferred", "open", "superseded", "rejected"];

function formatDate(iso: string) {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

export function ItemCard({
  item,
  approved,
  busy,
  onReview,
}: {
  item: Item;
  approved: boolean;
  busy: boolean;
  onReview: (changes: { status?: Status; approved?: boolean }) => void;
}) {
  const deadline = item.deadline ? formatDate(item.deadline) : item.deadline_text;
  return (
    <article className="card" data-status={item.status} aria-label={`${TYPE_LABEL[item.type]} ${item.id}`}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="row">
          <StatusBadge status={item.status} />
          <span className="type-label">
            {TYPE_LABEL[item.type]} · <span className="mono">{item.id}</span>
          </span>
        </div>
        {approved && <span className="faint">✓ đã duyệt</span>}
      </div>

      <p className="item-content">{item.content}</p>

      <div className="meta">
        {item.type === "task" && (
          <span>
            Phụ trách: <b>{item.owner ?? "chưa rõ"}</b>
          </span>
        )}
        {deadline && (
          <span>
            Hạn: <b>{deadline}</b>
          </span>
        )}
        {item.decided_by && (
          <span>
            {item.status === "final" ? "Chốt bởi" : "Đồng ý bởi"}: <b>{item.decided_by}</b>
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

      <ul className="evidence" aria-label="Bằng chứng">
        {item.evidence.map((e) => (
          <li key={e.utt + e.quote}>
            <a href={`#${e.utt}`}>
              <span className="mono faint">{e.ts ?? e.utt}</span>
              <span>
                {e.speaker && <b>{e.speaker}: </b>}
                <span className="q">{e.quote}</span>
              </span>
            </a>
          </li>
        ))}
      </ul>

      <div className="row" style={{ marginTop: 12 }}>
        {!approved && (
          <button className="btn btn-sm" disabled={busy} onClick={() => onReview({ approved: true })}>
            Duyệt
          </button>
        )}
        <label className="faint row" style={{ gap: 6 }}>
          Đổi trạng thái
          <select
            value={item.status}
            disabled={busy}
            onChange={(e) => onReview({ status: e.target.value as Status })}
          >
            {REVIEWABLE.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </label>
      </div>
    </article>
  );
}
