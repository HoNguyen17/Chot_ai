"""Ghép transcript m01–m25 thành cuộc họp dài (L1–L3) kèm gold / đáp án / sự kiện oracle đã map lại.

  python -m chot.eval.stitch            # đọc data/long/plans/L*.json, ghi data/long/{raw,gold,...}

Kế hoạch `data/long/plans/L{n}.json`:
  {"id": "L1", "title": "...", "date": "2026-10-05",
   "participants": ["Hùng (CEO, chủ trì)", ...], "absent": ["Phong (Giám đốc)"],
   "roster": {"m01": {"Hùng": "Hùng", ...}},                 # tên nguồn → tên đích, theo từng nguồn
   "blocks": [{"source": "m01", "from": "u001", "to": "u014"}, ...]}   # theo thứ tự xuất hiện

Các khối của cùng một nguồn là cắt rời rồi quay lại sau: luật trạng thái chạy trên cả cuộc họp.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

from chot.adapters.parsing import parse_transcript_file
from chot.domain.dates import resolve_deadline
from chot.domain.models import Transcript
from chot.domain.text import is_backchannel, normalize

GAP_SECONDS = 25  # khoảng lặng giữa hai khối
_TEXT_KEYS = {"content", "decided_by", "owner", "note", "speaker", "quote", "title", "key"}
_ACCEPT_RE = re.compile(r"^(dạ|vâng|ok|oke|được|rồi)\b[^.!?]{0,25}\b(anh|chị|em)\b", re.I)
_ABSOLUTE_RE = re.compile(r"\d{1,2}/\d{1,2}")


def _name_sub(mapping: dict[str, str]):
    if not mapping:
        return lambda s: s
    alt = "|".join(map(re.escape, sorted(mapping, key=len, reverse=True)))
    pat = re.compile(rf"(?<!\w)({alt})(?!\w)")
    return lambda s: pat.sub(lambda m: mapping[m.group(1)], s)


def _fmt_ts(sec: int) -> str:
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def _is_unsafe_start(text: str) -> bool:
    """Câu đầu khối không được là backchannel / lời nhận việc: luật dựa vào câu kề nhau."""
    return is_backchannel(text) or bool(_ACCEPT_RE.match(text))


class Stitched:
    """Kết quả ghép: transcript mới + bảng map utt/tên/thread để chuyển gold, đáp án, sự kiện."""

    def __init__(self, plan: dict, data_dir: Path, oracle_dir: Path):
        self.plan, self.data_dir, self.oracle_dir = plan, data_dir, oracle_dir
        self.sources = list(dict.fromkeys(b["source"] for b in plan["blocks"]))
        self.sub = {s: _name_sub(plan["roster"][s]) for s in self.sources}
        self.date = dt.date.fromisoformat(plan["date"])
        self.umap: dict[tuple[str, str], str] = {}
        self.lines: list[str] = []
        self._build_transcript()
        self.thread_name = self._thread_names()

    # ---- transcript -------------------------------------------------------------------------
    def _build_transcript(self) -> None:
        src: dict[str, Transcript] = {
            s: parse_transcript_file(self.data_dir / "raw" / f"{s}.txt") for s in self.sources
        }
        seen: set[tuple[str, str]] = set()
        t, n = 10, 0
        for bi, b in enumerate(self.plan["blocks"]):
            tr = src[b["source"]]
            lo, hi = tr.order(b["from"]), tr.order(b["to"])
            if not 0 < lo <= hi < 10**9:
                raise ValueError(f"Khối sai khoảng: {b}")
            block = tr.utterances[lo - 1 : hi]
            if bi and _is_unsafe_start(block[0].text):
                raise ValueError(
                    f"Khối {b} bắt đầu bằng câu phụ thuộc câu trước: {block[0].text!r}"
                )
            for k, u in enumerate(block):
                if (b["source"], u.id) in seen:
                    raise ValueError(f"Câu {b['source']}.{u.id} nằm ở hai khối")
                seen.add((b["source"], u.id))
                if bi or k:
                    t += GAP_SECONDS if not k else max(1, u.ts - block[k - 1].ts)
                n += 1
                self.umap[(b["source"], u.id)] = f"u{n:03d}"
                text = self.sub[b["source"]](u.text)
                speaker = self.sub[b["source"]](u.speaker)
                self.lines.append(f"[{_fmt_ts(t)}] {speaker}: {text}")
        self.count = n

    def transcript_text(self) -> str:
        p = self.plan
        head = [f"# meeting: {p['id']}", f"# title: {p['title']}", f"# date: {p['date']}"]
        head.append("# participants: " + "; ".join(p["participants"]))
        if p.get("absent"):
            head.append("# absent: " + "; ".join(p["absent"]))
        return "\n".join(head + self.lines) + "\n"

    # ---- tài liệu đi kèm --------------------------------------------------------------------
    def _load(self, folder: Path, source: str) -> dict:
        return json.loads((folder / f"{source}.json").read_text(encoding="utf-8"))

    def _thread_names(self) -> dict[tuple[str, str], str]:
        """Thread trùng tên giữa hai nguồn → thêm tiền tố nguồn."""
        used: dict[str, set[str]] = {}
        for s in self.sources:
            ids = {
                i["thread"]
                for i in self._load(self.data_dir / "gold", s)["items"]
                if i.get("thread")
            }
            ids |= {t["id"] for t in self._load(self.oracle_dir, s)["threads"]}
            for tid in ids:
                used.setdefault(tid, set()).add(s)
        return {
            (s, tid): f"{s}-{tid}" if len(srcs) > 1 else tid
            for tid, srcs in used.items()
            for s in srcs
        }

    def _text(self, source: str, value):
        return self.sub[source](value) if isinstance(value, str) else value

    def _utt(self, source: str, old: str) -> str:
        try:
            return self.umap[(source, old)]
        except KeyError:
            raise ValueError(
                f"{source}.{old} không nằm trong khối nào của {self.plan['id']}"
            ) from None

    def _item(self, source: str, it: dict) -> dict:
        out = {k: self._text(source, v) if k in _TEXT_KEYS else v for k, v in it.items()}
        out["id"] = f"{source}.{it['id']}"
        out["evidence"] = [self._utt(source, e) for e in it["evidence"]]
        if it.get("thread"):
            out["thread"] = self.thread_name[(source, it["thread"])]
        phrase = it.get("deadline_text")
        if phrase and not _ABSOLUTE_RE.search(normalize(phrase)):  # hạn tương đối → tính lại
            new = resolve_deadline(phrase, self.date)
            out["deadline"] = new.isoformat() if new else None
            if new or it.get("deadline"):
                out["needs_review"] = True
        return out

    def items(self, folder: Path) -> list[dict]:
        merged = [self._item(s, it) for s in self.sources for it in self._load(folder, s)["items"]]
        return sorted(merged, key=lambda i: min(i["evidence"]))

    def gold(self, folder: Path) -> dict:
        labeler = self._load(folder, self.sources[0]).get("labeler")
        return {"meeting_id": self.plan["id"], "labeler": labeler, "items": self.items(folder)}

    def events(self) -> dict:
        threads, events = [], []
        for s in self.sources:
            doc = self._load(self.oracle_dir, s)
            threads += [
                {**t, "id": self.thread_name[(s, t["id"])], "title": self._text(s, t.get("title"))}
                for t in doc["threads"]
            ]
            for e in doc["events"]:
                ne = {k: self._text(s, v) if k in _TEXT_KEYS else v for k, v in e.items()}
                ne["utt"] = self._utt(s, e["utt"])
                ne["thread"] = self.thread_name[(s, e["thread"])]
                events.append(ne)
        events.sort(key=lambda e: e["utt"])
        return {"threads": threads, "events": events}


def stitch(plan_path: Path, data_dir: Path, oracle_dir: Path, out_dir: Path) -> Stitched:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    st = Stitched(plan, data_dir, oracle_dir)
    pid = plan["id"]
    docs = {
        "gold": st.gold(data_dir / "gold"),
        "answer_key": st.gold(data_dir / "answer_key"),
        "oracle_events": st.events(),
    }
    for folder, doc in docs.items():
        (out_dir / folder).mkdir(parents=True, exist_ok=True)
        (out_dir / folder / f"{pid}.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    (out_dir / "raw" / f"{pid}.txt").write_text(st.transcript_text(), encoding="utf-8")
    return st


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ghép m01–m25 thành cuộc họp dài")
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--long", type=Path, default=Path("data/long"))
    ap.add_argument("--oracle", type=Path, default=Path("apps/api/tests/fixtures/oracle_events"))
    ap.add_argument("plans", nargs="*", type=Path, help="mặc định: <long>/plans/L*.json")
    args = ap.parse_args(argv)
    for p in args.plans or sorted((args.long / "plans").glob("L*.json")):
        st = stitch(p, args.data, args.oracle, args.long)
        items = st.gold(args.data / "gold")["items"]
        review = sum(1 for i in items if i.get("needs_review"))
        print(f"{st.plan['id']}: {st.count} câu, {len(items)} mục gold, {review} needs_review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
