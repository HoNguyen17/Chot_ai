import datetime as dt

import pytest

from chot.domain.dates import extract_deadline_phrase, resolve_deadline
from chot.domain.text import is_backchannel, is_hedged

MON = dt.date(2026, 10, 5)  # thứ Hai
FRI = dt.date(2026, 10, 9)  # thứ Sáu


@pytest.mark.parametrize("text", ["Dạ.", "Vâng ạ", "Dạ vâng.", "Ừ.", "Ừm...", "ờ", "dạ, dạ"])
def test_backchannel(text):
    assert is_backchannel(text)


@pytest.mark.parametrize("text", ["Dạ ok anh, thứ Năm em gửi.", "Ừ anh cũng thấy vậy. Tú sửa nhé."])
def test_not_backchannel(text):
    assert not is_backchannel(text)


@pytest.mark.parametrize(
    "text",
    [
        "Thôi tạm thời đi MoMo nhé",
        "Nếu mà khách duyệt thì làm",
        "Chị thích concept 2 hơn",
        "Dạ, để em xem lại ạ",
        "Tạm thời chị nghiêng về nhóm micro-KOL",
        "hay là quay lại VNPay cho chắc",
    ],
)
def test_hedged(text):
    assert is_hedged(text)


@pytest.mark.parametrize(
    "text",
    ["Vậy chốt nhé: launch tháng 11 dùng MoMo", "Chắc chắn làm B", "Giá combo 65 nghìn, chốt."],
)
def test_not_hedged(text):
    assert not is_hedged(text)


@pytest.mark.parametrize(
    "phrase,meeting,expected",
    [
        ("thứ Sáu", MON, dt.date(2026, 10, 9)),
        ("thứ Sáu này", MON, dt.date(2026, 10, 9)),
        ("thứ Hai", MON, dt.date(2026, 10, 12)),  # cùng thứ → tuần sau
        ("thứ Tư", FRI, dt.date(2026, 10, 14)),
        ("thứ Hai tuần sau", FRI, dt.date(2026, 10, 12)),
        ("cuối tuần này", MON, dt.date(2026, 10, 11)),
        ("cuối tuần sau", MON, dt.date(2026, 10, 18)),
        ("hôm nay", MON, MON),
        ("chiều nay", MON, MON),
        ("mai", MON, dt.date(2026, 10, 6)),
        ("15/11", MON, dt.date(2026, 11, 15)),
        ("tuần sau", MON, None),
    ],
)
def test_resolve_deadline(phrase, meeting, expected):
    assert resolve_deadline(phrase, meeting) == expected


def test_extract_phrase_from_sentence():
    assert extract_deadline_phrase("Lan theo vụ sandbox, thứ Sáu này báo lại anh") == "thứ sáu này"
    assert extract_deadline_phrase("Không có hạn gì cả") is None
