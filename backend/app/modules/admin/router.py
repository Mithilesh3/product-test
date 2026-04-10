import secrets
import uuid
from datetime import datetime
from app.core.time_utils import UTC

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.db.dependencies import get_db
from app.modules.users.router import super_admin_required
from app.db.models import User, Report, Organization, Subscription, KnowledgeAsset
from app.core.security import hash_password
from app.modules.admin.knowledge_service import (
    save_uploaded_asset,
    process_knowledge_asset,
    apply_deterministic_updates,
)


# Router WITHOUT prefix (prefix applied in main.py)
router = APIRouter(tags=["Admin"])


# =====================================================
# ADMIN ANALYTICS
# =====================================================

@router.get("/analytics")
def get_admin_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):

    total_users = db.query(func.count(User.id)).scalar()
    total_reports = db.query(func.count(Report.id)).scalar()
    total_orgs = db.query(func.count(Organization.id)).scalar()

    active_subscriptions = (
        db.query(func.count(Subscription.id))
        .filter(Subscription.is_active.is_(True))
        .scalar()
    )

    return {
        "total_users": total_users or 0,
        "total_reports": total_reports or 0,
        "total_organizations": total_orgs or 0,
        "active_subscriptions": active_subscriptions or 0,
    }


# =====================================================
# SUPER ADMIN - ALL REGISTERED USERS (CROSS TENANT)
# =====================================================
@router.get("/users/all")
def list_all_registered_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):
    users = (
        db.query(User)
        .filter(User.is_deleted.is_(False))
        .order_by(User.created_at.desc())
        .all()
    )

    results = []
    for u in users:
        organization_name = None
        organization_plan = None
        if u.organization:
            organization_name = u.organization.name
            organization_plan = u.organization.plan

        # Do not return self row in super admin listing.
        if u.id == current_user.id:
            continue

        results.append(
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "mobile_number": u.mobile_number,
                "role": u.role,
                "tenant_id": u.tenant_id,
                "organization_name": organization_name,
                "organization_plan": organization_plan,
                "kyc_verified": u.kyc_verified,
                "is_blocked": u.is_blocked,
                "signup_source": u.signup_source,
                "signup_ip": u.signup_ip,
                "signup_city": u.signup_city,
                "signup_country": u.signup_country,
                "signup_locale": u.signup_locale,
                "signup_timezone": u.signup_timezone,
                "created_at": u.created_at,
            }
        )

    return results


class ManualCreateUserRequest(BaseModel):
    full_name: str | None = None
    mobile_number: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: str = "user"
    organization_name: str | None = None
    organization_plan: str = "basic"
    kyc_verified: bool = True


class KnowledgeAssetApprovalRequest(BaseModel):
    consent: bool
    notes: str | None = None


class KnowledgeAssetRejectionRequest(BaseModel):
    reason: str | None = None


@router.post("/users/manual-create")
def create_user_manually(
    payload: ManualCreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):
    allowed_roles = {"admin", "manager", "user"}
    if payload.role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    email = (payload.email or "").strip().lower() or None
    mobile_number = (payload.mobile_number or "").strip() or None
    full_name = (payload.full_name or "").strip() or None

    if not email and not mobile_number:
        raise HTTPException(status_code=400, detail="Email or mobile number is required")

    if email:
        existing_email = db.query(User).filter(User.email == email, User.is_deleted.is_(False)).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    if mobile_number:
        existing_mobile = (
            db.query(User)
            .filter(User.mobile_number == mobile_number, User.is_deleted.is_(False))
            .first()
        )
        if existing_mobile:
            raise HTTPException(status_code=400, detail="Mobile number already registered")

    organization_name = (payload.organization_name or "").strip() or None
    organization: Organization | None = None
    if organization_name:
        organization = (
            db.query(Organization)
            .filter(Organization.name == organization_name, Organization.is_deleted.is_(False))
            .first()
        )

    if not organization:
        organization_name = organization_name or f"Manual Tenant {secrets.token_hex(2).upper()}"
        organization = Organization(name=organization_name, plan=payload.organization_plan or "basic")
        db.add(organization)
        db.flush()

    generated_password = payload.password or secrets.token_hex(4)

    user = User(
        email=email,
        full_name=full_name,
        mobile_number=mobile_number,
        password=hash_password(generated_password),
        tenant_id=organization.id,
        role=payload.role,
        kyc_verified=payload.kyc_verified,
        is_deleted=False,
        is_blocked=False,
        abuse_warnings=0,
        signup_source="manual_super_admin",
        signup_ip=None,
        signup_user_agent=None,
        signup_referrer=None,
        signup_accept_language=None,
        signup_locale="en-IN",
        signup_timezone="Asia/Kolkata",
        signup_city=None,
        signup_country="India",
    )
    db.add(user)

    existing_subscription = (
        db.query(Subscription).filter(Subscription.tenant_id == organization.id).first()
    )
    if not existing_subscription:
        subscription = Subscription(
            tenant_id=organization.id,
            plan_name=payload.organization_plan or "basic",
            is_active=bool(payload.kyc_verified),
        )
        db.add(subscription)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not create user due to duplicate fields")

    db.refresh(user)
    return {
        "message": "User created successfully",
        "id": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "mobile_number": user.mobile_number,
        "role": user.role,
        "generated_password": generated_password,
    }


