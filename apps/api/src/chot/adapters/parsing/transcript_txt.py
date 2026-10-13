"""Parser cho định dạng transcript .txt của Chốt (xem docs/DATA_DESIGN.md#transcript).

    # meeting: m01
    # title: Weekly sync
    # date: 2026-10-05
    # participants: Hùng (CEO, chủ trì); Minh (PM)
    # absent: Phong (Giám đốc)
    [00:01:05] Minh: Em đề xuất VNPay...

Dòng không có timestamp được nối vào câu nói trước đó. Định dạng .vtt/.srt: thêm parser mới
cùng thư mục, trả về cùng kiểu Transcript.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from pathlib import Path

from chot.domain.models import Participant, Transcript, Utterance

_HEADER_RE = re.compile(r"^#\s*(\w+)\s*:\s*(.*)$")
_LINE_RE = re.compile(
    r"^\[(?P<ts>(?:\d{1,2}:)?\d{1,2}:\d{2})\]\s*(?P<speaker>[^:\]]{1,60}?)\s*:\s*(?P<text>.+)$"
)
_PERSON_RE = re.compile(r"^\s*(?P<name>[^()]+?)\s*(?:\((?P<meta>[^)]*)\))?\s*$")
_CHAIR_MARKERS = {"chủ trì", "chair", "host"}


class TranscriptParseError(ValueError):
    pass


def _seconds(ts: str) -> int:
    parts = [int(p) for p in ts.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def parse_people(raw: str) -> list[Participant]:
    people = []
    for chunk in filter(None, (c.strip() for c in raw.split(";"))):
        m = _PERSON_RE.match(chunk)
        if not m:
            continue
        meta = [x.strip() for x in (m.group("meta") or "").split(",") if x.strip()]
        is_chair = any(x.lower() in _CHAIR_MARKERS for x in meta)
        roles = [x for x in meta if x.lower() not in _CHAIR_MARKERS]
        people.append(
            Participant(
                name=m.group("name").strip(), role=roles[0] if roles else None, is_chair=is_chair
            )
        )
    return people


def parse_transcript(text: str, meeting_id: str | None = None) -> Transcript:
    text = unicodedata.normalize("NFC", text)
    headers: dict[str, str] = {}
    utterances: list[Utterance] = []

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            m = _HEADER_RE.match(line)
            if m:
                headers[m.group(1).lower()] = m.group(2).strip()
            continue
        m = _LINE_RE.match(line)
        if m:
            idx = len(utterances) + 1
            utterances.append(
                Utterance(
                    id=f"u{idx:03d}",
                    index=idx,
                    ts=_seconds(m.group("ts")),
                    speaker=m.group("speaker").strip(),
                    text=m.group("text").strip(),
                )
            )
        elif utterances:
            last = utterances[-1]
            utterances[-1] = last.model_copy(update={"text": f"{last.text} {line}"})
        else:
            raise TranscriptParseError(f"Dòng {lineno} không đúng định dạng: {line[:60]!r}")

    if not utterances:
        raise TranscriptParseError("Transcript không có câu nói nào.")

    participants = parse_people(headers.get("participants", ""))
    known = {p.name for p in participants}
    for u in utterances:  # người nói không khai báo ở header vẫn được ghi nhận, không có quyền chốt
        if u.speaker not in known:
            participants.append(Participant(name=u.speaker))
            known.add(u.speaker)

    date = None
    if headers.get("date"):
        try:
            date = dt.date.fromisoformat(headers["date"])
        except ValueError:
            date = None

    return Transcript(
        meeting_id=meeting_id or headers.get("meeting") or "meeting",
        title=headers.get("title"),
        date=date,
        participants=participants,
        absent=parse_people(headers.get("absent", "")),
        utterances=utterances,
    )


def parse_transcript_file(path: str | Path) -> Transcript:
    p = Path(path)
    return parse_transcript(p.read_text(encoding="utf-8"), meeting_id=None)
