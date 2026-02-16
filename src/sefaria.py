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

    def fetch_halacha(self, volume: Volume, siman: int, seif: int) -> Halacha | None:
        """Fetch a specific halacha (seif) from Sefaria."""
        reference = f"{volume.ref_base}.{siman}.{seif}"
        data = self.get_text(reference)

        if not data:
            return None

        # Extract Hebrew text
        hebrew = data.get("he", "")
        if isinstance(hebrew, list):
            hebrew = " ".join(str(p) for p in hebrew if p)

        hebrew = self._clean_text(hebrew)

        if not hebrew or len(hebrew) < 10:
            logger.warning(f"No Hebrew text for {reference}")
            return None

        # Build Sefaria URL
        sefaria_url = f"{self.WEB_URL}/{reference.replace(' ', '_')}"

        return Halacha(
            volume=volume,
            siman=siman,
            seif=seif,
            hebrew_text=hebrew,
            sefaria_url=sefaria_url,
        )

    def _get_seif_count(self, volume: Volume, siman: int) -> int | None:
        """Fetch a full siman to discover how many seifim it has."""
        reference = f"{volume.ref_base}.{siman}"
        data = self.get_text(reference)
        if not data:
            return None

        he = data.get("he", [])
        if isinstance(he, list):
            return len(he)
        return None

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
        """Get a random halacha from a specific volume.

        Uses the provided RNG for deterministic selection.
        Strategy: pick random siman, fetch it to find seif count, pick random seif.
        """
        for attempt in range(10):
            siman = rng.randint(1, volume.max_siman)

            # Get seif count for this siman
            seif_count = self._get_seif_count(volume, siman)
            if seif_count and seif_count > 0:
                seif = rng.randint(1, seif_count)
                halacha = self.fetch_halacha(volume, siman, seif)
                if halacha:
                    logger.info(
                        f"Found halacha: {halacha.reference} (attempt {attempt + 1})"
                    )
                    return halacha

            # Fallback: try seif 1 directly
            halacha = self.fetch_halacha(volume, siman, 1)
            if halacha:
                logger.info(
                    f"Found halacha: {halacha.reference} (attempt {attempt + 1})"
                )
                return halacha

        logger.error(
            f"Failed to find valid halacha in {volume.volume} after 10 attempts"
        )
        return None
