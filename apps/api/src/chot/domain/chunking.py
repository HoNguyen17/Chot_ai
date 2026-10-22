"""Chia transcript dài thành đoạn cho lượt 2 của extractor (SPEC M3 §3.2) — thuần, không I/O."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from chot.domain.models import Utterance


class Chunk(BaseModel):
    """`label_ids`: câu LLM gán nhãn. `context_ids`: câu ngay trước, CHỈ ĐỌC."""

    model_config = ConfigDict(frozen=True)

    label_ids: list[str]
    context_ids: list[str]


def chunk(utterances: list[Utterance], size: int, context: int) -> list[Chunk]:
    """Cắt cố định theo số câu; mỗi câu thuộc đúng 1 đoạn. Ngắn ≤ size → 1 đoạn (như M2)."""
    if size < 1 or context < 0:
        raise ValueError(f"CHUNK_SIZE phải ≥ 1 và CHUNK_CONTEXT ≥ 0 (nhận {size}, {context})")
    ids = [u.id for u in utterances]
    return [
        Chunk(label_ids=ids[i : i + size], context_ids=ids[max(0, i - context) : i])
        for i in range(0, len(ids), size)
    ]
