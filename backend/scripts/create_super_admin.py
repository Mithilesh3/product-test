from __future__ import annotations

import os
import sys

from app.db.session import SessionLocal
from app.db.models import Organization, Subscription, User
from app.core.security import hash_password


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def main() -> int:
    email = _require_env("SUPER_ADMIN_EMAIL").lower()
    password = _require_env("SUPER_ADMIN_PASSWORD")
    full_name = os.getenv("SUPER_ADMIN_NAME", "Super Admin").strip() or "Super Admin"
    org_name = os.getenv("SUPER_ADMIN_ORG", "LifeSignify HQ").strip() or "LifeSignify HQ"

    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == email, User.is_deleted.is_(False)).first()
        if existing:
            print(f"Super admin already exists for {email}")
            return 0

        org = db.query(Organization).filter(Organization.name == org_name, Organization.is_deleted.is_(False)).first()
        if not org:
            org = Organization(name=org_name, plan="premium")
            db.add(org)
            db.flush()

        subscription = db.query(Subscription).filter(Subscription.tenant_id == org.id).first()
        if not subscription:
            subscription = Subscription(tenant_id=org.id, plan_name="premium", is_active=True)
            db.add(subscription)

        user = User(
            email=email,
            full_name=full_name,
            mobile_number=None,
            password=hash_password(password),
            tenant_id=org.id,
            role="super_admin",
            kyc_verified=True,
            is_deleted=False,
            is_blocked=False,
            abuse_warnings=0,
            signup_source="bootstrap_script",
            signup_locale="en-IN",
            signup_timezone="Asia/Kolkata",
            signup_country="India",
        )
        db.add(user)
        db.commit()
        print(f"Created super admin: {email}")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Failed to create super admin: {exc}", file=sys.stderr)
        raise SystemExit(1)
