#!/usr/bin/env python3
"""Poll Telegram for commands and respond.

This script is designed to run via GitHub Actions every 5 minutes.
It polls for new updates, handles commands, and persists state.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commands import (
    get_error_message,
    get_info_message,
    get_start_messages,
    get_today_messages,
)
from src.config import Config
from src.sefaria import SefariaClient
from src.selector import HalachaSelector
from src.subscribers import add_subscriber, is_subscribed, remove_subscriber
from src.tts import is_tts_enabled, send_voice_for_pair

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STATE_DIR = Path(__file__).parent.parent / ".github" / "state"
STATE_FILE = STATE_DIR / "last_update_id.json"


def load_state() -> int:
    """Load last processed update ID from state file."""
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            return int(data.get("last_update_id", 0))
        except (json.JSONDecodeError, KeyError, ValueError):
            return 0
    return 0


def save_state(last_update_id: int) -> None:
    """Save last processed update ID to state file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_update_id": last_update_id}, indent=2))
    logger.info(f"Saved state: last_update_id={last_update_id}")


async def handle_command(
    bot: object,
    chat_id: int,
    command: str,
    selector: HalachaSelector,
    config: Config | None = None,
) -> None:
    """Handle a single command."""
    try:
        if command == "/start":
            was_new = add_subscriber(chat_id)
            if was_new:
                logger.info(f"Auto-subscribed new user {chat_id}")

            messages = get_start_messages(selector)
            for msg in messages:
                await bot.send_message(  # type: ignore[attr-defined]
                    chat_id=chat_id,
                    text=msg,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            logger.info(f"Sent start messages to {chat_id}")

            if is_tts_enabled(config):
                assert config is not None
                pair = selector.get_daily_pair()
                if pair:
                    await send_voice_for_pair(
                        bot, pair, chat_id, config.google_tts_credentials_json
                    )

        elif command == "/today":
            messages = get_today_messages(selector)
            for msg in messages:
                await bot.send_message(  # type: ignore[attr-defined]
                    chat_id=chat_id,
                    text=msg,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            logger.info(f"Sent today's halachot to {chat_id}")

            if is_tts_enabled(config):
                assert config is not None
                pair = selector.get_daily_pair()
                if pair:
                    await send_voice_for_pair(
                        bot, pair, chat_id, config.google_tts_credentials_json
                    )

        elif command in ("/info", "/about", "/help"):
            await bot.send_message(  # type: ignore[attr-defined]
                chat_id=chat_id,
                text=get_info_message(),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            logger.info(f"Sent info message to {chat_id}")

        elif command == "/subscribe":
            if is_subscribed(chat_id):
                await bot.send_message(  # type: ignore[attr-defined]
                    chat_id=chat_id,
                    text="✅ אתה כבר רשום לקבלת הלכות יומיות.",
                    parse_mode="HTML",
                )
            else:
                add_subscriber(chat_id)
                await bot.send_message(  # type: ignore[attr-defined]
                    chat_id=chat_id,
                    text="✅ נרשמת בהצלחה! תקבל הלכות יומיות כל בוקר.",
                    parse_mode="HTML",
                )
            logger.info(f"Subscribe command from {chat_id}")

        elif command == "/unsubscribe":
            if remove_subscriber(chat_id):
                await bot.send_message(  # type: ignore[attr-defined]
                    chat_id=chat_id,
                    text="✅ הסרת את הרישום. לא תקבל עוד הלכות יומיות.\nאפשר להירשם מחדש עם /subscribe",
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(  # type: ignore[attr-defined]
                    chat_id=chat_id,
                    text="אתה לא רשום כרגע. להרשמה שלח /subscribe",
                    parse_mode="HTML",
                )
            logger.info(f"Unsubscribe command from {chat_id}")

        else:
            logger.debug(f"Unknown command '{command}' from {chat_id} - ignoring")

    except Exception as e:
        logger.error(f"Error handling command {command} for {chat_id}: {e}")
        try:
            await bot.send_message(  # type: ignore[attr-defined]
                chat_id=chat_id,
                text=get_error_message(),
                parse_mode="HTML",
            )
        except Exception:
            pass


async def poll_and_respond() -> bool:
    """Poll for updates and respond to commands."""
    try:
        from telegram import Bot
        from telegram.error import NetworkError, TimedOut
    except ImportError as e:
        logger.error(f"telegram module not available: {e}")
        return False

    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return False

    client = SefariaClient()
    selector = HalachaSelector(client)

    cached = selector.get_cached_messages()
    if cached:
        logger.info(
            f"Cache pre-warmed: {len(cached)} messages ready for instant response"
        )
    else:
        logger.warning("No cached messages available - responses may be slower")

    last_update_id = load_state()
    logger.info(f"Starting poll with offset {last_update_id + 1}")

    max_retries = 3
    async with Bot(token=config.telegram_bot_token) as bot:
        try:
            webhook_deleted = await bot.delete_webhook(drop_pending_updates=False)
            if webhook_deleted:
                logger.info("Webhook cleared, ready for polling")
        except (TimedOut, NetworkError) as e:
            logger.warning(f"Could not clear webhook (will retry on next run): {e}")

        updates = None
        for attempt in range(1, max_retries + 1):
            try:
                updates = await bot.get_updates(
                    offset=last_update_id + 1,
                    timeout=10,
                    allowed_updates=["message"],
                )
                break
            except (TimedOut, NetworkError) as e:
                if attempt < max_retries:
                    wait = attempt * 2
                    logger.warning(
                        f"get_updates attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.warning(
                        f"get_updates failed after {max_retries} attempts: {e}. "
                        "Will retry on next scheduled run."
                    )
                    return True

        if not updates:
            logger.info("No new updates")
            return True

        logger.info(f"Processing {len(updates)} update(s)")

        new_last_update_id = last_update_id
        for update in updates:
            new_last_update_id = max(new_last_update_id, update.update_id)

            if not update.message or not update.message.text:
                continue

            text = update.message.text.strip()
            chat_id = update.message.chat_id

            if text.startswith("/"):
                command = text.split()[0].split("@")[0].lower()
                logger.info(f"Processing command '{command}' from chat {chat_id}")
                await handle_command(bot, chat_id, command, selector, config)

        if new_last_update_id > last_update_id:
            save_state(new_last_update_id)

        return True


def main() -> None:
    """Main entry point."""
    logger.info("=== Poll Commands Script Started ===")

    try:
        success = asyncio.run(poll_and_respond())
    except Exception as e:
        logger.warning(f"Poll encountered error (non-fatal): {e}")
        success = True

    if success:
        logger.info("=== Poll completed successfully ===")
    else:
        logger.warning("=== Poll completed with issues (non-fatal) ===")

    sys.exit(0)


if __name__ == "__main__":
    main()
