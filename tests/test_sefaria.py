"""Tests for Sefaria API client."""

import pytest
import responses

from src.models import Volume
from src.sefaria import SefariaClient


@pytest.fixture
def client():
    return SefariaClient()


@pytest.fixture
def sample_volume():
    return Volume(
        volume="Orach Chaim",
        volume_he="אורח חיים",
        ref_base="Shulchan_Arukh,_Orach_Chaim",
        max_siman=697,
    )


def test_load_catalog(client):
    catalog = client.catalog
    assert len(catalog) == 4
    names = [v.volume for v in catalog]
    assert "Orach Chaim" in names
    assert "Yoreh De'ah" in names
    assert "Even HaEzer" in names
    assert "Choshen Mishpat" in names


def test_get_volume(client):
    vol = client.get_volume("Orach Chaim")
    assert vol is not None
    assert vol.max_siman == 697

    assert client.get_volume("Nonexistent") is None


def test_clean_text(client):
    assert client._clean_text("<b>hello</b> world") == "hello world"
    assert client._clean_text("  multiple   spaces  ") == "multiple spaces"
    assert client._clean_text("") == ""


@responses.activate
def test_get_text_success(client):
    responses.add(
        responses.GET,
        "https://www.sefaria.org/api/texts/Shulchan_Arukh,_Orach_Chaim.1.1?context=0",
        json={
            "he": "יתגבר כארי",
            "text": "One should strengthen",
            "ref": "Shulchan Arukh, Orach Chaim 1:1",
        },
        status=200,
    )
    result = client.get_text("Shulchan_Arukh,_Orach_Chaim.1.1")
    assert result is not None
    assert result["he"] == "יתגבר כארי"


@responses.activate
def test_get_text_failure(client):
    responses.add(
        responses.GET,
        "https://www.sefaria.org/api/texts/bad_ref?context=0",
        status=404,
    )
    result = client.get_text("bad_ref")
    assert result is None


@responses.activate
def test_fetch_halacha(client, sample_volume):
    responses.add(
        responses.GET,
        "https://www.sefaria.org/api/texts/Shulchan_Arukh,_Orach_Chaim.1.1?context=0",
        json={
            "he": "יתגבר כארי לעמוד בבוקר לעבודת בוראו שיהא הוא מעורר השחר.",
            "text": "",
        },
        status=200,
    )
    halacha = client.fetch_halacha(sample_volume, 1, 1)
    assert halacha is not None
    assert halacha.siman == 1
    assert halacha.seif == 1
    assert "יתגבר" in halacha.hebrew_text


@responses.activate
def test_fetch_halacha_no_text(client, sample_volume):
    responses.add(
        responses.GET,
        "https://www.sefaria.org/api/texts/Shulchan_Arukh,_Orach_Chaim.1.1?context=0",
        json={"he": "", "text": ""},
        status=200,
    )
    halacha = client.fetch_halacha(sample_volume, 1, 1)
    assert halacha is None


@responses.activate
def test_fetch_halacha_html_list(client, sample_volume):
    """Handle case where API returns list of segments."""
    responses.add(
        responses.GET,
        "https://www.sefaria.org/api/texts/Shulchan_Arukh,_Orach_Chaim.5.3?context=0",
        json={
            "he": ["<b>חלק</b> ראשון", "חלק שני של ההלכה"],
            "text": "",
        },
        status=200,
    )
    halacha = client.fetch_halacha(sample_volume, 5, 3)
    assert halacha is not None
    assert "חלק ראשון" in halacha.hebrew_text
    assert "חלק שני" in halacha.hebrew_text
    assert "<b>" not in halacha.hebrew_text
