from pathlib import Path

import pytest

from chot.adapters.parsing import parse_transcript, parse_transcript_file

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def data_dir() -> Path:
    return DATA


@pytest.fixture
def m01():
    return parse_transcript_file(DATA / "raw" / "m01.txt")


@pytest.fixture
def mini():
    """Cuộc họp tí hon dùng cho unit test luật."""
    return parse_transcript(
        "\n".join(
            [
                "# meeting: t1",
                "# date: 2026-10-05",
                "# participants: Sếp (CEO, chủ trì); An (Dev); Bình (QA)",
                "[00:10] An: Em đề xuất dùng A.",
                "[00:20] Bình: A chậm lắm, em đề xuất B.",
                "[00:30] Sếp: Tạm thời đi B nhé.",
                "[00:40] An: Dạ.",
                "[00:50] Sếp: Chốt dùng B.",
                "[01:00] Sếp: An làm việc X, thứ Sáu nhé.",
                "[01:10] An: Dạ vâng.",
                "[01:20] Sếp: Bình làm việc Y nhé.",
                "[01:30] Bình: Dạ, để em xem lại.",
                "[01:40] Bình: Em sẽ viết tài liệu Z cuối tuần này.",
            ]
        )
    )
