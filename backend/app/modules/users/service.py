from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.config import settings
from app.core.payment_config import create_gateway_order, verify_gateway_payment
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.models import Organization, Payment, Subscription, User

logger = logging.getLogger(__name__)

KYC_AMOUNT_PAISE = 100
KYC_PLAN_KEY = "kyc_registration"


def _normalize_mobile(value: str) -> str:
    digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        return digits[-10:]
    if len(digits) == 11 and digits.startswith("0"):
        return digits[-10:]
    return digits


def _mobile_candidates(value: str) -> set[str]:
    normalized = _normalize_mobile(value)
    if not normalized:
        return set()

    candidates = {normalized}
    if len(normalized) == 10:
        candidates.add(f"91{normalized}")
    elif len(normalized) == 12 and normalized.startswith("91"):
        candidates.add(normalized[-10:])
    return {item for item in candidates if item}


def _safe_org_name(full_name: str, mobile_number: str) -> str:
    base = " ".join((full_name or "").split()) or "NumAI User"
    return f"{base} ({mobile_number})"


def _create_kyc_order(normalized_mobile: str) -> dict:
    try:
        order = create_gateway_order(
            amount=KYC_AMOUNT_PAISE,
            currency="INR",
            notes={
                "purpose": "registration_kyc",
                "mobile_number": normalized_mobile,
            },
            redirect_url=settings.PHONEPE_KYC_RETURN_URL,
        )
        logger.info(
            "kyc_order_created", extra={"mobile_number": normalized_mobile, "order_id": order.id}
        )
        return {
            "id": order.id,
            "amount": order.amount,
            "currency": order.currency,
            "provider": order.provider,
            "checkout_url": order.checkout_url,
        }
    except Exception as exc:
        logger.exception("Payment order creation failed during registration")
        message = str(exc) or "Payment gateway request failed"
        if "authentication failed" in message.lower():
            raise HTTPException(
                status_code=502,
                detail="Payment gateway authentication failed. Verify payment credentials in backend environment.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Unable to initiate KYC payment. Please retry shortly.",
        ) from exc


def _registration_response(normalized_mobile: str, order: dict) -> dict:
    return {
        "registration_pending": True,
        "mobile_number": normalized_mobile,
        "kyc_order": {
            "id": order["id"],
            "amount": KYC_AMOUNT_PAISE,
            "currency": "INR",
            "description": "KYC verification fee (Non-refundable)",
            "provider": order.get("provider"),
            "checkout_url": order.get("checkout_url"),
        },
    }


