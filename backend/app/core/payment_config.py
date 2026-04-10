from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

import razorpay
from fastapi import HTTPException

from app.core.config import settings

RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET
PAYMENT_PROVIDER = (settings.PAYMENT_PROVIDER or "razorpay").strip().lower()


@dataclass
class PaymentOrder:
    id: str
    amount: int
    currency: str
    provider: str
    checkout_url: str | None = None


def _http_json_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_payload: dict[str, Any] | None = None,
    form_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_headers = headers.copy() if headers else {}
    data: bytes | None = None
    if json_payload is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(json_payload).encode("utf-8")
    elif form_payload is not None:
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(form_payload).encode("utf-8")

    req = urllib.request.Request(url=url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail="Payment gateway unreachable") from exc

    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Payment gateway returned invalid response") from exc


class _MockOrderClient:
    def create(self, payload: dict) -> dict:
        return {
            "id": f"order_mock_{uuid.uuid4().hex[:12]}",
            "amount": payload.get("amount"),
            "currency": payload.get("currency", "INR"),
            "status": "created",
            "notes": payload.get("notes") or {},
        }


class _MockRazorpayClient:
    def __init__(self) -> None:
        self.order = _MockOrderClient()
        self.auth = ("mock_key_id", "mock_key_secret")


if settings.ENABLE_MOCK_PAYMENTS:
    razorpay_client = _MockRazorpayClient()
else:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


_phonepe_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0}


def _ensure_phonepe_credentials() -> None:
    if not settings.PHONEPE_CLIENT_ID or not settings.PHONEPE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="PhonePe credentials missing. Set PHONEPE_CLIENT_ID and PHONEPE_CLIENT_SECRET.",
        )


def _phonepe_access_token() -> str:
    _ensure_phonepe_credentials()
    now = int(time.time())
    cached_token = _phonepe_token_cache.get("access_token")
    if cached_token and now < int(_phonepe_token_cache.get("expires_at", 0)):
        return str(cached_token)

    payload = {
        "client_id": settings.PHONEPE_CLIENT_ID,
        "client_secret": settings.PHONEPE_CLIENT_SECRET,
        "client_version": settings.PHONEPE_CLIENT_VERSION,
        "grant_type": "client_credentials",
    }
    token_response = _http_json_request(
        "POST",
        settings.PHONEPE_AUTH_URL,
        form_payload=payload,
    )

    access_token = str(token_response.get("access_token") or "").strip()
    if not access_token:
        raise HTTPException(status_code=502, detail="PhonePe auth failed: missing access token")

    expires_in = int(token_response.get("expires_in") or 900)
    _phonepe_token_cache["access_token"] = access_token
    _phonepe_token_cache["expires_at"] = now + max(60, expires_in - 30)
    return access_token


def _phonepe_headers() -> dict[str, str]:
    token = _phonepe_access_token()
    return {
        "Authorization": f"O-Bearer {token}",
    }


def _join_redirect_url(base: str, query_params: dict[str, str]) -> str:
    parsed = urllib.parse.urlparse(base)
    existing_qs = dict(urllib.parse.parse_qsl(parsed.query))
    existing_qs.update(query_params)
    return urllib.parse.urlunparse(
        parsed._replace(query=urllib.parse.urlencode(existing_qs))
    )


def _create_phonepe_order(
    *,
    amount: int,
    currency: str,
    redirect_url: str,
    notes: dict[str, Any] | None = None,
) -> PaymentOrder:
    merchant_order_id = f"lsn-{uuid.uuid4().hex[:20]}"
    payload: dict[str, Any] = {
        "merchantOrderId": merchant_order_id,
        "amount": int(amount),
        "paymentFlow": {
            "type": "PG_CHECKOUT",
            "merchantUrls": {
                "redirectUrl": _join_redirect_url(
                    redirect_url,
                    {"phonepe_order_id": merchant_order_id},
                ),
            },
        },
    }
    if notes:
        payload["metaInfo"] = {"udf1": json.dumps(notes)[:240]}

    response = _http_json_request(
        "POST",
        settings.PHONEPE_PAY_URL,
        headers=_phonepe_headers(),
        json_payload=payload,
    )
    checkout_url = (
        response.get("checkoutPageUrl")
        or response.get("redirectUrl")
        or response.get("paymentUrl")
    )
    if not checkout_url:
        raise HTTPException(status_code=502, detail="PhonePe pay response missing checkout URL")

    return PaymentOrder(
        id=merchant_order_id,
        amount=int(amount),
        currency=currency,
        provider="phonepe",
        checkout_url=str(checkout_url),
    )


