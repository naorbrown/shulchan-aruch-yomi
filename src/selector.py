"""Daily halacha selection logic."""

import hashlib
import json
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from .config import get_data_dir
from .formatter import format_daily_message, format_welcome_message
from .models import DailyPair, Halacha, Volume
from .sefaria import VOLUME_NAMES, SefariaClient

logger = logging.getLogger(__name__)

CACHE_DIR = get_data_dir() / "cache"

# In-memory cache for daily pairs (avoids repeated file I/O)
_memory_cache: dict[str, DailyPair] = {}

# In-memory cache for pre-formatted messages (instant responses)
_message_cache: dict[str, list[str]] = {}


class HalachaSelector:
    """Selects two random halachot from different volumes each day."""

    def __init__(self, client: SefariaClient):
        self.client = client

    def _get_daily_seed(self, for_date: date) -> str:
        """Generate a deterministic seed for a given date."""
        return for_date.isoformat()

    def _get_daily_rng(self, for_date: date) -> random.Random:
        """Get a seeded RNG for deterministic daily selection."""
        seed = self._get_daily_seed(for_date)
        seed_int = int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)
        return random.Random(seed_int)

    def _select_two_volumes(self, rng: random.Random) -> tuple[Volume, Volume]:
        """Select two different volumes for the day."""
        names = VOLUME_NAMES.copy()
        rng.shuffle(names)
        vol1 = self.client.get_volume(names[0])
        vol2 = self.client.get_volume(names[1])
        if not vol1 or not vol2:
            raise RuntimeError("Failed to load volume catalog")
        return vol1, vol2

    def _get_cache_path(self, for_date: date) -> Path:
        """Get the cache file path for a date."""
        return CACHE_DIR / f"pair_{for_date.isoformat()}.json"

    def _load_cached_pair(self, for_date: date) -> DailyPair | None:
        """Load cached daily pair if available."""
        cache_key = for_date.isoformat()

        if cache_key in _memory_cache:
            logger.debug(f"Memory cache hit for {for_date}")
            return _memory_cache[cache_key]

        cache_path = self._get_cache_path(for_date)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            first_vol = Volume(**data["first"]["volume"])
            first = Halacha(
                volume=first_vol,
                siman=data["first"]["siman"],
                seif=data["first"]["seif"],
                hebrew_text=data["first"]["hebrew_text"],
                sefaria_url=data["first"]["sefaria_url"],
            )

            second_vol = Volume(**data["second"]["volume"])
            second = Halacha(
                volume=second_vol,
                siman=data["second"]["siman"],
                seif=data["second"]["seif"],
                hebrew_text=data["second"]["hebrew_text"],
                sefaria_url=data["second"]["sefaria_url"],
            )

            pair = DailyPair(first=first, second=second, date_seed=data["date_seed"])
            _memory_cache[cache_key] = pair

            if "formatted_messages" in data:
                _message_cache[cache_key] = data["formatted_messages"]
                logger.debug(f"Loaded cached formatted messages for {for_date}")
            else:
                welcome = format_welcome_message()
                content_messages = format_daily_message(pair, for_date)
                _message_cache[cache_key] = [welcome] + content_messages

            logger.info(f"Loaded cached pair for {for_date}")
            return pair
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to load cache for {for_date}: {e}")
            return None

    def _save_cached_pair(self, pair: DailyPair, for_date: date) -> None:
        """Save daily pair and pre-formatted messages to cache."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = self._get_cache_path(for_date)

        welcome = format_welcome_message()
        content_messages = format_daily_message(pair, for_date)
        formatted_messages = [welcome] + content_messages

        cache_key = for_date.isoformat()
        _message_cache[cache_key] = formatted_messages

        data = {
            "date_seed": pair.date_seed,
            "formatted_messages": formatted_messages,
            "first": {
                "volume": {
                    "volume": pair.first.volume.volume,
                    "volume_he": pair.first.volume.volume_he,
                    "ref_base": pair.first.volume.ref_base,
                    "max_siman": pair.first.volume.max_siman,
                },
                "siman": pair.first.siman,
                "seif": pair.first.seif,
                "hebrew_text": pair.first.hebrew_text,
                "sefaria_url": pair.first.sefaria_url,
            },
            "second": {
                "volume": {
                    "volume": pair.second.volume.volume,
                    "volume_he": pair.second.volume.volume_he,
                    "ref_base": pair.second.volume.ref_base,
                    "max_siman": pair.second.volume.max_siman,
                },
                "siman": pair.second.siman,
                "seif": pair.second.seif,
                "hebrew_text": pair.second.hebrew_text,
                "sefaria_url": pair.second.sefaria_url,
            },
        }

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Cached pair and formatted messages for {for_date}")

    def _get_fallback_halacha(self, volume: Volume, rng: random.Random) -> Halacha:
        """Create a fallback halacha when API fails."""
        siman = rng.randint(1, volume.max_siman)
        return Halacha(
            volume=volume,
            siman=siman,
            seif=1,
            hebrew_text="לא ניתן לטעון את הטקסט כרגע. לחץ על הקישור לקריאה בספריא.",
            sefaria_url=f"https://www.sefaria.org/{volume.ref_base.replace(' ', '_')}.{siman}",
        )

    def get_daily_pair(self, for_date: date | None = None) -> DailyPair | None:
        """Get the pair of halachot for a given date.

        Selection is deterministic - same date always returns same pair.
        Uses caching to avoid repeated API calls.
        """
        if for_date is None:
            for_date = date.today()

        cached = self._load_cached_pair(for_date)
        if cached:
            return cached

        rng = self._get_daily_rng(for_date)
        vol1, vol2 = self._select_two_volumes(rng)

        logger.info(f"Selecting halachot for {for_date}: {vol1.volume} + {vol2.volume}")

        rng1 = random.Random(
            int(
                hashlib.sha256(f"{for_date.isoformat()}-1".encode()).hexdigest()[:16],
                16,
            )
        )
        rng2 = random.Random(
            int(
                hashlib.sha256(f"{for_date.isoformat()}-2".encode()).hexdigest()[:16],
                16,
            )
        )

        first: Halacha | None = None
        second: Halacha | None = None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(
                self.client.get_random_halacha_from_volume, vol1, rng1
            )
            future2 = executor.submit(
                self.client.get_random_halacha_from_volume, vol2, rng2
            )
            first = future1.result()
            second = future2.result()

        if not first:
            logger.warning(f"API failed for {vol1.volume}, using fallback")
            first = self._get_fallback_halacha(vol1, rng)
        if not second:
            logger.warning(f"API failed for {vol2.volume}, using fallback")
            second = self._get_fallback_halacha(vol2, rng)

        pair = DailyPair(
            first=first,
            second=second,
            date_seed=self._get_daily_seed(for_date),
        )

        fallback_marker = "לא ניתן לטעון"
        if (
            fallback_marker not in first.hebrew_text
            and fallback_marker not in second.hebrew_text
        ):
            self._save_cached_pair(pair, for_date)

        _memory_cache[for_date.isoformat()] = pair

        return pair

    def get_cached_messages(self, for_date: date | None = None) -> list[str] | None:
        """Get pre-formatted messages for a date if cached."""
        if for_date is None:
            for_date = date.today()

        cache_key = for_date.isoformat()

        if cache_key in _message_cache:
            logger.debug(f"Message cache hit for {for_date}")
            return _message_cache[cache_key]

        self._load_cached_pair(for_date)

        if cache_key in _message_cache:
            return _message_cache[cache_key]

        return None
