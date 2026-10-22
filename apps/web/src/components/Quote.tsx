import type { Evidence } from "@/lib/types";

export type OnQuote = (utt: string) => void;

/** Một trích dẫn bấm được → mở transcript tại đúng câu. Bằng chứng của người duyệt thì chỉ là chữ. */
export function Quote({ ev, onQuote }: { ev: Evidence; onQuote: OnQuote }) {
  if (!ev.utt) {
    return (
      <span className="quote quote-reviewer">
        {ev.by ?? "Người duyệt"}: {ev.note}
      </span>
    );
  }
  const utt = ev.utt;
  return (
    <button type="button" className="quote" onClick={() => onQuote(utt)}>
      <span className="mono faint">{ev.ts ?? utt}</span>
      <span>
        {ev.speaker && <b>{ev.speaker}: </b>}
        <span className="q">{ev.quote}</span>
      </span>
    </button>
  );
}
