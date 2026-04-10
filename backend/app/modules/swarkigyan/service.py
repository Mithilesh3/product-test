import logging
import re
from typing import Literal

from app.core.llm_config import DEPLOYMENT_NAME, azure_client, build_token_param
from app.modules.swarkigyan.prompt import SWAR_RISHI_SYSTEM_PROMPT
from app.modules.swarkigyan.schemas import SwarChatRequest
from app.modules.numerology.knowledge_store import get_swar_prompt_notes, merge_swar_tones
from app.modules.numerology.number_profiles import SWAR_TONES

logger = logging.getLogger(__name__)

SupportedLanguage = Literal["hindi", "english", "hinglish"]

OUT_OF_SCOPE_REPLY = "This is outside Swarkigyan scope."
SAFE_FALLBACK = {
    "english": "My child, for this, it would be best to consult a qualified professional.",
    "hindi": "बेटा/बेटी, इस चीज़ के लिए किसी योग्य विशेषज्ञ से सलाह लेना बेहतर होगा।",
    "hinglish": "Beta/Beti, is cheez ke liye kisi qualified professional se salah lena behtar hoga.",
}

_SCOPE_KEYWORDS = [
    "swar",
    "swara",
    "swarkigyan",
    "swarvigyan",
    "ida",
    "pingala",
    "sushumna",
    "nostril",
    "left nostril",
    "right nostril",
    "breath awareness",
    "nadi",
    "स्वर",
    "स्वर विज्ञान",
    "इड़ा",
    "पिंगला",
    "सुषुम्ना",
    "नाड़ी",
    "नासिका",
    "श्वास",
]

_UNSAFE_KEYWORDS = [
    "disease",
    "diagnose",
    "diagnosis",
    "treatment",
    "cure",
    "medicine",
    "therapy",
    "doctor",
    "breathing problem",
    "asthma",
    "heart problem",
    "legal",
    "lawyer",
    "court",
    "investment",
    "stock",
    "crypto",
    "financial",
    "loan",
    "इलाज",
    "दवा",
    "डॉक्टर",
    "बीमारी",
    "निवेश",
    "कानूनी",
    "वकील",
]

_ABUSIVE_KEYWORDS = [
    "madarchod",
    "mc",
    "bc",
    "bhenchod",
    "behenchod",
    "chutiya",
    "chutia",
    "gandu",
    "randi",
    "lund",
    "lavde",
    "bhosdi",
    "bhosdike",
    "harami",
    "fuck",
    "fucking",
    "shit",
    "bitch",
    "asshole",
    "idiot",
    "stupid bot",
    "bhosdi wale",
    "bhosdiwale",
    "\u092d\u094b\u0938\u0921\u093c\u0940 \u0935\u093e\u0932\u0947",
    "\u092d\u094b\u0938\u0921\u093c\u0940\u0935\u093e\u0932\u0947",
    "मादरचोद",
    "बहनचोद",
    "चूतिया",
    "गांडू",
    "भोसड़ी",
    "भोसडी",
    "हरामी",
    "साला",
]

_GREETING_KEYWORDS = [
    "hi",
    "hello",
    "hey",
    "namaste",
    "नमस्ते",
    "राम राम",
]

_DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")


def detect_language(message: str, preference: str | None) -> SupportedLanguage:
    if preference == "hindi":
        return "hindi"
    if preference == "english":
        return "english"
    if preference == "hinglish":
        return "hinglish"

    text = message.strip()
    has_devanagari = bool(_DEVANAGARI_PATTERN.search(text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    if has_devanagari and has_latin:
        return "hinglish"
    if has_devanagari:
        return "hindi"
    return "english"


def is_unsafe(message: str) -> bool:
    lower = message.lower()
    return any(term in lower for term in _UNSAFE_KEYWORDS)


def is_scope_related(message: str) -> bool:
    lower = message.lower()
    if any(term in lower for term in _GREETING_KEYWORDS):
        return True
    return any(term in lower for term in _SCOPE_KEYWORDS)


def contains_abusive_language(message: str) -> bool:
    raw = (message or "").lower()
    normalized = re.sub(r"\s+", " ", raw).strip()
    compact = re.sub(r"[^a-z0-9\u0900-\u097f]+", "", raw)

    for term in _ABUSIVE_KEYWORDS:
        escaped_term = re.escape(term)
        if re.search(rf"(^|[\s\W]){escaped_term}($|[\s\W])", normalized):
            return True

        compact_term = re.sub(r"[^a-z0-9\u0900-\u097f]+", "", term)
        if compact_term and compact_term in compact:
            return True

    return False


def _language_instruction(language: SupportedLanguage) -> str:
    if language == "hindi":
        return "Respond in respectful simple Hindi only."
    if language == "hinglish":
        return "Respond in natural simple Hinglish only."
    return "Respond in warm simple English only."


def _build_swar_knowledge_context() -> str:
    notes = get_swar_prompt_notes()
    tones = merge_swar_tones(SWAR_TONES)
    lines: list[str] = []
    if notes:
        trimmed = notes[:8]
        lines.append("Deterministic Swar guidance notes:")
        lines.extend(f"- {note}" for note in trimmed)
    if tones:
        lines.append("Swara tone map (vowel: tone - quality):")
        for key in sorted(tones.keys())[:8]:
            tone = tones[key]
            tone_name = str(tone.get("tone") or "").strip()
            quality = str(tone.get("quality") or "").strip()
            if tone_name or quality:
                lines.append(f"- {key}: {tone_name} - {quality}".strip(" -"))
    return "\n".join(lines).strip()


def _build_messages(payload: SwarChatRequest, language: SupportedLanguage) -> list[dict[str, str]]:
    knowledge_context = _build_swar_knowledge_context()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SWAR_RISHI_SYSTEM_PROMPT},
        *([{"role": "system", "content": knowledge_context}] if knowledge_context else []),
        {"role": "system", "content": _language_instruction(language)},
    ]

    # Keep short context window to control tokens and preserve recent flow.
    for item in payload.history[-8:]:
        messages.append({"role": item.role, "content": item.content})

    messages.append({"role": "user", "content": payload.message})
    return messages


def generate_swarkigyan_reply(payload: SwarChatRequest) -> tuple[str, SupportedLanguage, bool]:
    language = detect_language(payload.message, payload.language_preference)

    if is_unsafe(payload.message):
        return SAFE_FALLBACK[language], language, True

    if not is_scope_related(payload.message):
        return OUT_OF_SCOPE_REPLY, language, True

    try:
        response = azure_client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=_build_messages(payload, language),
            temperature=0.3,
            **build_token_param(350),
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            content = {
                "english": "Please share a clearer Swar Vigyan question.",
                "hindi": "कृपया स्वर विज्ञान से जुड़ा प्रश्न थोड़ा स्पष्ट लिखें।",
                "hinglish": "Kripya Swar Vigyan wala question thoda aur clear likhiye.",
            }[language]
        return content, language, False
    except Exception:
        logger.exception("Swarkigyan Azure chat failed")
        fallback = {
            "english": "I could not process this right now. Please try again in a moment.",
            "hindi": "अभी उत्तर तैयार नहीं हो पाया। कृपया थोड़ी देर बाद फिर पूछें।",
            "hinglish": "Abhi response generate nahi ho paya. Kripya thodi der baad phir poochiye.",
        }[language]
        return fallback, language, True
