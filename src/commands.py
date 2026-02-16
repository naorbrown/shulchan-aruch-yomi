"""Command logic for Telegram bot.

This module provides the core text message logic used by both:
- bot.py (Application framework handlers)
- poll_commands.py (Stateless GitHub Actions polling)

Returns formatted text messages only. Voice messages are handled separately
by send_voice_for_pair() in tts.py.
"""

from __future__ import annotations

import logging
from datetime import date

from .formatter import (
    format_daily_message,
    format_error_message,
    format_info_message,
    format_welcome_message,
)
from .selector import HalachaSelector

logger = logging.getLogger(__name__)


def get_start_messages(
    selector: HalachaSelector, for_date: date | None = None
) -> list[str]:
    """Get text messages for /start command (welcome + daily content)."""
    if for_date is None:
        for_date = date.today()

    try:
        cached_messages = selector.get_cached_messages(for_date)
        if cached_messages:
            logger.debug(f"Using cached messages for {for_date}")
            return cached_messages

        messages = [format_welcome_message()]
        pair = selector.get_daily_pair(for_date)
        if pair:
            messages.extend(format_daily_message(pair, for_date))
        else:
            logger.warning(f"No daily pair available for {for_date}")
            messages.append(format_error_message())
        return messages
    except Exception as e:
        logger.exception(f"Error getting daily pair: {e}")
        return [format_welcome_message(), format_error_message()]


def get_today_messages(
    selector: HalachaSelector, for_date: date | None = None
) -> list[str]:
    """Get text messages for /today command (just daily content, no welcome)."""
    if for_date is None:
        for_date = date.today()

    try:
        cached_messages = selector.get_cached_messages(for_date)
        if cached_messages and len(cached_messages) > 1:
            logger.debug(f"Using cached content for {for_date}")
            return cached_messages[1:]

        pair = selector.get_daily_pair(for_date)
        if pair:
            return format_daily_message(pair, for_date)
        else:
            logger.warning(f"No daily pair available for {for_date}")
            return [format_error_message()]
    except Exception as e:
        logger.exception(f"Error getting daily pair: {e}")
        return [format_error_message()]


def get_info_message() -> str:
    """Get message for /info command."""
    return format_info_message()


def get_error_message() -> str:
    """Get generic error message."""
    return format_error_message()
