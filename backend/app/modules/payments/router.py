from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from fastapi.responses import HTMLResponse

from app.db.dependencies import get_db
from app.core.payment_config import public_payment_config
from app.modules.users.router import get_current_user
from app.db.models import User
from app.modules.payments.service import (
    PLAN_PRICING,
    PLAN_REPORT_LIMITS,
    create_payment_order,
    get_payment_invoice,
    render_invoice_html,
    verify_payment_signature,
)

router = APIRouter(tags=["Payments"])


# =====================================================
# RESPONSE MODELS
# =====================================================

class Plan(BaseModel):
    name: str
    price: int
    reports_limit: int | str


class CreateOrderRequest(BaseModel):
    plan: str


class VerifyPaymentRequest(BaseModel):
    order_id: str | None = None
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    razorpay_signature: str | None = None


class PublicPaymentConfig(BaseModel):
    provider: str
    razorpay_key_id: str | None = None


@router.get("/public-config", response_model=PublicPaymentConfig)
def get_public_payment_config():
    return public_payment_config()


# =====================================================
# GET AVAILABLE PLANS
# =====================================================

@router.get("/plans", response_model=List[Plan])
def get_plans():
    basic_price = int(PLAN_PRICING["basic"] / 100)
    standard_price = int(PLAN_PRICING["standard"] / 100)
    enterprise_price = int(PLAN_PRICING["enterprise"] / 100)
    return [
        {
            "name": "Basic",
            "price": basic_price,
            "reports_limit": PLAN_REPORT_LIMITS["basic"]
        },
        {
            "name": "Standard",
            "price": standard_price,
            "reports_limit": PLAN_REPORT_LIMITS["standard"]
        },
        {
            "name": "Enterprise",
            "price": enterprise_price,
            "reports_limit": PLAN_REPORT_LIMITS["enterprise"]
        }
    ]

# =====================================================
# GET PAYMENT HISTORY
# =====================================================

@router.get("/history")
def get_payment_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.db.models import Payment

    def _normalize_plan(plan_name: str | None) -> str:
        raw = (plan_name or "").lower().strip()
        if raw == "pro":
            return "standard"
        if raw == "premium":
            return "enterprise"
        return raw

    def _display_amount_inr(amount: int | None, plan_name: str | None) -> float:
        raw_amount = int(amount or 0)
        normalized_plan = _normalize_plan(plan_name)
        expected_paise = PLAN_PRICING.get(normalized_plan)
        expected_rupees = int(expected_paise / 100) if expected_paise else None

        if expected_paise and raw_amount == expected_paise:
            return round(raw_amount / 100, 2)
        if expected_rupees and raw_amount == expected_rupees:
            return float(raw_amount)

        # Legacy/fallback handling:
        # - modern plan payments are saved in paise
        # - very small values (like KYC Rs.1 -> 100 paise) should still be divided by 100
        if raw_amount > 5000 or raw_amount <= 500:
            return round(raw_amount / 100, 2)

        return float(raw_amount)

    payments = (
        db.query(Payment)
        .filter(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "id": payment.id,
            "amount": payment.amount,
            "amount_inr": _display_amount_inr(payment.amount, payment.plan_name),
            "status": payment.status,
            "payment_reference": payment.razorpay_payment_id or payment.razorpay_order_id,
            "plan_name": _normalize_plan(payment.plan_name),
            "created_at": payment.created_at,
        }
        for payment in payments
    ]


@router.get("/invoice/{payment_id}")
def get_invoice(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_payment_invoice(db, current_user, payment_id)


@router.get("/invoice/{payment_id}/download")
def download_invoice(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = get_payment_invoice(db, current_user, payment_id)
    html = render_invoice_html(invoice)
    filename = f"invoice-{invoice['invoice_number']}.html"
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Invoice-Number": invoice["invoice_number"],
        },
    )


@router.get("/invoice/{payment_id}/view", response_class=HTMLResponse)
def view_invoice_html(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = get_payment_invoice(db, current_user, payment_id)
    return HTMLResponse(content=render_invoice_html(invoice))


# =====================================================
# CREATE PAYMENT ORDER (UPDATED ✅)
# =====================================================

@router.post("/create-order")
def create_order(
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_payment_order(db, current_user, payload.plan)


# =====================================================
# VERIFY PAYMENT
# =====================================================

@router.post("/verify")
def verify_payment(
    payload: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order_id = payload.order_id or payload.razorpay_order_id
    if not order_id:
        raise HTTPException(status_code=400, detail="order_id is required")

    return verify_payment_signature(
        db=db,
        current_user=current_user,
        order_id=order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
