from datetime import timezone

try:
    from datetime import UTC as _UTC  # Python 3.11+
except ImportError:  # pragma: no cover - Python <3.11
    _UTC = timezone.utc

UTC = _UTC

__all__ = ["UTC"]
