from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import secrets

from app.db.dependencies import get_db
from app.db.models import User, Organization, Subscription
from app.modules.users.schemas import (
    UserCreate,
    RegisterInitResponse,
    TokenResponse,
    VerifyRegistrationKYCRequest,
)
from app.modules.users.service import (
    create_user,
    login_user,
    login_super_admin,
    verify_registration_kyc,
)
from app.core.security import decode_access_token, hash_password
from app.modules.reports.plan_config import resolve_plan_key


router = APIRouter(tags=["Users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


# =====================================================
# AUTH DEPENDENCY
# =====================================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    user = (
        db.query(User)
        .filter(
            User.id == int(user_id),
            User.tenant_id == int(tenant_id),
            User.is_deleted == False
        )
        .first()
    )

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.is_blocked:
        raise HTTPException(status_code=401, detail="Account blocked due to abusive behavior")

    return user


# =====================================================
# ROLE GUARDS
# =====================================================
def super_admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# =====================================================
# REGISTER
# =====================================================
@router.post("/register", response_model=RegisterInitResponse)
def register(
    user: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    signup_context = {
        "source": user.signup_source or "web_signup",
        "ip": request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else None),
        "user_agent": request.headers.get("user-agent"),
        "referrer": request.headers.get("referer"),
        "accept_language": request.headers.get("accept-language"),
        "locale": user.signup_locale,
        "timezone": user.signup_timezone,
        "city": user.signup_city,
        "country": user.signup_country,
    }

    return create_user(
        db,
        user.full_name,
        user.mobile_number,
        user.password,
        signup_context=signup_context,
    )


@router.post("/register/verify-kyc")
def verify_registration_payment(
    payload: VerifyRegistrationKYCRequest,
    db: Session = Depends(get_db),
):
    order_id = payload.order_id or payload.razorpay_order_id
    if not order_id:
        raise HTTPException(status_code=400, detail="order_id is required")

    return verify_registration_kyc(
        db=db,
        mobile_number=payload.mobile_number,
        order_id=order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )


# =====================================================
# LOGIN
# =====================================================
@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    result = login_user(db, form_data.username, form_data.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return result


@router.post("/super-admin/login", response_model=TokenResponse)
def super_admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    result = login_super_admin(db, form_data.username, form_data.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return result


# =====================================================
# CURRENT USER DETAILS
# =====================================================
@router.get("/me")
def read_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.tenant_id == current_user.tenant_id,
            Subscription.is_active == True
        )
        .first()
    )

    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "mobile_number": current_user.mobile_number,
        "email": current_user.email,
        "kyc_verified": current_user.kyc_verified,
        "role": current_user.role,
        "organization": {
            "id": current_user.organization.id,
            "name": current_user.organization.name,
            "plan": resolve_plan_key(current_user.organization.plan),
        },
        "subscription": {
            "plan_name": resolve_plan_key(subscription.plan_name) if subscription else "basic",
            "is_active": subscription.is_active if subscription else False,
            "end_date": subscription.end_date if subscription else None,
            "reports_used": subscription.reports_used if subscription else 0,
        }
    }


# =====================================================
# LIST ORG USERS
# =====================================================
@router.get("/org-users")
def list_org_users(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    users = (
        db.query(User)
        .filter(
            User.tenant_id == current_user.tenant_id,
            User.is_deleted == False,
            User.role != "super_admin",
            User.id != current_user.id,
        )
        .all()
    )

    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "mobile_number": u.mobile_number,
            "role": u.role,
            "tenant_id": u.tenant_id,
            "organization_name": u.organization.name if u.organization else None,
            "organization_plan": u.organization.plan if u.organization else None,
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
        for u in users
    ]


# =====================================================
# DELETE USER (SAFE)
# =====================================================
@router.delete("/delete-user/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    user_query = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    )
    if current_user.role != "super_admin":
        user_query = user_query.filter(User.tenant_id == current_user.tenant_id)

    user = user_query.first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    if user.role == "super_admin":
        raise HTTPException(status_code=403, detail="Cannot delete super admin account")

    user.is_deleted = True
    db.commit()

    return {"message": "User deleted successfully"}


# =====================================================
# UPDATE ROLE
# =====================================================
@router.put("/update-user-role/{user_id}")
def update_user_role(
    user_id: int,
    new_role: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    allowed_roles = ["admin", "manager", "user"]

    if new_role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_query = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    )
    if current_user.role != "super_admin":
        user_query = user_query.filter(User.tenant_id == current_user.tenant_id)

    user = user_query.first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "super_admin":
        raise HTTPException(status_code=403, detail="Cannot modify super admin role")

    user.role = new_role
    db.commit()

    return {"message": "Role updated successfully"}


# =====================================================
# INVITE USER
# =====================================================
class InviteUserRequest(BaseModel):
    email: str
    role: str = "user"


@router.post("/invite")
def invite_user(
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    temp_password = secrets.token_hex(4)

    new_user = User(
        email=payload.email,
        password=hash_password(temp_password),
        tenant_id=current_user.tenant_id,
        role=payload.role,
        signup_source="admin_invite",
        signup_country="India",
        signup_timezone="Asia/Kolkata",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User invited successfully",
        "temporary_password": temp_password
    }   
