#!/usr/bin/env python3
"""Run the bot locally in interactive polling mode."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.bot import ShulchanAruchYomiBot
from src.config import Config


def main() -> None:
    """Start the bot in polling mode."""
    load_dotenv()
    config = Config.from_env()
    config.setup_logging()

    bot = ShulchanAruchYomiBot(config)
    bot.run_polling()


if __name__ == "__main__":
    main()
