"""Hebrew Text-to-Speech using Google Cloud TTS."""

from __future__ import annotations

import io
import logging
import os
import re
import tempfile
from datetime import date
from typing import TYPE_CHECKING

from google.cloud import texttospeech
from pydub import AudioSegment

from .config import get_data_dir
from .models import DailyPair

if TYPE_CHECKING:
    from .config import Config

logger = logging.getLogger(__name__)

# Audio cache directory
AUDIO_CACHE_DIR = get_data_dir() / "cache" / "audio"

# Google Cloud TTS byte limit is 5000 per request.
# Nikud'd Hebrew is ~4 bytes/char, so ~1200 chars stays safely under the limit.
MAX_CHUNK_CHARS = 1200

# Voice selection
VOICE_NAME = "he-IL-Wavenet-D"
LANGUAGE_CODE = "he-IL"

# Speaking rate multiplier (1.0 = normal speed)
SPEAKING_RATE = 1.0

# Silence between chunks (milliseconds)
INTER_CHUNK_SILENCE_MS = 300


def is_tts_enabled(config: Config | None) -> bool:
    """Check whether TTS voice messages should be sent."""
    if config is None:
        return False
    return config.google_tts_enabled


class HebrewTTSClient:
    """Client for generating Hebrew audio using Google Cloud TTS."""

    def __init__(self, credentials_json: str | None = None):
        self._temp_creds_path: str | None = None

        if credentials_json:
            fd, path = tempfile.mkstemp(suffix=".json", prefix="gcloud_tts_")
            os.write(fd, credentials_json.encode())
            os.close(fd)
            self._temp_creds_path = path
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path

        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code=LANGUAGE_CODE,
            name=VOICE_NAME,
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.OGG_OPUS,
            speaking_rate=SPEAKING_RATE,
        )

    def __del__(self) -> None:
        """Clean up temp credentials file."""
        if self._temp_creds_path and os.path.exists(self._temp_creds_path):
            os.unlink(self._temp_creds_path)

    def get_or_generate_audio(self, text: str, cache_key: str) -> bytes | None:
        """Get audio from cache or generate it."""
        cache_path = AUDIO_CACHE_DIR / f"{cache_key}.ogg"
        if cache_path.exists():
            logger.info(f"Audio cache hit: {cache_key}")
            return cache_path.read_bytes()

        audio = self.synthesize_text(text)
        if audio:
            AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(audio)
            logger.info(f"Cached audio: {cache_key} ({len(audio)} bytes)")
        return audio

    def synthesize_text(self, text: str) -> bytes | None:
        """Synthesize Hebrew text to OGG Opus audio."""
        try:
            chunks = chunk_text(text)
            logger.info(f"Synthesizing {len(chunks)} chunk(s), {len(text)} chars total")

            audio_chunks = []
            for i, chunk in enumerate(chunks):
                audio_bytes = self._synthesize_chunk(chunk)
                audio_chunks.append(audio_bytes)
                logger.debug(f"Chunk {i + 1}/{len(chunks)}: {len(audio_bytes)} bytes")

            if len(audio_chunks) == 1:
                return audio_chunks[0]

            return _concatenate_audio(audio_chunks)

        except Exception:
            logger.exception("TTS synthesis failed")
            return None

    def _synthesize_chunk(self, chunk: str) -> bytes:
        """Synthesize a single text chunk via Google Cloud TTS."""
        synthesis_input = texttospeech.SynthesisInput(text=chunk)
        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=self.voice,
            audio_config=self.audio_config,
        )
        return response.audio_content


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split Hebrew text into chunks for TTS synthesis."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentence_pattern = re.compile(r"(?<=[.:׃])\s+")
    sentences = sentence_pattern.split(text)

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(sentence) > max_chars:
                words = sentence.split()
                current = ""
                for word in words:
                    candidate = f"{current} {word}".strip() if current else word
                    if len(candidate) <= max_chars:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def _concatenate_audio(audio_chunks: list[bytes]) -> bytes:
    """Concatenate OGG Opus audio chunks with silence gaps."""
    silence = AudioSegment.silent(duration=INTER_CHUNK_SILENCE_MS)
    combined = AudioSegment.empty()

    for i, chunk_bytes in enumerate(audio_chunks):
        segment = AudioSegment.from_ogg(io.BytesIO(chunk_bytes))
        if i > 0:
            combined += silence
        combined += segment

    buf = io.BytesIO()
    combined.export(buf, format="ogg", codec="libopus")
    return buf.getvalue()


async def send_voice_for_pair(
    bot: object,
    pair: DailyPair,
    chat_id: int | str,
    credentials_json: str | None = None,
    today: date | None = None,
    *,
    _tts_client: HebrewTTSClient | None = None,
) -> None:
    """Generate and send voice messages for a daily halacha pair.

    Non-blocking: TTS failure never raises — it logs and returns.
    """
    if today is None:
        today = date.today()

    try:
        tts = _tts_client or HebrewTTSClient(credentials_json)
        today_str = today.isoformat()

        halachot = [
            (pair.first, f"audio_{today_str}_1", "א"),
            (pair.second, f"audio_{today_str}_2", "ב"),
        ]

        for halacha, cache_key, label in halachot:
            audio = tts.get_or_generate_audio(halacha.hebrew_text, cache_key)
            if not audio:
                logger.warning(f"TTS failed for halacha {label}, skipping voice")
                continue

            vol_he = halacha.volume.volume_he
            caption = f"\U0001f509 {label}. {vol_he} — סימן {halacha.siman}"

            await bot.send_voice(  # type: ignore[attr-defined]
                chat_id=chat_id,
                voice=audio,
                caption=caption,
                read_timeout=30,
                write_timeout=30,
            )
            logger.info(f"Voice message {label} sent to {chat_id}")

        logger.info(f"Voice messages completed for {chat_id}")

    except Exception:
        logger.exception(f"Voice message delivery failed for {chat_id}")
