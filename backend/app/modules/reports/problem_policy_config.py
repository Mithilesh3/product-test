from __future__ import annotations

import json
import logging
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "problem_policy_rules.json"


def _safe_token_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    tokens: List[str] = []
    for item in value:
        token = str(item or "").strip().lower()
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def _safe_category(value: Any) -> str:
    return str(value or "").strip().lower()


@lru_cache(maxsize=1)
def _load_overrides() -> Dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}

    try:
        payload = json.loads(_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.warning("Problem policy config load failed (%s): %s", _CONFIG_PATH, exc)
        return {}

    if not isinstance(payload, dict):
        logger.warning("Problem policy config must be a JSON object: %s", _CONFIG_PATH)
        return {}
    return payload


def merge_category_fields(
    *,
    defaults: Dict[str, Dict[str, List[str]]],
    config_key: str,
    fields: Iterable[str],
) -> Dict[str, Dict[str, List[str]]]:
    merged: Dict[str, Dict[str, List[str]]] = {}
    field_names = [str(field) for field in fields]

    for category, value in defaults.items():
        cat = _safe_category(category)
        if not cat or not isinstance(value, dict):
            continue
        merged[cat] = {field: _safe_token_list(value.get(field)) for field in field_names}

    overrides = _load_overrides().get(config_key)
    if isinstance(overrides, dict):
        for category, value in overrides.items():
            cat = _safe_category(category)
            if not cat or not isinstance(value, dict):
                continue
            current = deepcopy(merged.get(cat, {field: [] for field in field_names}))
            for field in field_names:
                if field in value:
                    current[field] = _safe_token_list(value.get(field))
                elif field not in current:
                    current[field] = []
            merged[cat] = current

    if "general" not in merged:
        merged["general"] = {field: [] for field in field_names}
    return merged


def merge_token_map(
    *,
    defaults: Dict[str, List[str]],
    config_key: str,
) -> Dict[str, List[str]]:
    merged: Dict[str, List[str]] = {}
    for category, value in defaults.items():
        cat = _safe_category(category)
        if not cat:
            continue
        merged[cat] = _safe_token_list(value)

    overrides = _load_overrides().get(config_key)
    if isinstance(overrides, dict):
        for category, value in overrides.items():
            cat = _safe_category(category)
            if not cat:
                continue
            merged[cat] = _safe_token_list(value)

    if "general" not in merged:
        merged["general"] = []
    return merged


def merge_token_list(*, defaults: List[str], config_key: str) -> List[str]:
    merged = _safe_token_list(defaults)
    override_value = _load_overrides().get(config_key)
    if isinstance(override_value, list):
        override_tokens = _safe_token_list(override_value)
        if override_tokens:
            return override_tokens
    return merged


def merge_priority_list(
    *,
    defaults: List[str],
    config_key: str,
    known_categories: Iterable[str],
) -> List[str]:
    known = [_safe_category(category) for category in known_categories if _safe_category(category)]
    merged: List[str] = []

    override_value = _load_overrides().get(config_key)
    if isinstance(override_value, list):
        for item in override_value:
            category = _safe_category(item)
            if category and category in known and category not in merged:
                merged.append(category)

    for item in defaults:
        category = _safe_category(item)
        if category and category not in merged:
            merged.append(category)

    for category in known:
        if category not in merged:
            merged.append(category)

    return merged


def get_problem_policy_config_path() -> Path:
    return _CONFIG_PATH
