from datetime import datetime

from app.core.time_utils import UTC
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.payment_config import create_gateway_order, verify_gateway_payment
from app.db.models import Organization, Payment, Subscription, User


# =====================================================
# PLAN PRICING (IN PAISE)
# =====================================================
PLAN_PRICING = {
    "basic": 9900,
    "standard": 49900,
    "enterprise": 109900,
    # Backward compatibility alias.
    "pro": 49900,
    "premium": 109900,
}

PLAN_REPORT_LIMITS = {
    "basic": 1,
    "standard": 5,
    "enterprise": 21,
}

PLAN_DISPLAY_NAMES = {
    "basic": "Basic",
    "standard": "Standard",
    "enterprise": "Enterprise",
}

INVOICE_COMPANY_NAME = "NETSEEMS VENTURES PRIVATE LIMITED"
INVOICE_BRAND_LINE = "(Operating under brand: LifeSignify)"
INVOICE_ADDRESS_LINE_1 = "A19, Om Bungalow, Sai Jyot Park,"
INVOICE_ADDRESS_LINE_2 = "Rahatani, Pune, Maharashtra - 411017"
INVOICE_GSTIN = "27AAHCN4778J1ZU"
INVOICE_PRODUCT_DESCRIPTION = "LifeSignify NumAI SaaS Subscription"
GST_RATE_PERCENT = Decimal("18.00")


