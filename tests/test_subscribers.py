"""Tests for subscriber management."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.subscribers import (
    add_subscriber,
    get_subscriber_count,
    is_subscribed,
    load_subscribers,
    remove_subscriber,
    save_subscribers,
)


def _temp_state():
    """Create a context with temporary state directory."""
    tmpdir = Path(tempfile.mkdtemp())
    state_dir = tmpdir / "state"
    state_dir.mkdir()
    subs_file = state_dir / "subscribers.json"
    return state_dir, subs_file


def test_load_empty():
    _, subs_file = _temp_state()
    with patch("src.subscribers.SUBSCRIBERS_FILE", subs_file):
        assert load_subscribers() == set()


def test_save_and_load():
    state_dir, subs_file = _temp_state()
    with (
        patch("src.subscribers.SUBSCRIBERS_FILE", subs_file),
        patch("src.subscribers.STATE_DIR", state_dir),
    ):
        save_subscribers({111, 222, 333})
        loaded = load_subscribers()
        assert loaded == {111, 222, 333}


def test_add_subscriber():
    state_dir, subs_file = _temp_state()
    with (
        patch("src.subscribers.SUBSCRIBERS_FILE", subs_file),
        patch("src.subscribers.STATE_DIR", state_dir),
    ):
        assert add_subscriber(100) is True
        assert add_subscriber(100) is False  # Already exists
        assert is_subscribed(100) is True


def test_remove_subscriber():
    state_dir, subs_file = _temp_state()
    with (
        patch("src.subscribers.SUBSCRIBERS_FILE", subs_file),
        patch("src.subscribers.STATE_DIR", state_dir),
    ):
        add_subscriber(200)
        assert remove_subscriber(200) is True
        assert remove_subscriber(200) is False  # Already removed
        assert is_subscribed(200) is False


def test_subscriber_count():
    state_dir, subs_file = _temp_state()
    with (
        patch("src.subscribers.SUBSCRIBERS_FILE", subs_file),
        patch("src.subscribers.STATE_DIR", state_dir),
    ):
        add_subscriber(1)
        add_subscriber(2)
        add_subscriber(3)
        assert get_subscriber_count() == 3
