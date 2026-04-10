from pydantic import BaseModel, EmailStr, Field
from typing import Literal


# =========================
# REGISTER
# =========================
class UserCreate(BaseModel):
    full_name: str = Field(min_length=2)
    mobile_number: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=6)
    signup_source: str | None = None
    signup_city: str | None = None
    signup_country: str | None = None
    signup_locale: str | None = None
    signup_timezone: str | None = None


class RegisterInitResponse(BaseModel):
    registration_pending: bool
    mobile_number: str
    kyc_order: dict


# =========================
# USER RESPONSE
# =========================
class UserResponse(BaseModel):
    id: int
    full_name: str | None = None
    email: EmailStr | None = None
    mobile_number: str | None = None
    tenant_id: int
    role: str
    plan: str
    kyc_verified: bool = False

    model_config = {
        "from_attributes": True
    }


# =========================
# TOKEN RESPONSE
# =========================
class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class VerifyRegistrationKYCRequest(BaseModel):
    mobile_number: str
    order_id: str | None = None
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    razorpay_signature: str | None = None


# =========================
# PLAN UPDATE (Admin Only)
# =========================
class PlanUpdate(BaseModel):
    plan: Literal["basic", "standard", "enterprise"]
