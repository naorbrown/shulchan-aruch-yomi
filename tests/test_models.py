"""Tests for data models."""

import pytest

from src.models import DailyPair, Halacha, Volume


def test_volume_creation():
    vol = Volume(
        volume="Orach Chaim",
        volume_he="אורח חיים",
        ref_base="Shulchan_Arukh,_Orach_Chaim",
        max_siman=697,
    )
    assert vol.volume == "Orach Chaim"
    assert vol.volume_he == "אורח חיים"
    assert vol.max_siman == 697


def test_volume_frozen():
    vol = Volume(
        volume="Orach Chaim",
        volume_he="אורח חיים",
        ref_base="Shulchan_Arukh,_Orach_Chaim",
        max_siman=697,
    )
    with pytest.raises(AttributeError):
        vol.volume = "Other"  # type: ignore[misc]


def test_halacha_reference(sample_halacha_1):
    assert sample_halacha_1.reference == "Shulchan_Arukh,_Orach_Chaim.1.1"


def test_halacha_hebrew_reference(sample_halacha_1):
    ref = sample_halacha_1.hebrew_reference
    assert "שולחן ערוך" in ref
    assert "אורח חיים" in ref
    assert "סימן 1" in ref
    assert "סעיף 1" in ref


def test_daily_pair_validates_different_volumes(sample_halacha_1, sample_volume_oc):
    """DailyPair must have halachot from different volumes."""
    same_vol_halacha = Halacha(
        volume=sample_volume_oc,
        siman=2,
        seif=1,
        hebrew_text="Test text here for validation.",
        sefaria_url="https://www.sefaria.org/test",
    )
    with pytest.raises(ValueError, match="different volumes"):
        DailyPair(
            first=sample_halacha_1,
            second=same_vol_halacha,
            date_seed="2026-02-16",
        )


def test_daily_pair_different_volumes(sample_pair):
    assert sample_pair.first.volume.volume != sample_pair.second.volume.volume
    assert sample_pair.date_seed == "2026-02-16"