def _normalize_plan_key(raw: str) -> str:
    plan_key = (raw or "").lower().strip()
    if plan_key == "pro":
        return "standard"
    if plan_key == "premium":
        return "enterprise"
    return plan_key


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _build_invoice_data(payment: Payment, current_user: User) -> dict:
    total_amount = (Decimal(str(payment.amount or 0)) / Decimal("100.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    divisor = Decimal("1.00") + (GST_RATE_PERCENT / Decimal("100.00"))
    taxable_value = (total_amount / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gst_amount = (total_amount - taxable_value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    plan_key = _normalize_plan_key(payment.plan_name or "basic")
    created_at = payment.created_at or datetime.now(UTC)
    invoice_number = f"LSN-{created_at.strftime('%Y%m%d')}-{payment.id}"

    return {
        "invoice_number": invoice_number,
        "invoice_date": created_at.date().isoformat(),
        "company_name": INVOICE_COMPANY_NAME,
        "brand_line": INVOICE_BRAND_LINE,
        "address_line_1": INVOICE_ADDRESS_LINE_1,
        "address_line_2": INVOICE_ADDRESS_LINE_2,
        "company_gstin": INVOICE_GSTIN,
        "customer_name": current_user.full_name or "NA",
        "customer_email": current_user.email,
        "customer_mobile": current_user.mobile_number,
        "payment_reference": payment.razorpay_payment_id or payment.razorpay_order_id,
        "plan_name": PLAN_DISPLAY_NAMES.get(plan_key, plan_key.title()),
        "report_limit": PLAN_REPORT_LIMITS.get(plan_key, 0),
        "product_description": INVOICE_PRODUCT_DESCRIPTION,
        "currency": payment.currency or "INR",
        "taxable_value": _money(taxable_value),
        "gst_rate_percent": _money(GST_RATE_PERCENT),
        "gst_amount": _money(gst_amount),
        "total_amount": _money(total_amount),
        "status": payment.status,
    }


def get_payment_invoice(db: Session, current_user: User, payment_id: int) -> dict:
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Invoice access denied")

    if payment.status != "paid":
        raise HTTPException(status_code=400, detail="Invoice available only for paid transactions")

    return _build_invoice_data(payment, current_user)


def render_invoice_html(invoice: dict) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Invoice {invoice['invoice_number']}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111827; }}
    .header {{ margin-bottom: 16px; }}
    .company {{ font-size: 18px; font-weight: 700; }}
    .brand {{ font-size: 14px; color: #374151; margin-top: 2px; }}
    .address {{ font-size: 13px; color: #4b5563; margin-top: 8px; line-height: 1.5; }}
    .meta {{ font-size: 13px; color: #4b5563; margin-top: 4px; }}
    .section {{ margin-top: 20px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; font-size: 13px; text-align: left; }}
    th {{ background: #f9fafb; }}
    .totals td {{ font-weight: 600; }}
  </style>
</head>
<body>
  <div class="header">
    <div class="company">{invoice['company_name']}</div>
    <div class="brand">{invoice['brand_line']}</div>
    <div class="address">{invoice['address_line_1']}<br/>{invoice['address_line_2']}</div>
    <div class="meta"><strong>GSTIN:</strong> {invoice['company_gstin']}</div>
  </div>

  <div class="section">
    <strong>Invoice No:</strong> {invoice['invoice_number']}<br/>
    <strong>Date:</strong> {invoice['invoice_date']}<br/>
    <strong>Payment Ref:</strong> {invoice['payment_reference']}<br/>
  </div>

  <div class="section">
    <strong>Billed To</strong><br/>
    <strong>Name:</strong> {invoice.get('customer_name') or '-'}<br/>
    <strong>Mobile:</strong> {invoice.get('customer_mobile') or '-'}<br/>
    <strong>Email:</strong> {invoice.get('customer_email') or '-'}
  </div>

  <div class="section">
    <table>
      <thead>
        <tr>
          <th>Description</th>
          <th>Plan</th>
          <th>Reports Included</th>
          <th>Taxable (INR)</th>
          <th>GST {invoice['gst_rate_percent']}% (INR)</th>
          <th>Total (INR)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>{invoice['product_description']}</td>
          <td>{invoice['plan_name']}</td>
          <td>{invoice['report_limit']}</td>
          <td>{invoice['taxable_value']}</td>
          <td>{invoice['gst_amount']}</td>
          <td>{invoice['total_amount']}</td>
        </tr>
      </tbody>
    </table>
  </div>
</body>
</html>
"""


# =====================================================
# CREATE ORDER
# =====================================================
def create_payment_order(db: Session, current_user: User, plan_name: str):
    plan_key = _normalize_plan_key(plan_name)

    if plan_key not in PLAN_PRICING:
        raise HTTPException(status_code=400, detail="Invalid plan selected")

    amount = PLAN_PRICING[plan_key]

    order = create_gateway_order(
        amount=amount,
        currency="INR",
        notes={
            "tenant_id": current_user.tenant_id,
            "user_id": current_user.id,
            "plan": plan_key,
        },
        redirect_url=settings.PHONEPE_PAYMENT_RETURN_URL,
    )

    payment = Payment(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        plan_name=plan_key,
        razorpay_order_id=order.id,
        amount=amount,
        currency="INR",
        status="created",
        created_at=datetime.now(UTC),
    )

    db.add(payment)
    db.commit()

    return {
        "id": order.id,
        "amount": amount,
        "currency": "INR",
        "provider": order.provider,
        "checkout_url": order.checkout_url,
    }


# =====================================================
# VERIFY + ACTIVATE SUBSCRIPTION
# =====================================================
def verify_payment_signature(
    db: Session,
    current_user: User,
    order_id: str,
    payment_id: str | None = None,
    signature: str | None = None,
):
    verification = verify_gateway_payment(
        order_id=order_id,
        payment_id=payment_id,
        signature=signature,
    )
    if not verification.get("verified"):
        state = verification.get("status") or "unverified"
        raise HTTPException(status_code=400, detail=f"Payment verification failed ({state})")

    payment = (
        db.query(Payment)
        .filter(Payment.razorpay_order_id == order_id)
        .first()
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.user_id != current_user.id or payment.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Payment does not belong to this user")

    if payment.status == "paid":
        return {"message": "Already verified"}

    payment.status = "paid"
    payment.razorpay_payment_id = str(verification.get("payment_id") or payment_id or order_id)
    payment.razorpay_signature = str(verification.get("signature") or signature or "")

    subscription = (
        db.query(Subscription)
        .filter(Subscription.tenant_id == payment.tenant_id)
        .first()
    )

    if not subscription:
        subscription = Subscription(tenant_id=payment.tenant_id)
        db.add(subscription)

    subscription.plan_name = payment.plan_name
    subscription.is_active = True
    subscription.start_date = datetime.now(UTC)
    # Report credits are plan-based allocations, not monthly resets.
    subscription.end_date = None
    subscription.reports_used = 0

    organization = (
        db.query(Organization)
        .filter(Organization.id == payment.tenant_id)
        .first()
    )

    organization.plan = payment.plan_name

    db.commit()

    return {
        "message": "Subscription activated",
        "plan": organization.plan,
    }

