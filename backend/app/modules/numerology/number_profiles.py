from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.modules.numerology.knowledge_store import (
    get_number_profile_override,
    merge_profile,
    merge_swar_tones,
)


NUMBER_PROFILE_MAP: Dict[int, Dict[str, Any]] = {
    1: {
        "planet": "Sun",
        "element": "Fire",
        "qualities": ["leadership", "clarity", "authority"],
        "day": "Sunday",
        "direction": "East",
        "colors": ["Gold", "Orange"],
        "gemstone": "Ruby",
        "mantra": "Om Hraam Hreem Hraum Suryaya Namah",
    },
    2: {
        "planet": "Moon",
        "element": "Water",
        "qualities": ["sensitivity", "intuition", "balance"],
        "day": "Monday",
        "direction": "North-West",
        "colors": ["White", "Silver"],
        "gemstone": "Pearl",
        "mantra": "Om Som Somaya Namah",
    },
    3: {
        "planet": "Jupiter",
        "element": "Air",
        "qualities": ["wisdom", "expansion", "optimism"],
        "day": "Thursday",
        "direction": "North-East",
        "colors": ["Yellow"],
        "gemstone": "Yellow Sapphire",
        "mantra": "Om Brim Brihaspataye Namah",
    },
    4: {
        "planet": "Rahu",
        "element": "Earth",
        "qualities": ["structure", "discipline", "material focus"],
        "day": "Saturday",
        "direction": "South-West",
        "colors": ["Smoky Blue", "Grey"],
        "gemstone": "Hessonite",
        "mantra": "Om Raam Rahave Namah",
    },
    5: {
        "planet": "Mercury",
        "element": "Air",
        "qualities": ["communication", "intellect", "adaptability"],
        "day": "Wednesday",
        "direction": "North",
        "colors": ["Green"],
        "gemstone": "Emerald",
        "mantra": "Om Bum Budhaya Namah",
    },
    6: {
        "planet": "Venus",
        "element": "Water",
        "qualities": ["harmony", "beauty", "responsibility"],
        "day": "Friday",
        "direction": "West",
        "colors": ["Pink", "Cream"],
        "gemstone": "Diamond",
        "mantra": "Om Shum Shukraya Namah",
    },
    7: {
        "planet": "Ketu",
        "element": "Fire",
        "qualities": ["insight", "spiritual depth", "detachment"],
        "day": "Tuesday",
        "direction": "South-East",
        "colors": ["Smoky White", "Aqua"],
        "gemstone": "Cat's Eye",
        "mantra": "Om Kem Ketave Namah",
    },
    8: {
        "planet": "Saturn",
        "element": "Earth",
        "qualities": ["discipline", "authority", "endurance"],
        "day": "Saturday",
        "direction": "South",
        "colors": ["Navy", "Indigo", "Black"],
        "gemstone": "Blue Sapphire",
        "mantra": "Om Sham Shanicharaya Namah",
    },
    9: {
        "planet": "Mars",
        "element": "Fire",
        "qualities": ["action", "courage", "drive"],
        "day": "Tuesday",
        "direction": "East",
        "colors": ["Red", "Maroon"],
        "gemstone": "Red Coral",
        "mantra": "Om Kraam Kreem Kraum Bhaumaya Namah",
    },
}


SWAR_TONES: Dict[str, Dict[str, str]] = {
    "a": {"tone": "initiation", "quality": "drive and leadership"},
    "e": {"tone": "clarity", "quality": "analysis and communication"},
    "i": {"tone": "focus", "quality": "precision and intent"},
    "o": {"tone": "connection", "quality": "emotion and bonding"},
    "u": {"tone": "stability", "quality": "grounding and patience"},
    "y": {"tone": "insight", "quality": "reflection and inner voice"},
}


def number_profile(number: int) -> Dict[str, Any]:
    if not isinstance(number, int) or number <= 0:
        return {}
    profile = NUMBER_PROFILE_MAP.get(number)
    if not profile:
        return {}
    override = get_number_profile_override(number)
    merged = merge_profile(profile, override)
    return {"number": number, **merged}


def build_number_profiles(numbers: Dict[str, Any]) -> Dict[str, Any]:
    profiles: Dict[str, Any] = {}
    for key, value in (numbers or {}).items():
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number <= 0:
            continue
        profiles[key] = number_profile(number)
    return profiles


def dominant_planet_profile(numbers: List[int]) -> Dict[str, Any]:
    for value in numbers:
        if isinstance(value, int) and value > 0:
            profile = number_profile(value)
            if profile:
                return profile
    return number_profile(5)


def swar_profile(name: str) -> Dict[str, Any]:
    cleaned = "".join(ch.lower() for ch in str(name or "") if ch.isalpha())
    if not cleaned:
        return {}
    tones = merge_swar_tones(SWAR_TONES)
    vowels = [ch for ch in cleaned if ch in tones]
    if not vowels:
        return {}
    counts: Dict[str, int] = {}
    for ch in vowels:
        counts[ch] = counts.get(ch, 0) + 1
    dominant = max(counts.items(), key=lambda item: item[1])[0]
    tone = tones.get(dominant, {})
    return {
        "vowelCounts": counts,
        "dominantVowel": dominant,
        "dominantTone": tone.get("tone"),
        "dominantQuality": tone.get("quality"),
    }


def build_guidance_profile(primary_number: int, supportive_numbers: Optional[List[int]] = None) -> Dict[str, Any]:
    base = number_profile(primary_number) if isinstance(primary_number, int) else {}
    supported = [int(value) for value in (supportive_numbers or []) if isinstance(value, int) and 1 <= value <= 9]
    supported = supported or ([primary_number] if isinstance(primary_number, int) and primary_number > 0 else [])
    caution = [value for value in range(1, 10) if value not in set(supported)]
    return {
        "primaryNumber": primary_number,
        "supportiveNumbers": supported,
        "cautionNumbers": caution,
        "planet": base.get("planet"),
        "element": base.get("element"),
        "direction": base.get("direction"),
        "day": base.get("day"),
        "colors": base.get("colors"),
        "gemstone": base.get("gemstone"),
        "mantra": base.get("mantra"),
        "qualities": base.get("qualities"),
    }
