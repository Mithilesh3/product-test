from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "knowledge_overrides.json"

_cache_payload: Dict[str, Any] | None = None
_cache_mtime: float | None = None


def _load_payload() -> Dict[str, Any]:
    global _cache_payload, _cache_mtime
    if not _CONFIG_PATH.exists():
        _cache_payload = {}
        _cache_mtime = None
        return {}
    try:
        mtime = _CONFIG_PATH.stat().st_mtime
    except OSError:
        return _cache_payload or {}
    if _cache_payload is not None and _cache_mtime == mtime:
        return _cache_payload
    try:
        payload = json.loads(_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.warning("Failed to load knowledge overrides: %s", exc)
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    _cache_payload = payload
    _cache_mtime = mtime
    return payload


def save_payload(payload: Dict[str, Any]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    global _cache_payload, _cache_mtime
    _cache_payload = payload
    try:
        _cache_mtime = _CONFIG_PATH.stat().st_mtime
    except OSError:
        _cache_mtime = None


def get_prompt_notes() -> List[str]:
    payload = _load_payload()
    notes = payload.get("promptNotes")
    if isinstance(notes, list):
        return [str(note).strip() for note in notes if str(note).strip()]
    return []


def get_swar_prompt_notes() -> List[str]:
    payload = _load_payload()
    notes = payload.get("swarPromptNotes")
    if isinstance(notes, list):
        return [str(note).strip() for note in notes if str(note).strip()]
    return []


def get_number_profile_override(number: int) -> Dict[str, Any]:
    if not isinstance(number, int) or number <= 0:
        return {}
    payload = _load_payload()
    overrides = payload.get("numberProfiles") or {}
    if isinstance(overrides, dict):
        entry = overrides.get(str(number)) or overrides.get(number)
        if isinstance(entry, dict):
            return entry
    return {}


def get_swar_overrides() -> Dict[str, Dict[str, str]]:
    payload = _load_payload()
    overrides = payload.get("swarTones")
    if isinstance(overrides, dict):
        sanitized: Dict[str, Dict[str, str]] = {}
        for key, value in overrides.items():
            if not isinstance(value, dict):
                continue
            token = str(key or "").strip().lower()
            if not token:
                continue
            sanitized[token] = {
                "tone": str(value.get("tone") or "").strip(),
                "quality": str(value.get("quality") or "").strip(),
            }
        return sanitized
    return {}


def merge_profile(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    if not override:
        return base
    merged = deepcopy(base)
    for key, value in override.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, list):
            existing = merged.get(key)
            if isinstance(existing, list):
                for item in value:
                    if item not in existing:
                        existing.append(item)
                merged[key] = existing
            else:
                merged[key] = value
        elif isinstance(value, dict):
            existing = merged.get(key)
            if isinstance(existing, dict):
                existing.update({k: v for k, v in value.items() if v not in (None, "", [], {})})
                merged[key] = existing
            else:
                merged[key] = value
        else:
            merged[key] = value
    return merged


def merge_swar_tones(base: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    overrides = get_swar_overrides()
    if not overrides:
        return base
    merged = deepcopy(base)
    for key, value in overrides.items():
        if not value:
            continue
        existing = merged.get(key, {})
        updated = {**existing, **{k: v for k, v in value.items() if v}}
        merged[key] = updated
    return merged


def append_prompt_notes(notes: List[str]) -> None:
    payload = _load_payload()
    existing = payload.get("promptNotes") if isinstance(payload.get("promptNotes"), list) else []
    updated = list(existing)
    for note in notes:
        clean = str(note or "").strip()
        if clean and clean not in updated:
            updated.append(clean)
    payload["promptNotes"] = updated
    save_payload(payload)


def append_swar_prompt_notes(notes: List[str]) -> None:
    payload = _load_payload()
    existing = payload.get("swarPromptNotes") if isinstance(payload.get("swarPromptNotes"), list) else []
    updated = list(existing)
    for note in notes:
        clean = str(note or "").strip()
        if clean and clean not in updated:
            updated.append(clean)
    payload["swarPromptNotes"] = updated
    save_payload(payload)


def merge_number_profiles(overrides: Dict[str, Any]) -> None:
    payload = _load_payload()
    existing = payload.get("numberProfiles")
    if not isinstance(existing, dict):
        existing = {}
    for key, value in (overrides or {}).items():
        if not isinstance(value, dict):
            continue
        existing[str(key)] = value
    payload["numberProfiles"] = existing
    save_payload(payload)


def merge_swar_overrides(overrides: Dict[str, Any]) -> None:
    payload = _load_payload()
    existing = payload.get("swarTones")
    if not isinstance(existing, dict):
        existing = {}
    for key, value in (overrides or {}).items():
        if not isinstance(value, dict):
            continue
        existing[str(key)] = value
    payload["swarTones"] = existing
    save_payload(payload)


def update_from_extraction(extracted: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(extracted, dict):
        return {}
    applied = {
        "promptNotes": 0,
        "numberProfiles": 0,
        "swarTones": 0,
        "swarPromptNotes": 0,
    }

    prompt_notes = extracted.get("promptNotes")
    if isinstance(prompt_notes, list):
        append_prompt_notes(prompt_notes)
        applied["promptNotes"] = len(prompt_notes)

    number_profiles = extracted.get("numberProfiles")
    if isinstance(number_profiles, dict):
        merge_number_profiles(number_profiles)
        applied["numberProfiles"] = len(number_profiles)

    swar_tones = extracted.get("swarTones")
    if isinstance(swar_tones, dict):
        merge_swar_overrides(swar_tones)
        applied["swarTones"] = len(swar_tones)

    swar_prompt_notes = extracted.get("swarPromptNotes")
    if isinstance(swar_prompt_notes, list):
        append_swar_prompt_notes(swar_prompt_notes)
        applied["swarPromptNotes"] = len(swar_prompt_notes)

    return applied
