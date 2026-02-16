"""Tests for message formatting."""

from datetime import date

from src.formatter import (
    format_daily_message,
    format_error_message,
    format_halacha_messages,
    format_info_message,
    format_welcome_message,
    split_text,
)


def test_split_text_short():
    assert split_text("short text", 100) == ["short text"]


def test_split_text_at_boundary():
    text = "hello world foo bar"
    chunks = split_text(text, 12)
    assert chunks == ["hello world", "foo bar"]


def test_split_text_no_space():
    text = "a" * 20
    chunks = split_text(text, 10)
    assert chunks == ["a" * 10, "a" * 10]


def test_format_halacha_messages(sample_halacha_1):
    msgs = format_halacha_messages(sample_halacha_1, 1, "16/02/2026")
    assert len(msgs) >= 1
    assert "שולחן ערוך יומי" in msgs[0]
    assert "16/02/2026" in msgs[0]
    assert "אורח חיים" in msgs[0]
    assert "סימן 1" in msgs[0]
    assert "סעיף 1" in msgs[0]
    assert "ספריא" in msgs[-1]


def test_format_halacha_messages_no_date(sample_halacha_1):
    msgs = format_halacha_messages(sample_halacha_1, 2, "")
    assert len(msgs) >= 1
    assert "שולחן ערוך יומי" not in msgs[0]


def test_format_daily_message(sample_pair):
    msgs = format_daily_message(sample_pair, date(2026, 2, 16))
    assert len(msgs) >= 2
    # First message has date header
    assert "16/02/2026" in msgs[0]
    # Both volumes represented
    combined = " ".join(msgs)
    assert "אורח חיים" in combined
    assert "יורה דעה" in combined


def test_format_welcome_message():
    msg = format_welcome_message()
    assert "שולחן ערוך יומי" in msg
    assert "/unsubscribe" in msg


def test_format_info_message():
    msg = format_info_message()
    assert "שולחן ערוך" in msg
    assert "/today" in msg
    assert "/subscribe" in msg
    assert "sefaria.org" in msg


def test_format_error_message():
    msg = format_error_message()
    assert "לא הצלחתי" in msg


def test_message_length(sample_pair):
    msgs = format_daily_message(sample_pair, date(2026, 2, 16))
    for msg in msgs:
        assert len(msg) <= 4096
