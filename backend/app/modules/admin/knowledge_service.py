from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pypdf import PdfReader

from app.core.config import settings
from app.core.llm_config import azure_client, build_token_param
from app.db.session import SessionLocal
from app.db.models import KnowledgeAsset
from app.modules.numerology.knowledge_store import update_from_extraction

logger = logging.getLogger(__name__)


def _storage_root() -> Path:
    root = Path(getattr(settings, "KNOWLEDGE_ASSET_STORAGE_PATH", "") or "storage/admin_knowledge")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_read_upload(upload, target_path: Path) -> int:
    size = 0
    with target_path.open("wb") as out:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            out.write(chunk)
    return size


def save_uploaded_asset(upload, file_name: str) -> Tuple[str, int]:
    root = _storage_root()
    target_path = root / file_name
    size = _safe_read_upload(upload, target_path)
    return str(target_path), size


def _extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    chunks = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _extract_audio_text(file_path: str, language: Optional[str] = None) -> str:
    deployment = getattr(settings, "AZURE_OPENAI_AUDIO_DEPLOYMENT", "") or ""
    if not deployment:
        return ""

    with open(file_path, "rb") as audio_file:
        try:
            response = azure_client.audio.transcriptions.create(
                model=deployment,
                file=audio_file,
                language=language or None,
            )
        except Exception as exc:
            logger.warning("Audio transcription failed: %s", exc)
            return ""

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    if isinstance(response, dict):
        return str(response.get("text") or "").strip()
    return ""


def _clean_json_response(raw: str) -> Dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}
    return {}


def extract_deterministic_updates(
    text: str,
    language: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    if not text:
        return {}
    snippet = text[:12000]
    resolved_domain = (domain or "").strip().lower() or "numerology"
    if resolved_domain not in {"numerology", "swar_vigyan"}:
        resolved_domain = "numerology"

    if resolved_domain == "swar_vigyan":
        system_prompt = (
            "You are a deterministic Swar Vigyan knowledge extractor. "
            "Read the content and return JSON only with curated swara guidance updates. "
            "No prose outside JSON."
        )
        user_prompt = {
            "task": "Extract structured swara knowledge updates to enrich Swar Vigyan guidance.",
            "language": language or "unspecified",
            "output_schema": {
                "swarPromptNotes": ["short directive for swara guidance tone or logic"],
                "swarTones": {
                    "a": {"tone": "initiation", "quality": "drive and leadership"},
                    "i": {"tone": "focus", "quality": "precision and intent"}
                }
            },
            "rules": [
                "Only include updates explicitly supported by the content.",
                "Keep short arrays (max 5 items).",
                "Do not include numerology number meanings or planets unless the content links them to swara.",
                "Focus on swara, nostril flow, timing, and safe guidance phrasing.",
            ],
            "content": snippet,
        }
    else:
        system_prompt = (
            "You are a deterministic numerology knowledge extractor. "
            "Read the content and return JSON only with curated rule updates. "
            "No prose outside JSON."
        )
        user_prompt = {
            "task": "Extract structured rule updates that can enrich deterministic numerology.",
            "language": language or "unspecified",
            "output_schema": {
                "promptNotes": ["short directive for report tone or logic"],
                "numberProfiles": {
                    "1": {
                        "qualities": ["..."],
                        "colors": ["..."],
                        "direction": "East",
                        "day": "Sunday",
                        "planet": "Sun",
                        "element": "Fire",
                        "gemstone": "Ruby",
                        "mantra": "..."
                    }
                },
                "swarTones": {
                    "a": {"tone": "initiation", "quality": "drive and leadership"}
                }
            },
            "rules": [
                "Only include updates explicitly supported by the content.",
                "Keep short arrays (max 5 items).",
                "Do not hallucinate planets or mantras not present in the content.",
            ],
            "content": snippet,
        }

    response = azure_client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        temperature=0.2,
        **build_token_param(900),
    )
    content = response.choices[0].message.content
    return _clean_json_response(content)


def _merge_manual_notes(updates: Dict[str, Any], manual_notes: Optional[list], domain: Optional[str]) -> Dict[str, Any]:
    if not manual_notes:
        return updates
    cleaned = [str(note).strip() for note in manual_notes if str(note).strip()]
    if not cleaned:
        return updates
    merged = dict(updates or {})
    target_key = "swarPromptNotes" if (domain or "").lower() == "swar_vigyan" else "promptNotes"
    existing = merged.get(target_key)
    if not isinstance(existing, list):
        existing = []
    for note in cleaned:
        if note not in existing:
            existing.append(note)
    merged[target_key] = existing
    return merged


def process_knowledge_asset(asset_id: int) -> None:
    with SessionLocal() as db:
        asset = db.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
        if not asset:
            return
        asset.status = "processing"
        db.commit()

    extracted_text = ""
    transcript_text = ""
    failure_reason = ""

    try:
        if asset.source_type == "pdf" and asset.file_path:
            extracted_text = _extract_pdf_text(asset.file_path)
        elif asset.source_type == "audio" and asset.file_path:
            transcript_text = _extract_audio_text(asset.file_path, language=asset.language)
        elif asset.source_type == "text":
            extracted_text = asset.extracted_text or ""
    except Exception as exc:
        failure_reason = str(exc)

    base_text = transcript_text or extracted_text
    deterministic_updates = {}
    prompt_notes = []

    if base_text:
        try:
            deterministic_updates = extract_deterministic_updates(
                base_text,
                asset.language,
                asset.domain,
            )
        except Exception as exc:
            failure_reason = str(exc)

    if isinstance(deterministic_updates, dict):
        prompt_notes = []
        if isinstance(deterministic_updates.get("promptNotes"), list):
            prompt_notes.extend(deterministic_updates.get("promptNotes"))
        if isinstance(deterministic_updates.get("swarPromptNotes"), list):
            prompt_notes.extend(deterministic_updates.get("swarPromptNotes"))
        if isinstance(asset.manual_notes, list):
            prompt_notes.extend([str(note).strip() for note in asset.manual_notes if str(note).strip()])

    with SessionLocal() as db:
        asset = db.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
        if not asset:
            return
        if extracted_text:
            asset.extracted_text = extracted_text
        if transcript_text:
            asset.transcript_text = transcript_text
        asset.deterministic_updates = _merge_manual_notes(
            deterministic_updates or {},
            asset.manual_notes if isinstance(asset.manual_notes, list) else None,
            asset.domain,
        ) or None
        asset.prompt_notes = prompt_notes or None
        if failure_reason:
            asset.status = "failed"
            asset.deterministic_updates = {"error": failure_reason}
        else:
            asset.status = "ready_for_review"
        db.commit()


def apply_deterministic_updates(asset: KnowledgeAsset) -> Dict[str, Any]:
    updates = _merge_manual_notes(
        asset.deterministic_updates or {},
        asset.manual_notes if isinstance(asset.manual_notes, list) else None,
        asset.domain,
    )
    if not isinstance(updates, dict):
        return {}
    applied = update_from_extraction(updates)
    return applied
