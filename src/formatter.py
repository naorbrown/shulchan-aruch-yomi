"""Message formatting for Telegram."""

from collections.abc import Callable
from datetime import date

from .models import DailyPair, Halacha

MAX_MESSAGE_LENGTH = 4000

_STATIC_MESSAGES: dict[str, str] = {}


def _get_static_message(key: str, generator: Callable[[], str]) -> str:
    """Get a static message from cache or generate it."""
    if key not in _STATIC_MESSAGES:
        _STATIC_MESSAGES[key] = generator()
    return _STATIC_MESSAGES[key]


def split_text(text: str, max_len: int) -> list[str]:
    """Split text into chunks at word boundaries."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind(" ", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    return chunks


def format_halacha_messages(
    halacha: Halacha, number: int, date_str: str = ""
) -> list[str]:
    """Format a halacha into messages (Hebrew only)."""
    label = "א" if number == 1 else "ב"
    emoji = "📜" if number == 1 else "📖"
    if halacha.seif is not None:
        ref_display = f"סימן {halacha.siman} סעיף {halacha.seif}"
    else:
        ref_display = f"סימן {halacha.siman}"
    title = f'{emoji} <a href="{halacha.sefaria_url}"><b>{label}. {halacha.volume.volume_he} — {ref_display}</b></a>'
    link = f'<a href="{halacha.sefaria_url}">המשך בספריא →</a>'

    header = f"<b>📚 שולחן ערוך יומי</b> | {date_str}\n\n" if date_str else ""
    base = f"{header}{title}\n\n"
    footer = f"\n\n{link}"

    available = MAX_MESSAGE_LENGTH - len(base) - len(footer) - 100
    hebrew_chunks = split_text(halacha.hebrew_text, available)

    messages = []
    for i, chunk in enumerate(hebrew_chunks):
        msg = f"{base}{chunk}" if i == 0 else f"{title} (המשך)\n\n{chunk}"
        if i == len(hebrew_chunks) - 1:
            msg += footer
        messages.append(msg)

    return messages


def format_daily_message(pair: DailyPair, for_date: date | None = None) -> list[str]:
    """Format daily message as list of messages."""
    if for_date is None:
        for_date = date.today()
    date_str = for_date.strftime("%d/%m/%Y")

    messages = []
    messages.extend(format_halacha_messages(pair.first, 1, date_str))
    messages.extend(format_halacha_messages(pair.second, 2, ""))
    return messages


def format_welcome_message() -> str:
    """Get welcome message."""

    def _generate() -> str:
        return """<b>📚 שולחן ערוך יומי</b>

ברוכים הבאים! כל יום שתי הלכות חדשות מהשולחן ערוך.
🔊 כולל הקראה קולית בעברית — ניתן להאזין ב-1x, 1.5x או 2x.

✅ נרשמת אוטומטית לקבלת הלכות יומיות.
לביטול הרשמה: /unsubscribe"""

    return _get_static_message("welcome", _generate)


def format_info_message() -> str:
    """Get combined info message."""

    def _generate() -> str:
        return """<b>📚 שולחן ערוך יומי</b>

<b>שולחן ערוך</b> הוא ספר ההלכה המרכזי שחיבר רבי יוסף קארו. הספר מחולק לארבעה חלקים: אורח חיים, יורה דעה, אבן העזר, וחושן משפט.

<b>פקודות:</b>
/today - הלכות היום + הקראה קולית
/subscribe - הרשמה להלכות יומיות
/unsubscribe - ביטול הרשמה
/info - מידע ועזרה

🔊 כל הלכה מלווה בהקראה קולית בעברית. ניתן להאזין ב-1x, 1.5x או 2x.

📚 <a href="https://www.sefaria.org/Shulchan_Arukh">קרא בספריא</a>
💻 <a href="https://github.com/naorbrown/shulchan-aruch-yomi">קוד פתוח</a>"""

    return _get_static_message("info", _generate)


def format_error_message() -> str:
    """Get error message."""

    def _generate() -> str:
        return "לא הצלחתי לטעון את ההלכות. נסה שוב בעוד כמה דקות."

    return _get_static_message("error", _generate)