# =====================================================
# REGISTER + INITIATE KYC PAYMENT
# =====================================================
def create_user(
    db: Session,
    full_name: str,
    mobile_number: str,
    password: str,
    signup_context: dict | None = None,
):
    normalized_full_name = " ".join(str(full_name or "").split())
    normalized_mobile = _normalize_mobile(mobile_number)
    signup_context = signup_context or {}

    if not normalized_full_name:
        raise HTTPException(status_code=400, detail="Full name is required")
    if not normalized_mobile:
        raise HTTPException(status_code=400, detail="Mobile number is required")

    try:
        existing_user = (
            db.query(User)
            .filter(
                User.mobile_number.in_(list(_mobile_candidates(normalized_mobile))),
                User.is_deleted.is_(False),
            )
            .first()
        )
        if existing_user:
            if existing_user.kyc_verified:
                raise HTTPException(status_code=400, detail="Mobile number already registered")

            # Pending KYC registrations are retriable. We refresh profile/password so the
            # latest submission is the one used after KYC completion.
            if normalized_full_name and normalized_full_name != (existing_user.full_name or ""):
                existing_user.full_name = normalized_full_name
            existing_user.password = hash_password(password)
            existing_user.signup_source = signup_context.get("source") or existing_user.signup_source
            existing_user.signup_ip = signup_context.get("ip") or existing_user.signup_ip
            existing_user.signup_user_agent = (
                signup_context.get("user_agent") or existing_user.signup_user_agent
            )
            existing_user.signup_referrer = signup_context.get("referrer") or existing_user.signup_referrer
            existing_user.signup_accept_language = (
                signup_context.get("accept_language") or existing_user.signup_accept_language
            )
            existing_user.signup_locale = signup_context.get("locale") or existing_user.signup_locale
            existing_user.signup_timezone = signup_context.get("timezone") or existing_user.signup_timezone
            existing_user.signup_city = signup_context.get("city") or existing_user.signup_city
            existing_user.signup_country = signup_context.get("country") or existing_user.signup_country

            subscription = (
                db.query(Subscription)
                .filter(Subscription.tenant_id == existing_user.tenant_id)
                .first()
            )
            if not subscription:
                subscription = Subscription(
                    tenant_id=existing_user.tenant_id,
                    plan_name="basic",
                    is_active=False,
                )
                db.add(subscription)
                db.flush()

            order = _create_kyc_order(normalized_mobile)

            payment = Payment(
                user_id=existing_user.id,
                tenant_id=existing_user.tenant_id,
                plan_name=KYC_PLAN_KEY,
                razorpay_order_id=order["id"],
                amount=KYC_AMOUNT_PAISE,
                currency="INR",
                status="created",
            )
            db.add(payment)
            db.commit()
            logger.info(
                "registration_success_pending_kyc",
                extra={"user_id": existing_user.id, "tenant_id": existing_user.tenant_id},
            )
            return _registration_response(normalized_mobile, order)

        organization = Organization(name=_safe_org_name(normalized_full_name, normalized_mobile), plan="basic")
        db.add(organization)
        db.flush()

        user = User(
            full_name=normalized_full_name,
            mobile_number=normalized_mobile,
            email=None,
            password=hash_password(password),
            tenant_id=organization.id,
            role="admin",
            kyc_verified=False,
            signup_source=signup_context.get("source") or "web_signup",
            signup_ip=signup_context.get("ip"),
            signup_user_agent=signup_context.get("user_agent"),
            signup_referrer=signup_context.get("referrer"),
            signup_accept_language=signup_context.get("accept_language"),
            signup_locale=signup_context.get("locale"),
            signup_timezone=signup_context.get("timezone"),
            signup_city=signup_context.get("city"),
            signup_country=signup_context.get("country"),
        )
        db.add(user)
        db.flush()

        subscription = Subscription(
            tenant_id=organization.id,
            plan_name="basic",
            is_active=False,
        )
        db.add(subscription)
        db.flush()

        order = _create_kyc_order(normalized_mobile)

        payment = Payment(
            user_id=user.id,
            tenant_id=user.tenant_id,
            plan_name=KYC_PLAN_KEY,
            razorpay_order_id=order["id"],
            amount=KYC_AMOUNT_PAISE,
            currency="INR",
            status="created",
        )
        db.add(payment)

        db.commit()
        logger.info(
            "registration_success_pending_kyc",
            extra={"user_id": user.id, "tenant_id": user.tenant_id},
        )

        return _registration_response(normalized_mobile, order)

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError as exc:
        db.rollback()
        details = str(getattr(exc, "orig", exc)).lower()
        logger.warning("registration_failed_integrity", extra={"mobile_number": normalized_mobile})
        if "mobile" in details:
            raise HTTPException(status_code=400, detail="Mobile number already registered") from exc
        raise HTTPException(status_code=400, detail="Registration could not be completed") from exc

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error during registration")
        logger.warning("registration_failed_database", extra={"mobile_number": normalized_mobile})
        raise HTTPException(status_code=500, detail="Database error during registration") from exc


