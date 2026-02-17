#!/usr/bin/env python3
"""
Shulchan Aruch Yomi - Daily halachot from the Shulchan Aruch.

Usage:
    python main.py              # Send daily broadcast (for cron/CI)
    python main.py --serve      # Run interactive bot
    python main.py --preview    # Preview today's message
"""

import argparse
import asyncio
import logging
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from src.bot import ShulchanAruchYomiBot
from src.config import Config
from src.formatter import format_daily_message
from src.sefaria import SefariaClient
from src.selector import HalachaSelector

logger = logging.getLogger(__name__)

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")


def is_broadcast_hour() -> bool:
    """Check if it's currently the 3am hour in Israel."""
    israel_now = datetime.now(ISRAEL_TZ)
    return israel_now.hour == 3


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Shulchan Aruch Yomi Telegram Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py              Send daily message to configured chat
    python main.py --serve      Run interactive bot with polling
    python main.py --preview    Preview today's message locally
        """,
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run bot in interactive polling mode",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview today's message without sending",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Override date for preview (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Send broadcast regardless of time (for manual triggers)",
    )
    return parser.parse_args()


def preview_message(date_override: str | None = None) -> None:
    """Preview today's message without sending."""
    import re

    client = SefariaClient()
    selector = HalachaSelector(client)

    if date_override:
        target_date = datetime.strptime(date_override, "%Y-%m-%d").date()
    else:
        target_date = date.today()

    print(f"\n{'=' * 60}")
    print(f"Preview for: {target_date}")
    print("=" * 60)

    pair = selector.get_daily_pair(target_date)
    if pair:
        messages = format_daily_message(pair, target_date)
        for i, msg in enumerate(messages, 1):
            readable = re.sub(r"<[^>]+>", "", msg)
            print(f"\n--- Message {i} ---")
            print(readable)

        print(f"\n{'=' * 60}")
        total_chars = sum(len(m) for m in messages)
        print(f"Total messages: {len(messages)}")
        print(f"Total characters: {total_chars}")
        print(f"First halacha: {pair.first.reference}")
        print(f"Second halacha: {pair.second.reference}")
    else:
        print("ERROR: Failed to get daily pair")
        sys.exit(1)


async def send_broadcast(config: Config) -> bool:
    """Send the daily broadcast."""
    bot = ShulchanAruchYomiBot(config)
    return await bot.send_daily_broadcast()


def run_server(config: Config) -> None:
    """Run the bot in interactive mode."""
    bot = ShulchanAruchYomiBot(config)
    bot.run_polling()


def main() -> int:
    """Main entry point."""
    load_dotenv()

    args = parse_args()

    if args.preview:
        preview_message(args.date)
        return 0

    try:
        config = Config.from_env()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    config.setup_logging()
    logger.info("Shulchan Aruch Yomi starting...")
    logger.info(f"Chat ID: {config.telegram_chat_id}")
    logger.info(f"Token: {config.telegram_bot_token[:10]}...")

    if args.serve:
        run_server(config)
        return 0
    else:
        if not args.force and not is_broadcast_hour():
            israel_now = datetime.now(ISRAEL_TZ)
            logger.info(
                f"Skipping broadcast: Israel time is {israel_now.strftime('%H:%M')} "
                f"(not 3am). DST handling - other scheduled run will send."
            )
            return 0

        logger.info("Sending daily broadcast...")
        success = asyncio.run(send_broadcast(config))
        if success:
            logger.info("Broadcast completed successfully!")
        else:
            logger.error("Broadcast failed!")
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