def create_gateway_order(
    *,
    amount: int,
    currency: str = "INR",
    notes: dict[str, Any] | None = None,
    redirect_url: str | None = None,
) -> PaymentOrder:
    if settings.ENABLE_MOCK_PAYMENTS:
        order = razorpay_client.order.create(
            {"amount": amount, "currency": currency, "notes": notes or {}}
        )
        checkout_url = None
        if PAYMENT_PROVIDER == "phonepe":
            checkout_url = _join_redirect_url(
                redirect_url or settings.PHONEPE_KYC_RETURN_URL,
                {"phonepe_order_id": order["id"]},
            )
        return PaymentOrder(
            id=order["id"],
            amount=int(order.get("amount") or amount),
            currency=str(order.get("currency") or currency),
            provider=PAYMENT_PROVIDER,
            checkout_url=checkout_url,
        )

    if PAYMENT_PROVIDER == "phonepe":
        try:
            return _create_phonepe_order(
                amount=amount,
                currency=currency,
                redirect_url=redirect_url or settings.PHONEPE_PAYMENT_RETURN_URL,
                notes=notes,
            )
        except HTTPException:
            if settings.ENVIRONMENT.lower() == "production":
                raise
            fallback_order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
            checkout_url = _join_redirect_url(
                redirect_url or settings.PHONEPE_KYC_RETURN_URL,
                {"phonepe_order_id": fallback_order_id},
            )
            return PaymentOrder(
                id=fallback_order_id,
                amount=int(amount),
                currency=currency,
                provider="phonepe",
                checkout_url=checkout_url,
            )

    order_payload = {"amount": amount, "currency": currency, "payment_capture": 1}
    if notes:
        order_payload["notes"] = notes
    order = razorpay_client.order.create(order_payload)
    return PaymentOrder(
        id=order["id"],
        amount=int(order.get("amount") or amount),
        currency=str(order.get("currency") or currency),
        provider="razorpay",
        checkout_url=None,
    )


def verify_gateway_payment(
    *,
    order_id: str,
    payment_id: str | None = None,
    signature: str | None = None,
) -> dict[str, Any]:
    if settings.ENABLE_MOCK_PAYMENTS:
        return {
            "verified": True,
            "provider": PAYMENT_PROVIDER,
            "payment_id": payment_id or f"pay_mock_{uuid.uuid4().hex[:12]}",
            "signature": signature or "mock_signature",
            "status": "paid",
        }

    if PAYMENT_PROVIDER == "phonepe":
        if settings.ENVIRONMENT.lower() != "production" and order_id.startswith("order_mock_"):
            return {
                "verified": True,
                "provider": "phonepe",
                "payment_id": payment_id or f"pay_mock_{uuid.uuid4().hex[:12]}",
                "signature": signature or "mock_signature",
                "status": "paid",
            }
        status_url = settings.PHONEPE_STATUS_URL_TEMPLATE.format(order_id=order_id)
        response = _http_json_request(
            "GET",
            status_url,
            headers=_phonepe_headers(),
        )
        response_data = response.get("data") if isinstance(response.get("data"), dict) else {}
        state = str(
            response.get("state")
            or response.get("status")
            or response.get("orderState")
            or response.get("paymentState")
            or response_data.get("state")
            or response_data.get("paymentState")
            or ""
        ).upper()
        payment_details = response.get("paymentDetails") or response_data.get("paymentDetails") or {}
        if isinstance(payment_details, list):
            payment_details = payment_details[0] if payment_details else {}
        pg_payment_id = (
            payment_details.get("transactionId")
            or payment_details.get("paymentId")
            or response.get("transactionId")
            or response_data.get("transactionId")
            or order_id
        )
        verified = state in {"COMPLETED", "SUCCESS", "PAID"}
        return {
            "verified": verified,
            "provider": "phonepe",
            "payment_id": str(pg_payment_id),
            "signature": state,
            "status": state or "UNKNOWN",
            "raw": response,
        }

    if not payment_id or not signature:
        raise HTTPException(status_code=400, detail="Missing payment_id or signature")

    razorpay_secret = razorpay_client.auth[1]
    generated_signature = hmac.new(
        razorpay_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "verified": generated_signature == signature,
        "provider": "razorpay",
        "payment_id": payment_id,
        "signature": signature,
        "status": "paid",
    }


def public_payment_config() -> dict[str, str]:
    if PAYMENT_PROVIDER == "phonepe":
        return {"provider": "phonepe"}
    if not RAZORPAY_KEY_ID:
        raise HTTPException(status_code=500, detail="Razorpay key is not configured")
    return {"provider": "razorpay", "razorpay_key_id": RAZORPAY_KEY_ID}
