"use client";

import { useState } from "react";
import { TYPE_LABEL } from "@/lib/labels";
import type { Item, Question, ReviewAction } from "@/lib/types";
import { Quote, type OnQuote } from "./Quote";

export type AnswerBody = { action: ReviewAction; owner?: string; deadline?: string; thread?: string };

/** Một thẻ trong "Cần bạn trả lời": câu hỏi sinh từ mã lý do (API), trả lời bằng nút — không chọn trạng thái. */
export function QuestionCard({
  q,
  item,
  people,
  threads,
  busy,
  onAnswer,
  onQuote,
}: {
  q: Question;
  item: Item;
  people: string[];
  threads: { id: string; title: string }[];
  busy: boolean;
  onAnswer: (body: AnswerBody) => void;
  onQuote: OnQuote;
}) {
  const needOwner = q.codes.includes("OWNER_MISSING");
  const needDate = q.codes.includes("DEADLINE_VAGUE");
  const needThread = q.codes.includes("THREAD_UNMAPPED");
  const [owner, setOwner] = useState(item.owner ?? "");
  const [deadline, setDeadline] = useState(item.deadline ?? "");
  const [thread, setThread] = useState("");
  const ready = (!needOwner || owner) && (!needDate || deadline) && (!needThread || thread);
  const quotes = item.evidence.filter((e) => e.kind === "transcript").slice(0, 2);
  const topic = threads.find((t) => t.id === item.thread)?.title;

  function confirm() {
    onAnswer({
      action: "confirm",
      owner: needOwner ? owner : undefined,
      deadline: needDate ? deadline : undefined,
      thread: needThread ? thread : undefined,
    });
  }

  return (
    <article className="q-card" aria-label={`Câu hỏi về ${item.id}`}>
      <p className="q-head">
        <b>{TYPE_LABEL[item.type]}</b>
        {topic && <> · {topic}</>} · <span className="mono faint">{item.id}</span>
      </p>
      <p className="item-content">{item.content}</p>
      {q.texts.map((t) => (
        <p key={t} className="q-text">
          {t}
        </p>
      ))}
      {q.codes.includes("DURABLE_KNOWLEDGE") && (
        <p className="faint">Xác nhận → lưu vào Kho tri thức của nhóm. Bác bỏ → chỉ giữ trong buổi này.</p>
      )}

      <div className="quotes">
        {quotes.map((e) => (
          <Quote key={e.utt} ev={e} onQuote={onQuote} />
        ))}
      </div>

      {needOwner && (
        <div className="row" role="group" aria-label="Chọn người làm">
          {people.map((p) => (
            <button
              key={p}
              type="button"
              className="chip"
              aria-pressed={owner === p}
              onClick={() => setOwner(p)}
            >
              {p}
            </button>
          ))}
        </div>
      )}
      {needDate && (
        <label className="row faint">
          Hạn chót
          <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        </label>
      )}
      {needThread && (
        <label className="row faint">
          Chủ đề
          <select value={thread} onChange={(e) => setThread(e.target.value)}>
            <option value="">Chọn…</option>
            {threads.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </label>
      )}

      <div className="row q-actions">
        <button className="btn btn-yes" disabled={busy || !ready} onClick={confirm}>
          Xác nhận
        </button>
        <button className="btn btn-no" disabled={busy} onClick={() => onAnswer({ action: "reject" })}>
          Bác bỏ
        </button>
        <button className="link" disabled={busy} onClick={() => onAnswer({ action: "defer" })}>
          để họp sau
        </button>
      </div>
    </article>
  );
}
