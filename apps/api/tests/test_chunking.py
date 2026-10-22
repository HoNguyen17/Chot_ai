"""Chia đoạn họp dài (SPEC M3 §3.2): mọi câu thuộc đúng 1 đoạn, ngữ cảnh chỉ là câu ngay trước."""

import pytest

from chot.domain.chunking import chunk
from chot.domain.models import Utterance


def utts(n: int) -> list[Utterance]:
    return [
        Utterance(id=f"u{i:03d}", index=i, ts=i * 10, speaker="A", text="x")
        for i in range(1, n + 1)
    ]


@pytest.mark.parametrize("size", [50, 70, 100])
@pytest.mark.parametrize("n", [1, 49, 50, 70, 71, 101, 157, 200, 205])
def test_every_utterance_in_exactly_one_chunk(n, size):
    ids = [u.id for u in utts(n)]
    labels = [i for c in chunk(utts(n), size=size, context=10) for i in c.label_ids]
    assert labels == ids


@pytest.mark.parametrize("n", [71, 157, 205])
def test_context_is_up_to_n_utterances_right_before_chunk(n):
    ids = [u.id for u in utts(n)]
    chunks = chunk(utts(n), size=70, context=10)
    assert chunks[0].context_ids == []
    for c in chunks[1:]:
        start = ids.index(c.label_ids[0])
        assert c.context_ids == ids[max(0, start - 10) : start]


def test_short_transcript_is_one_chunk_without_context():
    chunks = chunk(utts(70), size=70, context=10)
    assert len(chunks) == 1 and chunks[0].context_ids == []
    assert len(chunk(utts(71), size=70, context=10)) == 2


def test_l4_trap_u071_starts_second_chunk_with_u070_as_context():
    second = chunk(utts(200), size=70, context=10)[1]
    assert second.label_ids[0] == "u071"
    assert second.context_ids[-1] == "u070"


@pytest.mark.parametrize(("size", "context"), [(0, 10), (70, -1)])
def test_invalid_config_rejected(size, context):
    with pytest.raises(ValueError):
        chunk(utts(5), size=size, context=context)
