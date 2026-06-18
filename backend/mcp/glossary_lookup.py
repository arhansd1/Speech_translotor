# mcp/glossary_lookup.py
# MCP Tool 3: Glossary lookup for domain-specific terms.
# Currently uses an in-memory dict. Qdrant vector search replaces this later —
# the interface (lookup_term function) stays identical, only the backend changes.
#
# The agent calls this when it spots a term in the translated text that might
# be a technical, medical, or legal term needing precise handling.

from typing import Optional

# Domain glossary: English term → definition + preferred translation hints per language
# Format: { "term": { "definition": str, "domain": str, "hints": { lang_code: preferred_translation } } }
GLOSSARY: dict[str, dict] = {
    # Medical
    "hypertension": {
        "definition": "Persistently elevated blood pressure above 140/90 mmHg",
        "domain": "medical",
        "hints": {
            "hi-IN": "उच्च रक्तचाप (ucch raktachaap)",
            "ta-IN": "உயர் இரத்த அழுத்தம் (uyar iratta azhuttam)",
            "te-IN": "అధిక రక్తపోటు (adhika raktapotu)",
        },
    },
    "diabetes": {
        "definition": "Chronic condition affecting blood sugar regulation",
        "domain": "medical",
        "hints": {
            "hi-IN": "मधुमेह (madhumeh)",
            "ta-IN": "நீரிழிவு நோய் (neeriziivu noi)",
        },
    },
    # Legal
    "affidavit": {
        "definition": "A written sworn statement of fact used as evidence in court",
        "domain": "legal",
        "hints": {
            "hi-IN": "शपथ पत्र (shapath patra)",
            "ta-IN": "உறுதிமொழி (urutimozhi)",
        },
    },
    "injunction": {
        "definition": "A court order requiring someone to do or stop doing something",
        "domain": "legal",
        "hints": {
            "hi-IN": "निषेधाज्ञा (nishedhagya)",
        },
    },
    # Technology
    "algorithm": {
        "definition": "A step-by-step procedure for solving a problem or achieving a goal",
        "domain": "technology",
        "hints": {
            "hi-IN": "एल्गोरिदम (algorithm)",  # Loan word — keep as-is
            "ta-IN": "வழிமுறை (vazimuRai)",
        },
    },
    "machine learning": {
        "definition": "AI technique where systems learn from data without explicit programming",
        "domain": "technology",
        "hints": {
            "hi-IN": "मशीन लर्निंग (machine learning)",
            "ta-IN": "இயந்திர கற்றல் (iyanthira kaRRal)",
        },
    },
    # Finance
    "mutual fund": {
        "definition": "A pooled investment vehicle managed by professionals",
        "domain": "finance",
        "hints": {
            "hi-IN": "म्युचुअल फंड (mutual fund)",
            "ta-IN": "பரஸ்பர நிதி (paraspar nithi)",
        },
    },
}


def lookup_term(
    term: str,
    target_language_code: Optional[str] = None,
) -> dict:
    """
    Look up a term in the glossary.
    Returns the entry if found, or {"found": False} if not.
    The agent uses the returned hints to verify/improve the translation.

    Args:
        term: The English term to look up (case-insensitive)
        target_language_code: If provided, include the preferred translation hint
                              for that language (e.g. "hi-IN")
    """
    normalized = term.lower().strip()
    entry = GLOSSARY.get(normalized)

    if not entry:
        # Try partial match — "hypertension" should match if input is "Hypertension."
        for key, val in GLOSSARY.items():
            if normalized in key or key in normalized:
                entry = val
                break

    if not entry:
        return {"found": False, "term": term}

    result = {
        "found": True,
        "term": term,
        "definition": entry["definition"],
        "domain": entry["domain"],
    }

    if target_language_code and target_language_code in entry.get("hints", {}):
        result["preferred_translation"] = entry["hints"][target_language_code]

    return result


def list_domains() -> list[str]:
    """Returns all domains present in the glossary."""
    return list({entry["domain"] for entry in GLOSSARY.values()})
