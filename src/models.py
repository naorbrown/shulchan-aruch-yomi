"""Data models for Shulchan Aruch Yomi."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Volume:
    """A volume of the Shulchan Aruch."""

    volume: str  # English name: Orach Chaim, Yoreh De'ah, etc.
    volume_he: str  # Hebrew name
    ref_base: str  # Sefaria reference base (e.g. Shulchan_Arukh,_Orach_Chayim)
    max_siman: int  # Highest siman number in this volume


@dataclass(frozen=True)
class Halacha:
    """A full siman (chapter) from the Shulchan Aruch."""

    volume: Volume
    siman: int
    seif: int | None  # None = full siman, int = specific seif
    hebrew_text: str
    sefaria_url: str

    @property
    def reference(self) -> str:
        """Full Sefaria reference string."""
        if self.seif is not None:
            return f"{self.volume.ref_base}.{self.siman}.{self.seif}"
        return f"{self.volume.ref_base}.{self.siman}"

    @property
    def hebrew_reference(self) -> str:
        """Hebrew reference for display."""
        base = f"שולחן ערוך, {self.volume.volume_he}, סימן {self.siman}"
        if self.seif is not None:
            return f"{base} סעיף {self.seif}"
        return base


@dataclass(frozen=True)
class DailyPair:
    """A pair of halachot for the day from two different volumes."""

    first: Halacha
    second: Halacha
    date_seed: str  # Date string used for deterministic selection

    def __post_init__(self) -> None:
        """Validate that halachot are from different volumes."""
        if self.first.volume.volume == self.second.volume.volume:
            raise ValueError("Daily pair must contain halachot from different volumes")
