from __future__ import annotations

import logging
from typing import Dict, List

from app.core.config import settings

logger = logging.getLogger(__name__)


def _missing(values: Dict[str, str | None]) -> List[str]:
    missing: List[str] = []
    for key, value in values.items():
        if not str(value or "").strip():
            missing.append(key)
    return missing


def verify_runtime_environment() -> Dict[str, object]:
    env_name = (settings.ENVIRONMENT or "development").strip().lower()
    payment_provider = (settings.PAYMENT_PROVIDER or "razorpay").strip().lower()

    payment_keys: Dict[str, str | None]
    if payment_provider == "phonepe":
        payment_keys = {
            "PAYMENT_PROVIDER": settings.PAYMENT_PROVIDER,
            "PHONEPE_CLIENT_ID": settings.PHONEPE_CLIENT_ID,
            "PHONEPE_CLIENT_SECRET": settings.PHONEPE_CLIENT_SECRET,
        }
    else:
        payment_keys = {
            "PAYMENT_PROVIDER": settings.PAYMENT_PROVIDER,
            "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID,
            "RAZORPAY_KEY_SECRET": settings.RAZORPAY_KEY_SECRET,
        }

    required_groups: Dict[str, Dict[str, str | None]] = {
        "azure_openai": {
            "AZURE_OPENAI_API_KEY": settings.AZURE_OPENAI_API_KEY,
            "AZURE_OPENAI_ENDPOINT": settings.AZURE_OPENAI_ENDPOINT,
            "AZURE_OPENAI_API_VERSION": settings.AZURE_OPENAI_API_VERSION,
            "AZURE_OPENAI_DEPLOYMENT": settings.AZURE_OPENAI_DEPLOYMENT,
        },
        "database": {
            "DATABASE_URL": settings.DATABASE_URL,
        },
        "jwt_auth": {
            "JWT_SECRET": settings.JWT_SECRET,
            "JWT_ALGORITHM": settings.JWT_ALGORITHM,
        },
        "payments": {
            **payment_keys,
        },
    }

    missing_by_group = {group: _missing(values) for group, values in required_groups.items()}
    missing_by_group = {group: keys for group, keys in missing_by_group.items() if keys}

    hard_failures: List[str] = []
    if missing_by_group:
        for group, keys in missing_by_group.items():
            hard_failures.append(f"{group}: {', '.join(keys)}")

    if settings.AI_FALLBACK_LOG_THRESHOLD < 0:
        hard_failures.append("AI_FALLBACK_LOG_THRESHOLD must be >= 0")

    if env_name in {"production", "prod"}:
        if settings.DEBUG_LOGGING:
            hard_failures.append("DEBUG_LOGGING must be false in production")
        if settings.ENABLE_MOCK_PAYMENTS:
            hard_failures.append("ENABLE_MOCK_PAYMENTS must be false in production")

    result = {
        "environment": env_name,
        "missing_by_group": missing_by_group,
        "debug_logging": settings.DEBUG_LOGGING,
        "mock_payments": settings.ENABLE_MOCK_PAYMENTS,
        "ai_fallback_log_threshold": settings.AI_FALLBACK_LOG_THRESHOLD,
    }

    if hard_failures:
        logger.error("Environment verification failed: %s", hard_failures)
        raise RuntimeError("Environment verification failed: " + " | ".join(hard_failures))

    logger.info("Environment verification passed", extra=result)
    return result
