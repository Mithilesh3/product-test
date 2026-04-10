from sqlalchemy.orm import Session
from app.db.models import AuditLog


def log_action(
    db: Session,
    user_id: int,
    tenant_id: int,
    action: str,
    details: dict | None = None,
):
    log = AuditLog(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        details=details or {}
    )

    db.add(log)
    db.commit()
