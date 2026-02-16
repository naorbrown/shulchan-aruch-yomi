"""Torah Yomi Unified Channel Publisher for Shulchan Aruch Bot."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

UNIFIED_CHANNEL_ID = os.getenv("TORAH_YOMI_CHANNEL_ID")
UNIFIED_BOT_TOKEN = os.getenv("TORAH_YOMI_CHANNEL_BOT_TOKEN")
PUBLISH_ENABLED = os.getenv("TORAH_YOMI_PUBLISH_ENABLED", "true").lower() == "true"

SOURCE = "shulchan_aruch"
BADGE = "📖 Shulchan Aruch | שולחן ערוך"

MAX_RETRIES = 3
RETRY_DELAY = 1.0


def format_for_unified_channel(content: str) -> str:
    """Format message with unified channel header."""
    header = f"{BADGE}\n{'─' * 30}\n\n"
    return f"{header}{content}"


def is_unified_channel_enabled() -> bool:
    """Check if unified channel publishing is enabled."""
    return PUBLISH_ENABLED and bool(UNIFIED_CHANNEL_ID) and bool(UNIFIED_BOT_TOKEN)


class TorahYomiPublisher:
    """Publisher for the unified Torah Yomi channel."""

    def __init__(self) -> None:
        pass

    async def publish_text(
        self,
        text: str,
        *,
        parse_mode: str = ParseMode.HTML,
        disable_web_page_preview: bool = True,
        **kwargs: Any,
    ) -> bool:
        """Publish a text message to the unified channel."""
        if not is_unified_channel_enabled():
            logger.debug("Unified channel publish disabled or not configured")
            return False

        if not UNIFIED_BOT_TOKEN or not UNIFIED_CHANNEL_ID:
            logger.error("No bot token or channel ID configured")
            return False

        formatted_text = format_for_unified_channel(text)

        bot = Bot(token=UNIFIED_BOT_TOKEN)
        channel_id = UNIFIED_CHANNEL_ID
        async with bot:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    await bot.send_message(
                        chat_id=channel_id,
                        text=formatted_text,
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_web_page_preview,
                        **kwargs,
                    )
                    logger.info(f"Published text to unified channel ({SOURCE})")
                    return True
                except TelegramError as e:
                    logger.error(f"Publish attempt {attempt} failed: {e}")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY * attempt)

        logger.error("All publish attempts failed")
        return False


async def publish_text_to_unified_channel(text: str, **kwargs: Any) -> bool:
    """Convenience function to publish text."""
    publisher = TorahYomiPublisher()
    return await publisher.publish_text(text, **kwargs)