@router.put("/users/{user_id}/block")
def set_user_block_status(
    user_id: int,
    blocked: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot block your own account")

    user.is_blocked = blocked
    if not blocked:
        user.abuse_warnings = 0

    db.commit()
    return {
        "message": "User updated successfully",
        "user_id": user.id,
        "is_blocked": user.is_blocked,
    }


# =====================================================
# SUPER ADMIN KNOWLEDGE STUDIO
# =====================================================

@router.post("/knowledge/assets")
def upload_knowledge_asset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    language: str | None = Form(None),
    domain: str | None = Form(None),
    source_type: str | None = Form(None),
    manual_notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):
    if not file:
        raise HTTPException(status_code=400, detail="File is required")

    filename = file.filename or "asset"
    extension = filename.split(".")[-1].lower() if "." in filename else ""
    resolved_type = (source_type or "").strip().lower()
    if not resolved_type:
        if extension in {"pdf"}:
            resolved_type = "pdf"
        elif extension in {"mp3", "wav", "m4a", "ogg"}:
            resolved_type = "audio"
        else:
            resolved_type = "text"

    resolved_domain = (domain or "").strip().lower() or "numerology"
    if resolved_domain not in {"numerology", "swar_vigyan"}:
        resolved_domain = "numerology"

    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file_path, size_bytes = save_uploaded_asset(file, unique_name)

    manual_note_list = []
    if manual_notes:
        manual_note_list = [line.strip() for line in manual_notes.splitlines() if line.strip()]

    asset = KnowledgeAsset(
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        domain=resolved_domain,
        source_type=resolved_type,
        language=(language or "").strip().lower() or None,
        title=(title or "").strip() or filename,
        description=(description or "").strip() or None,
        file_name=filename,
        file_path=file_path,
        content_type=file.content_type,
        size_bytes=size_bytes,
        status="uploaded",
        approval_status="pending",
        manual_notes=manual_note_list or None,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    background_tasks.add_task(process_knowledge_asset, asset.id)

    return {
        "id": asset.id,
        "title": asset.title,
        "status": asset.status,
        "approval_status": asset.approval_status,
        "domain": asset.domain,
        "source_type": asset.source_type,
        "language": asset.language,
        "created_at": asset.created_at,
    }


@router.get("/knowledge/assets")
def list_knowledge_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):
    assets = (
        db.query(KnowledgeAsset)
        .order_by(KnowledgeAsset.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": asset.id,
            "title": asset.title,
            "status": asset.status,
            "approval_status": asset.approval_status,
            "approved_at": asset.approved_at,
            "domain": asset.domain,
            "source_type": asset.source_type,
            "language": asset.language,
            "created_at": asset.created_at,
            "has_updates": bool(asset.deterministic_updates) or bool(asset.manual_notes),
        }
        for asset in assets
    ]


@router.post("/knowledge/assets/{asset_id}/process")
def reprocess_knowledge_asset(
    asset_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):
    asset = db.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.status = "uploaded"
    asset.approval_status = "pending"
    asset.approved_by = None
    asset.approved_at = None
    asset.approval_notes = None
    db.commit()
    background_tasks.add_task(process_knowledge_asset, asset.id)
    return {"message": "Processing started", "asset_id": asset.id}


@router.post("/knowledge/assets/{asset_id}/apply")
def apply_knowledge_asset(
    asset_id: int,
    payload: KnowledgeAssetApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):
    asset = db.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not payload.consent:
        raise HTTPException(status_code=400, detail="Consent is required before applying updates")
    if not asset.deterministic_updates and not asset.manual_notes:
        raise HTTPException(status_code=400, detail="No deterministic updates available on this asset")
    if asset.status not in {"ready_for_review", "approved"}:
        raise HTTPException(status_code=400, detail="Asset is not ready for approval")
    applied = apply_deterministic_updates(asset)
    asset.status = "applied"
    asset.approval_status = "approved"
    asset.approved_by = current_user.id
    asset.approved_at = datetime.now(UTC)
    if payload.notes:
        asset.approval_notes = payload.notes.strip()
    db.commit()
    return {"message": "Deterministic updates applied", "applied": applied}


@router.post("/knowledge/assets/{asset_id}/reject")
def reject_knowledge_asset(
    asset_id: int,
    payload: KnowledgeAssetRejectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(super_admin_required),
):
    asset = db.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.status = "rejected"
    asset.approval_status = "rejected"
    asset.approved_by = current_user.id
    asset.approved_at = datetime.now(UTC)
    if payload.reason:
        asset.approval_notes = payload.reason.strip()
    db.commit()
    return {"message": "Asset rejected"}

