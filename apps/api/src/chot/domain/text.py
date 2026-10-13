"""Chuẩn hoá văn bản tiếng Việt + nhận diện tín hiệu ngữ dụng (rào đón, backchannel)."""

from __future__ import annotations

import re
import unicodedata

_PUNCT_EDGES = " \t\n\r.,!?…\"'“”‘’:;-–—()[]"


def normalize(text: str) -> str:
    """NFC + lowercase + gộp khoảng trắng. Dùng cho so khớp trích dẫn."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(_PUNCT_EDGES)


# "dạ", "vâng", "ừ"... đứng một mình = đang nghe, KHÔNG phải đồng ý hay nhận việc.
_BACKCHANNEL_RE = re.compile(
    r"^(dạ|vâng|ừ|ừm|ờ|uhm|um|à)([\s,]+(dạ|vâng|ạ|anh|chị|em|ừ|ờ))*[\s.!…]*$"
)

# Tín hiệu rào đón: có những từ này thì đồng thuận chưa phải cam kết.
_HEDGE_PATTERNS = [
    r"tạm thời",
    r"\btạm\b",
    r"nếu mà",
    r"\bnếu\b",
    r"hay là",
    r"chắc là",
    r"có lẽ",
    r"\bthử\b",
    r"để (em|anh|chị|mình|tôi) xem",
    r"xem lại",
    r"tính sau",
    r"để sau",
    r"chưa chắc",
    r"nghiêng về",
    r"\bthích\b",
    r"hình như",
    r"\bchắc\b(?! chắn)",
    r"hỏi lại",
]
_HEDGE_RE = re.compile("|".join(_HEDGE_PATTERNS))


def is_backchannel(text: str) -> bool:
    return bool(_BACKCHANNEL_RE.match(normalize(text)))


def is_hedged(text: str) -> bool:
    return bool(_HEDGE_RE.search(normalize(text)))


def hedge_markers(text: str) -> list[str]:
    return [m.group(0) for m in _HEDGE_RE.finditer(normalize(text))]
