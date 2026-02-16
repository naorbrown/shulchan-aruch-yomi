"""Configuration management for Shulchan Aruch Yomi."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    telegram_bot_token: str
    telegram_chat_id: str
    log_level: str = "INFO"
    sefaria_base_url: str = "https://www.sefaria.org/api"
    request_timeout: int = 30
    # TTS config (optional — audio is a graceful enhancement)
    google_tts_enabled: bool = False
    google_tts_credentials_json: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is required")

        config = cls(
            telegram_bot_token=token,
            telegram_chat_id=chat_id,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            google_tts_enabled=os.getenv("GOOGLE_TTS_ENABLED", "false").lower()
            == "true",
            google_tts_credentials_json=os.getenv("GOOGLE_TTS_CREDENTIALS_JSON"),
        )

        if config.google_tts_enabled:
            logger.info("TTS voice messages: ENABLED")
            if not config.google_tts_credentials_json:
                logger.warning(
                    "TTS is enabled but GOOGLE_TTS_CREDENTIALS_JSON is not set "
                    "-- voice messages will fail"
                )
        else:
            logger.info(
                "TTS voice messages: DISABLED "
                "(set GOOGLE_TTS_ENABLED=true to enable)"
            )

        return config

    def setup_logging(self) -> None:
        """Configure application logging."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """Get the data directory."""
    return get_project_root() / "data"
