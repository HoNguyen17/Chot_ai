"use client";

import { useEffect, useRef } from "react";
import type { Utterance } from "@/lib/types";

/** Câu đang xem; object mới mỗi lần bấm → bấm lại cùng câu vẫn cuộn. */
export type Focus = { utt: string } | null;

/** Ngăn transcript: câu đang xem được cuộn tới và tô sáng. */
export function TranscriptPane({ utterances, focus }: { utterances: Utterance[]; focus: Focus }) {
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!focus) return;
    box.current
      ?.querySelector(`[data-utt="${CSS.escape(focus.utt)}"]`)
      ?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [focus]);

  return (
    <div ref={box} className="card transcript" aria-label="Transcript">
      {utterances.map((u) => (
        <div key={u.id} data-utt={u.id} className={`utt${u.id === focus?.utt ? " hl" : ""}`}>
          <span className="mono faint">{formatTs(u.ts)}</span>
          <span>
            <span className="who">{u.speaker}:</span> {u.text}
          </span>
        </div>
      ))}
    </div>
  );
}

function formatTs(sec: number) {
  const h = Math.floor(sec / 3600);
  const mm = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
  const ss = String(sec % 60).padStart(2, "0");
  return h ? `${String(h).padStart(2, "0")}:${mm}:${ss}` : `${mm}:${ss}`;
}
