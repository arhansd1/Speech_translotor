# sarvam/languages.py
# Single source of truth for every language the app handles.
# Sarvam STT+Translate supports all 22 scheduled Indian languages.
# Bulbul v2 TTS supports 11 of those (10 Indian + English).
# The frontend uses this via the /languages endpoint to build its dropdown.

from dataclasses import dataclass
from typing import Optional


@dataclass
class Language:
    code: str           # BCP-47 code Sarvam API expects (e.g. "hi-IN")
    name: str           # Human-readable display name
    script: str         # Unicode script name (for UI tooltip)
    tts_supported: bool # Whether Bulbul v2 can speak this language
    tts_speaker: Optional[str] = None  # Default speaker ID for Bulbul v2


# All 22 constitutionally scheduled Indian languages + English
# Ordered by speaker population (largest first) so dropdown feels natural
LANGUAGES: list[Language] = [
    Language("hi-IN", "Hindi",      "Devanagari", tts_supported=True,  tts_speaker="anushka"),
    Language("bn-IN", "Bengali",    "Bengali",    tts_supported=True,  tts_speaker="manisha"),
    Language("te-IN", "Telugu",     "Telugu",     tts_supported=True,  tts_speaker="arya"),
    Language("mr-IN", "Marathi",    "Devanagari", tts_supported=True,  tts_speaker="vidya"),
    Language("ta-IN", "Tamil",      "Tamil",      tts_supported=True,  tts_speaker="anushka"),
    Language("gu-IN", "Gujarati",   "Gujarati",   tts_supported=True,  tts_speaker="manisha"),
    Language("kn-IN", "Kannada",    "Kannada",    tts_supported=True,  tts_speaker="arya"),
    Language("ml-IN", "Malayalam",  "Malayalam",  tts_supported=True,  tts_speaker="vidya"),
    Language("pa-IN", "Punjabi",    "Gurmukhi",   tts_supported=True,  tts_speaker="anushka"),
    Language("od-IN", "Odia",       "Odia",       tts_supported=True,  tts_speaker="manisha"),
    Language("ur-IN", "Urdu",       "Nastaliq",   tts_supported=False),
    Language("as-IN", "Assamese",   "Bengali",    tts_supported=False),
    Language("mai-IN","Maithili",   "Devanagari", tts_supported=False),
    Language("sat-IN","Santali",    "Ol Chiki",   tts_supported=False),
    Language("ks-IN", "Kashmiri",   "Nastaliq",   tts_supported=False),
    Language("ne-IN", "Nepali",     "Devanagari", tts_supported=False),
    Language("sd-IN", "Sindhi",     "Devanagari", tts_supported=False),
    Language("doi-IN","Dogri",      "Devanagari", tts_supported=False),
    Language("kok-IN","Konkani",    "Devanagari", tts_supported=False),
    Language("mni-IN","Manipuri",   "Meitei",     tts_supported=False),
    Language("brx-IN","Bodo",       "Devanagari", tts_supported=False),
    Language("sa-IN", "Sanskrit",   "Devanagari", tts_supported=False),
    Language("en-IN", "English",    "Latin",      tts_supported=True,  tts_speaker="hitesh"),
]

# Quick lookups used by the Sarvam client
LANGUAGE_BY_CODE: dict[str, Language] = {lang.code: lang for lang in LANGUAGES}

def get_language(code: str) -> Optional[Language]:
    return LANGUAGE_BY_CODE.get(code)

def tts_supported(code: str) -> bool:
    lang = get_language(code)
    return lang.tts_supported if lang else False

def get_speaker(code: str) -> str:
    lang = get_language(code)
    if lang and lang.tts_speaker:
        return lang.tts_speaker
    return "anushka"  # safe fallback

def languages_as_dict() -> list[dict]:
    """Serializable list for the /languages API endpoint."""
    return [
        {
            "code": lang.code,
            "name": lang.name,
            "script": lang.script,
            "tts_supported": lang.tts_supported,
        }
        for lang in LANGUAGES
    ]