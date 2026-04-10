import logging
import socket
from pathlib import Path
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)


def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists() or os.environ.get("RUNNING_IN_DOCKER") == "1"


def _resolve_database_url(raw_url: str) -> str:
    """
    Keep docker-compose behavior (`db` host) intact, but make local development
    resilient: when `db` is not resolvable on host Python runs, fall back to
    localhost postgres mapping.
    """
    try:
        parsed = make_url(raw_url)
    except Exception:
        return raw_url

    host = (parsed.host or "").strip().lower()
    if host != "db":
        return raw_url

    if _running_in_docker():
        return raw_url

    try:
        socket.gethostbyname(host)
        return raw_url
    except OSError:
        fallback_url = parsed.set(host="127.0.0.1").render_as_string(hide_password=False)
        logger.warning(
            "DATABASE_URL host 'db' not resolvable in current runtime. Falling back to 127.0.0.1."
        )
        return fallback_url

engine = create_engine(
    _resolve_database_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
