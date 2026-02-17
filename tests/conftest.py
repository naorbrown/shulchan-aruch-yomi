"""Pytest fixtures for Shulchan Aruch Yomi tests."""

import pytest

from src.models import DailyPair, Halacha, Volume


@pytest.fixture
def sample_volume_oc() -> Volume:
    """Sample Orach Chaim volume."""
    return Volume(
        volume="Orach Chaim",
        volume_he="אורח חיים",
        ref_base="Shulchan_Arukh,_Orach_Chayim",
        max_siman=697,
    )


@pytest.fixture
def sample_volume_yd() -> Volume:
    """Sample Yoreh De'ah volume."""
    return Volume(
        volume="Yoreh De'ah",
        volume_he="יורה דעה",
        ref_base="Shulchan_Arukh,_Yoreh_De'ah",
        max_siman=403,
    )


@pytest.fixture
def sample_halacha_1(sample_volume_oc: Volume) -> Halacha:
    """Sample halacha from Orach Chaim."""
    return Halacha(
        volume=sample_volume_oc,
        siman=1,
        seif=1,
        hebrew_text="יתגבר כארי לעמוד בבוקר לעבודת בוראו שיהא הוא מעורר השחר.",
        sefaria_url="https://www.sefaria.org/Shulchan_Arukh,_Orach_Chayim.1.1",
    )


@pytest.fixture
def sample_halacha_2(sample_volume_yd: Volume) -> Halacha:
    """Sample halacha from Yoreh De'ah."""
    return Halacha(
        volume=sample_volume_yd,
        siman=1,
        seif=1,
        hebrew_text="אין שוחטין לא בתוך הנהר ולא על גבי כלים ולא לתוך כלים.",
        sefaria_url="https://www.sefaria.org/Shulchan_Arukh,_Yoreh_De'ah.1.1",
    )


@pytest.fixture
def sample_pair(sample_halacha_1: Halacha, sample_halacha_2: Halacha) -> DailyPair:
    """Sample daily pair."""
    return DailyPair(
        first=sample_halacha_1,
        second=sample_halacha_2,
        date_seed="2026-02-16",
    )
