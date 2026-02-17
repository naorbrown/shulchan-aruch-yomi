"""Sefaria API client for fetching Shulchan Aruch texts."""

import json
import logging
import random
import re
from typing import Any

import requests

from .config import get_data_dir
from .models import Halacha, Volume

logger = logging.getLogger(__name__)

VOLUME_NAMES = ["Orach Chaim", "Yoreh De'ah", "Even HaEzer", "Choshen Mishpat"]


class SefariaClient:
    """Client for the Sefaria API."""

    BASE_URL = "https://www.sefaria.org/api"
    WEB_URL = "https://www.sefaria.org"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ShulchanAruchYomiBot/1.0",
                "Connection": "keep-alive",
            }
        )
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=1,
        )
        self.session.mount("https://", adapter)
        self._catalog: list[Volume] | None = None

    @property
    def catalog(self) -> list[Volume]:
        """Load and cache the volume catalog."""
        if self._catalog is None:
            self._catalog = self._load_catalog()
        return self._catalog

    def _load_catalog(self) -> list[Volume]:
        """Load the volume catalog from data/volumes.json."""
        catalog_path = get_data_dir() / "volumes.json"
        if not catalog_path.exists():
            raise FileNotFoundError(f"Volume catalog not found at {catalog_path}")

        with open(catalog_path, encoding="utf-8") as f:
            data = json.load(f)

        return [
            Volume(
                volume=item["volume"],
                volume_he=item["volume_he"],
                ref_base=item["ref_base"],
                max_siman=item["max_siman"],
            )
            for item in data
        ]

    def get_volume(self, name: str) -> Volume | None:
        """Get a volume by English name."""
        for v in self.catalog:
            if v.volume == name:
                return v
        return None

    def get_text(self, reference: str) -> dict[str, Any] | None:
        """Fetch text from Sefaria API."""
        url = f"{self.BASE_URL}/texts/{reference}?context=0"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {reference}: {e}")
            return None

    def fetch_full_siman(self, volume: Volume, siman: int) -> Halacha | None:
        """Fetch a complete siman (all seifim) from Sefaria."""
        reference = f"{volume.ref_base}.{siman}"
        data = self.get_text(reference)

        if not data:
            return None

        # Extract Hebrew text — full siman returns a list of seifim
        hebrew_raw = data.get("he", [])
        if isinstance(hebrew_raw, str):
            hebrew_raw = [hebrew_raw]

        cleaned_seifim = [self._clean_text(s) for s in hebrew_raw if s]
        cleaned_seifim = [s for s in cleaned_seifim if s]

        if not cleaned_seifim:
            logger.warning(f"No Hebrew text for {reference}")
            return None

        hebrew = "\n".join(cleaned_seifim)

        if len(hebrew) < 10:
            logger.warning(f"Hebrew text too short for {reference}")
            return None

        sefaria_url = f"{self.WEB_URL}/{reference.replace(' ', '_')}"

        return Halacha(
            volume=volume,
            siman=siman,
            seif=None,
            hebrew_text=hebrew,
            sefaria_url=sefaria_url,
        )

    def _clean_text(self, text: str) -> str:
        """Clean HTML and normalize text."""
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def get_random_halacha_from_volume(
        self, volume: Volume, rng: random.Random
    ) -> Halacha | None:
        """Get a random full siman from a specific volume.

        Uses the provided RNG for deterministic selection.
        Strategy: pick random siman, fetch all seifim.
        """
        for attempt in range(10):
            siman = rng.randint(1, volume.max_siman)

            halacha = self.fetch_full_siman(volume, siman)
            if halacha:
                logger.info(
                    f"Found halacha: {halacha.reference} (attempt {attempt + 1})"
                )
                return halacha

        logger.error(
            f"Failed to find valid halacha in {volume.volume} after 10 attempts"
        )
        return None
