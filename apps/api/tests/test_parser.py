import datetime as dt

import pytest

from chot.adapters.parsing import parse_transcript
from chot.adapters.parsing.transcript_txt import TranscriptParseError


def test_parses_header_and_utterances(m01):
    assert m01.meeting_id == "m01"
    assert m01.date == dt.date(2026, 10, 5)
    assert m01.chairs == {"Hùng"}
    assert len(m01.utterances) == 26
    u = m01.utt("u019")
    assert u.speaker == "Hùng" and u.ts_label == "14:20"
    assert "chốt" in u.text


def test_continuation_line_is_appended():
    tr = parse_transcript("[00:01] A: Xin chào\nmọi người nhé\n[00:05] B: Chào")
    assert tr.utterances[0].text == "Xin chào mọi người nhé"
    assert len(tr.utterances) == 2


def test_unknown_speaker_added_without_authority():
    tr = parse_transcript("# participants: A (chủ trì)\n[00:01] B: Tôi chốt luôn.")
    names = {p.name: p for p in tr.participants}
    assert "B" in names and not names["B"].is_chair


def test_absent_people_are_not_participants(data_dir):
    from chot.adapters.parsing import parse_transcript_file

    tr = parse_transcript_file(data_dir / "raw" / "m04.txt")
    assert [p.name for p in tr.absent] == ["Phong"]
    assert "Phong" not in tr.names


def test_garbage_raises():
    with pytest.raises(TranscriptParseError):
        parse_transcript("đây không phải transcript")
