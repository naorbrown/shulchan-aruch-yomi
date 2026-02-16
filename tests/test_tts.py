"""Tests for TTS module."""

from unittest.mock import MagicMock

from src.tts import chunk_text, is_tts_enabled


def test_chunk_text_short():
    assert chunk_text("short") == ["short"]


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("  ") == []


def test_chunk_text_long():
    text = "word " * 500  # ~2500 chars
    chunks = chunk_text(text, max_chars=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 100


def test_chunk_text_sentence_boundaries():
    text = "First sentence. Second sentence. Third sentence."
    chunks = chunk_text(text, max_chars=35)
    assert len(chunks) >= 2
    # Should split at sentence boundary
    assert chunks[0].endswith("sentence.")


def test_chunk_text_hebrew():
    text = "הלכה ראשונה. הלכה שניה: הלכה שלישית."
    chunks = chunk_text(text, max_chars=25)
    assert len(chunks) >= 2


def test_is_tts_enabled_none():
    assert is_tts_enabled(None) is False


def test_is_tts_enabled_false():
    config = MagicMock()
    config.google_tts_enabled = False
    assert is_tts_enabled(config) is False


def test_is_tts_enabled_true():
    config = MagicMock()
    config.google_tts_enabled = True
    assert is_tts_enabled(config) is True
