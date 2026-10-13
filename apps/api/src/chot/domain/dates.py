"""Chuẩn hoá hạn chót nói bằng tiếng Việt ("thứ Sáu", "cuối tuần này", "15/11") thành ngày.

Quy ước (xem docs/DATA_DESIGN.md#deadline):
- "thứ X" trơn       → lần gần nhất SAU ngày họp (cùng thứ → tuần sau).
- "thứ X này"         → thứ X của tuần hiện tại; nếu đã qua → tuần sau.
- "thứ X tuần sau"    → thứ X của tuần lịch kế tiếp (tuần bắt đầu thứ Hai).
- "cuối tuần (này)"   → Chủ nhật tuần hiện tại. "cuối tuần sau" → Chủ nhật tuần sau.
- "hôm nay" / "mai"   → ngày họp / ngày họp + 1.
- "tuần sau" trơn     → None (không đủ cụ thể; giữ deadline_text).
- "dd/mm[/yyyy]"      → ngày tương ứng; thiếu năm thì lấy năm của cuộc họp.
"""

from __future__ import annotations

import datetime as dt
import re

from chot.domain.text import normalize

_WEEKDAYS = {
    "thứ hai": 0, "thứ 2": 0,
    "thứ ba": 1, "thứ 3": 1,
    "thứ tư": 2, "thứ 4": 2,
    "thứ năm": 3, "thứ 5": 3,
    "thứ sáu": 4, "thứ 6": 4,
    "thứ bảy": 5, "thứ 7": 5,
    "chủ nhật": 6,
}  # fmt: skip

_WD_ALT = "|".join(sorted(map(re.escape, _WEEKDAYS), key=len, reverse=True))
_PATTERNS = [
    re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?:/(\d{4}))?(?!\d)"),
    re.compile(rf"({_WD_ALT})(\s+tuần\s+sau|\s+tuần\s+này|\s+này)?"),
    re.compile(r"cuối\s+tuần(\s+này|\s+sau)?"),
    re.compile(r"hôm\s+nay|trong\s+hôm\s+nay|chiều\s+nay|tối\s+nay"),
    re.compile(r"(?<!\w)(ngày\s+mai|mai)(?!\w)"),
    re.compile(r"tuần\s+sau"),
]


def extract_deadline_phrase(text: str) -> str | None:
    """Tìm cụm chỉ thời hạn đầu tiên trong câu (theo thứ tự ưu tiên)."""
    norm = normalize(text)
    for pat in _PATTERNS:
        m = pat.search(norm)
        if m:
            return m.group(0).strip()
    return None


def _monday(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())


def resolve_deadline(phrase: str | None, meeting_date: dt.date | None) -> dt.date | None:
    if not phrase or not meeting_date:
        return None
    p = normalize(phrase)

    m = _PATTERNS[0].search(p)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else meeting_date.year
        try:
            d = dt.date(year, month, day)
        except ValueError:
            return None
        if not m.group(3) and d < meeting_date - dt.timedelta(days=30):
            d = d.replace(year=year + 1)
        return d

    m = _PATTERNS[1].search(p)
    if m:
        target = _WEEKDAYS[m.group(1)]
        suffix = (m.group(2) or "").strip()
        monday = _monday(meeting_date)
        if "tuần sau" in suffix:
            return monday + dt.timedelta(days=7 + target)
        this_week = monday + dt.timedelta(days=target)
        if suffix in ("này", "tuần này"):
            return this_week if this_week >= meeting_date else this_week + dt.timedelta(days=7)
        return this_week if this_week > meeting_date else this_week + dt.timedelta(days=7)

    m = _PATTERNS[2].search(p)
    if m:
        sunday = _monday(meeting_date) + dt.timedelta(days=6)
        return sunday + dt.timedelta(days=7) if (m.group(1) or "").strip() == "sau" else sunday

    if _PATTERNS[3].search(p):
        return meeting_date
    if _PATTERNS[4].search(p):
        return meeting_date + dt.timedelta(days=1)
    return None  # "tuần sau" trơn hoặc không nhận ra
