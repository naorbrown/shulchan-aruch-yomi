"""Tests for daily halacha selection."""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models import Halacha, Volume
from src.selector import HalachaSelector, _memory_cache, _message_cache


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear module-level caches before each test."""
    _memory_cache.clear()
    _message_cache.clear()
    yield
    _memory_cache.clear()
    _message_cache.clear()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.catalog = [
        Volume(
            volume="Orach Chaim",
            volume_he="אורח חיים",
            ref_base="Shulchan_Arukh,_Orach_Chayim",
            max_siman=697,
        ),
        Volume(
            volume="Yoreh De'ah",
            volume_he="יורה דעה",
            ref_base="Shulchan_Arukh,_Yoreh_De'ah",
            max_siman=403,
        ),
        Volume(
            volume="Even HaEzer",
            volume_he="אבן העזר",
            ref_base="Shulchan_Arukh,_Even_HaEzer",
            max_siman=178,
        ),
        Volume(
            volume="Choshen Mishpat",
            volume_he="חושן משפט",
            ref_base="Shulchan_Arukh,_Choshen_Mishpat",
            max_siman=427,
        ),
    ]

    def get_volume(name):
        for v in client.catalog:
            if v.volume == name:
                return v
        return None

    client.get_volume.side_effect = get_volume
    return client


@pytest.fixture
def selector(mock_client):
    return HalachaSelector(mock_client)


def test_deterministic_selection(selector):
    """Same date always picks the same two volumes."""
    d = date(2026, 2, 16)
    rng = selector._get_daily_rng(d)
    vol1, vol2 = selector._select_two_volumes(rng)

    # Run again with same date
    rng2 = selector._get_daily_rng(d)
    vol1b, vol2b = selector._select_two_volumes(rng2)

    assert vol1.volume == vol1b.volume
    assert vol2.volume == vol2b.volume


def test_different_dates_can_differ(selector):
    """Different dates should (usually) pick different volumes."""
    results = set()
    for day in range(1, 31):
        d = date(2026, 3, day)
        rng = selector._get_daily_rng(d)
        vol1, vol2 = selector._select_two_volumes(rng)
        results.add((vol1.volume, vol2.volume))
    # Over 30 days, we should see more than 1 unique pair
    assert len(results) > 1


def test_volumes_are_different(selector):
    """The two volumes should always be different."""
    for day in range(1, 31):
        d = date(2026, 1, day)
        rng = selector._get_daily_rng(d)
        vol1, vol2 = selector._select_two_volumes(rng)
        assert vol1.volume != vol2.volume


def test_get_daily_pair_with_mock_api(selector, mock_client):
    """Test the full selection flow with mocked API."""

    def mock_random(volume, rng):
        """Return a halacha with the correct volume."""
        return Halacha(
            volume=volume,
            siman=rng.randint(1, 10),
            seif=None,
            hebrew_text="יתגבר כארי לעמוד בבוקר לעבודת בוראו שיהא הוא מעורר השחר.",
            sefaria_url=f"https://www.sefaria.org/{volume.ref_base}.1",
        )

    mock_client.get_random_halacha_from_volume.side_effect = mock_random

    with patch("src.selector.CACHE_DIR", Path(tempfile.mkdtemp())):
        pair = selector.get_daily_pair(date(2026, 2, 16))

    assert pair is not None
    assert pair.first.volume.volume != pair.second.volume.volume