def verify_registration_kyc(
    db: Session,
    mobile_number: str,
    order_id: str,
    payment_id: str | None = None,
    signature: str | None = None,
):
    normalized_mobile = _normalize_mobile(mobile_number)

    user = (
        db.query(User)
        .filter(
            User.mobile_number.in_(list(_mobile_candidates(normalized_mobile))),
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payment = (
        db.query(Payment)
        .filter(
            Payment.user_id == user.id,
            Payment.razorpay_order_id == order_id,
            Payment.plan_name == KYC_PLAN_KEY,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="KYC payment not found")

    verification = verify_gateway_payment(
        order_id=order_id,
        payment_id=payment_id,
        signature=signature,
    )
    if not verification.get("verified"):
        logger.warning(
            "kyc_verification_failed_signature",
            extra={"mobile_number": normalized_mobile, "order_id": order_id},
        )
        raise HTTPException(
            status_code=400,
            detail=f"Payment verification failed ({verification.get('status') or 'unverified'})",
        )

    payment.status = "paid"
    payment.razorpay_payment_id = str(verification.get("payment_id") or payment_id or order_id)
    payment.razorpay_signature = str(verification.get("signature") or signature or "")
    user.kyc_verified = True

    db.commit()
    logger.info(
        "kyc_verification_success",
        extra={"mobile_number": normalized_mobile, "order_id": order_id},
    )

    return {
        "message": "KYC completed. Please login with mobile number and password.",
        "mobile_number": normalized_mobile,
        "kyc_verified": True,
    }


# =====================================================
# AUTHENTICATE USER (MOBILE-FIRST, EMAIL COMPAT)
# =====================================================
def authenticate_user(db: Session, identifier: str, password: str):
    normalized_identifier = (identifier or "").strip().lower()
    normalized_mobile = _normalize_mobile(identifier)
    mobile_candidates = list(_mobile_candidates(normalized_mobile))

    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.email) == normalized_identifier,
                User.mobile_number.in_(mobile_candidates) if mobile_candidates else False,
            ),
            User.is_deleted.is_(False),
        )
        .first()
    )

    if not user:
        return None

    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Account blocked due to abusive behavior")

    if not verify_password(password, user.password):
        return None

    return user


# =====================================================
# LOGIN (JWT = user + tenant + role)
# =====================================================
def login_user(db: Session, identifier: str, password: str):
    user = authenticate_user(db, identifier, password)

    if not user:
        return None

    user_tenant_id = getattr(user, "tenant_id", None)
    user_mobile = getattr(user, "mobile_number", None)
    user_email = getattr(user, "email", None)
    user_role = getattr(user, "role", "user")
    user_kyc_verified = bool(getattr(user, "kyc_verified", False))

    kyc_record_exists = (
        db.query(Payment.id)
        .filter(
            Payment.user_id == user.id,
            Payment.plan_name == KYC_PLAN_KEY,
        )
        .first()
        is not None
    )

    # Enforce KYC only for users who entered the new registration KYC flow.
    # Legacy users (no kyc_registration record) can continue logging in.
    # Safety: if tenant mapping is missing and KYC is incomplete, block login.
    if (kyc_record_exists or user_tenant_id is None) and not user_kyc_verified:
        logger.info(
            "login_blocked_kyc_incomplete",
            extra={"user_id": user.id, "mobile_number": user_mobile},
        )
        raise HTTPException(status_code=403, detail="Complete KYC payment to continue")

    if user_tenant_id is None:
        raise HTTPException(status_code=400, detail="User organization mapping missing")

    organization = db.query(Organization).filter(Organization.id == user_tenant_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    token = create_access_token(
        {
            "sub": str(user.id),
            "tenant_id": user_tenant_id,
            "role": user_role,
        }
    )

    try:
        log_action(
            db=db,
            user_id=user.id,
            tenant_id=user_tenant_id,
            action="USER_LOGIN",
            details={
                "mobile_number": user_mobile,
                "email": user_email,
            },
        )
    except Exception:
        db.rollback()
        logger.exception("Login succeeded, but audit logging failed")

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# =====================================================
# SUPER ADMIN LOGIN (SEPARATE FLOW)
# =====================================================
def login_super_admin(db: Session, identifier: str, password: str):
    user = authenticate_user(db, identifier, password)

    if not user:
        return None

    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin account required")

    organization = db.query(Organization).filter(Organization.id == user.tenant_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    token = create_access_token(
        {
            "sub": str(user.id),
            "tenant_id": user.tenant_id,
            "role": user.role,
        }
    )

    try:
        log_action(
            db=db,
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="SUPER_ADMIN_LOGIN",
            details={
                "mobile_number": user.mobile_number,
                "email": user.email,
            },
        )
    except Exception:
        db.rollback()
        logger.exception("Super admin login succeeded, but audit logging failed")

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# =====================================================
# UPDATE ORGANIZATION PLAN (ADMIN)
# =====================================================
def update_organization_plan(
    db: Session,
    current_user: User,
    new_plan: str,
):
    organization = db.query(Organization).filter(Organization.id == current_user.tenant_id).first()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    organization.plan = new_plan
    db.commit()
    db.refresh(organization)

    try:
        log_action(
            db=db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="PLAN_UPDATED",
            details={"new_plan": new_plan},
        )
    except Exception:
        db.rollback()
        logger.exception("Plan update succeeded, but audit logging failed")

    return organization
