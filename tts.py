"""
tts.py — turns advisory text into spoken audio in the farmer's chosen language.

Uses gTTS (the free Google Translate TTS endpoint) because it needs no extra
API key or billing setup beyond internet access — a good fit for a project
that already leans on free tiers for a live demo.

For production you'd likely want to swap this for something with an SLA and
better Indian-language coverage/voice quality — Google Cloud Text-to-Speech,
or an India-specific option like Bhashini / AI4Bharat's TTS models. The rest
of app.py doesn't need to change if you do that — just replace the body of
text_to_speech_bytes() below and keep the same signature.

Install: pip install gTTS

NOTE ON LANGUAGE CODES: translations.py wasn't part of what I could see, so
LANGUAGE_TO_GTTS_CODE below is a best-guess map of common Indian-language
names to gTTS codes. Check it against your actual LANGUAGES list in
translations.py and adjust the keys if any names differ (e.g. if you use
"Hinglish" or a script-specific label) — anything not found falls back to Hindi.
"""

from io import BytesIO
from gtts import gTTS

LANGUAGE_TO_GTTS_CODE = {
    "Hindi": "hi",
    "English": "en",
    "Punjabi": "pa",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Odia": "or",
    "Oriya": "or",
}


def get_gtts_lang_code(language_name: str) -> str:
    """Maps a language name from translations.LANGUAGES to a gTTS language code."""
    return LANGUAGE_TO_GTTS_CODE.get(language_name, "hi")


def text_to_speech_bytes(text: str, language_name: str) -> bytes:
    """
    Returns MP3 bytes of `text` spoken in the given language.
    Raises on network failure — callers should catch this and show a
    friendly message rather than letting the tab crash.
    """
    lang_code = get_gtts_lang_code(language_name)
    tts = gTTS(text=text, lang=lang_code)
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()
