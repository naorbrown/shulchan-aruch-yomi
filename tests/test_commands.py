"""Tests for command handlers."""

from datetime import date
from unittest.mock import MagicMock

from src.commands import (
    get_error_message,
    get_info_message,
    get_start_messages,
    get_today_messages,
)
from src.models import DailyPair, Halacha, Volume


def _make_pair() -> DailyPair:
    oc = Volume(
        volume="Orach Chaim",
        volume_he="אורח חיים",
        ref_base="Shulchan_Arukh,_Orach_Chaim",
        max_siman=697,
    )
    yd = Volume(
        volume="Yoreh De'ah",
        volume_he="יורה דעה",
        ref_base="Shulchan_Arukh,_Yoreh_De'ah",
        max_siman=403,
    )
    h1 = Halacha(
        volume=oc,
        siman=1,
        seif=1,
        hebrew_text="יתגבר כארי לעמוד בבוקר לעבודת בוראו שיהא הוא מעורר השחר.",
        sefaria_url="https://www.sefaria.org/Shulchan_Arukh,_Orach_Chaim.1.1",
    )
    h2 = Halacha(
        volume=yd,
        siman=1,
        seif=1,
        hebrew_text="אין שוחטין לא בתוך הנהר ולא על גבי כלים.",
        sefaria_url="https://www.sefaria.org/Shulchan_Arukh,_Yoreh_De'ah.1.1",
    )
    return DailyPair(first=h1, second=h2, date_seed="2026-02-16")


def test_get_start_messages():
    selector = MagicMock()
    selector.get_cached_messages.return_value = None
    selector.get_daily_pair.return_value = _make_pair()

    msgs = get_start_messages(selector, date(2026, 2, 16))
    assert len(msgs) >= 2
    # First is welcome
    assert "שולחן ערוך יומי" in msgs[0]
    assert "ברוכים הבאים" in msgs[0]


def test_get_start_messages_cached():
    selector = MagicMock()
    selector.get_cached_messages.return_value = ["cached1", "cached2"]

    msgs = get_start_messages(selector, date(2026, 2, 16))
    assert msgs == ["cached1", "cached2"]


def test_get_today_messages():
    selector = MagicMock()
    selector.get_cached_messages.return_value = None
    selector.get_daily_pair.return_value = _make_pair()

    msgs = get_today_messages(selector, date(2026, 2, 16))
    assert len(msgs) >= 1
    # No welcome message
    assert "ברוכים הבאים" not in msgs[0]


def test_get_today_messages_cached():
    selector = MagicMock()
    selector.get_cached_messages.return_value = ["welcome", "content1", "content2"]

    msgs = get_today_messages(selector, date(2026, 2, 16))
    assert msgs == ["content1", "content2"]


def test_get_info_message():
    msg = get_info_message()
    assert "שולחן ערוך" in msg


def test_get_error_message():
    msg = get_error_message()
    assert "לא הצלחתי" in msg


def test_get_start_messages_api_failure():
    selector = MagicMock()
    selector.get_cached_messages.return_value = None
    selector.get_daily_pair.return_value = None

    msgs = get_start_messages(selector, date(2026, 2, 16))
    assert len(msgs) >= 2
    assert "לא הצלחתי" in msgs[-1]
