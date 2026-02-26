from fastapi import APIRouter, HTTPException, Request, Query
import requests
from models.booking import (
    Booking, BookingCreate, PaymentCreate, BookingListResponse,
    BookingStatus, PaymentStatus, PaymentMethod, PaymentRecord,
    BillplzWebhookPayload
)
from routes.auth import get_current_user
from datetime import datetime, timezone
import uuid
import math
import requests
from requests.auth import HTTPBasicAuth
import hmac
import hashlib
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bookings", tags=["Bookings"])

# Billplz configuration - read at request time
def get_billplz_config():
    return {
        "api_key": os.environ.get("BILLPLZ_API_KEY"),
        "collection_id": os.environ.get("BILLPLZ_COLLECTION_ID"),
        "sandbox": os.environ.get("BILLPLZ_SANDBOX", "true").lower() == "true",
        "x_signature_key": os.environ.get("BILLPLZ_X_SIGNATURE_KEY", "")
    }

def get_billplz_base_url():
    sandbox = os.environ.get("BILLPLZ_SANDBOX", "true").lower() == "true"
    return "https://www.billplz-sandbox.com/api" if sandbox else "https://www.billplz.com/api"

# Stripe configuration
def get_stripe_key():
    return os.environ.get("STRIPE_API_KEY")

# Bayarcash configuration
def get_bayarcash_config():
    return {
        "api_token": os.environ.get("BAYARCASH_API_TOKEN"),
        "portal_key": os.environ.get("BAYARCASH_PORTAL_KEY", ""),
        "sandbox": os.environ.get("BAYARCASH_SANDBOX", "false").lower() == "true"
    }

def get_bayarcash_base_url():
    sandbox = os.environ.get("BAYARCASH_SANDBOX", "false").lower() == "true"
    return "https://console.bayarcash-sandbox.com/api/v2" if sandbox else "https://console.bayar.cash/api/v2"

# Payment processing fees
BILLPLZ_FEE = 1.50  # RM1.50 flat fee
STRIPE_FEE_PERCENT = 4.0  # 4% fee


async def get_next_booking_id(db) -> str:
    counter = await db.counters.find_one_and_update(
        {"_id": "booking_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
        projection={"_id": 0}
    )
    seq = counter.get("seq", 1)
    return f"BK-{seq:06d}"


@router.post("", response_model=Booking)
async def create_booking(booking_data: BookingCreate, request: Request):
    db = request.app.state.db
    current_user = await get_current_user(request)

    trip = await db.trips.find_one({"trip_id": booking_data.trip_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if booking_data.guests > trip.get("max_guests", 12):
        raise HTTPException(status_code=400, detail=f"Maximum {trip['max_guests']} guests allowed")

    if len(booking_data.participant_details) != booking_data.guests:
        raise HTTPException(status_code=400, detail="Participant details must match number of guests")

    price_per_person = trip.get("price", 0)
    deposit_per_person = trip.get("deposit_price", 50)
    total_amount = price_per_person * booking_data.guests

    if booking_data.payment_type == "deposit":
        initial_amount = deposit_per_person * booking_data.guests
    else:
        initial_amount = total_amount

    booking_id = await get_next_booking_id(db)
    now = datetime.now(timezone.utc)

    booking_doc = {
        "booking_id": booking_id,
        "user_id": current_user.user_id,
        "trip_id": booking_data.trip_id,
        "trip_title": trip.get("title", ""),
        "trip_image": trip.get("images", [None])[0] if trip.get("images") else None,
        "trip_type": booking_data.trip_type,
        "start_date": booking_data.start_date,
        "guests": booking_data.guests,
        "total_amount": total_amount,
        "deposit_amount": deposit_per_person * booking_data.guests,
        "paid_amount": 0,
        "remaining_amount": total_amount,
        "currency": trip.get("currency", "RM"),
        "payment_type": booking_data.payment_type,
        "payment_status": PaymentStatus.PENDING.value,
        "booking_status": BookingStatus.PENDING.value,
        "participant_details": [p.model_dump() for p in booking_data.participant_details],
        "payments": [],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    await db.bookings.insert_one(booking_doc)

    # Send booking confirmation email (non-blocking)
    try:
        from services.email_service import send_booking_confirmation
        import asyncio
        asyncio.create_task(send_booking_confirmation(
            booking_doc, trip, current_user.email, current_user.name
        ))
    except Exception as e:
        logger.warning(f"Failed to queue booking email: {e}")

    booking_doc["created_at"] = now
    booking_doc["updated_at"] = now

    return Booking(**booking_doc)


@router.get("/my-bookings", response_model=BookingListResponse)
async def get_my_bookings(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    db = request.app.state.db
    current_user = await get_current_user(request)

    query = {"user_id": current_user.user_id}
    if status:
        query["booking_status"] = status

    total = await db.bookings.count_documents(query)
    pages = math.ceil(total / limit) if total > 0 else 1

    skip = (page - 1) * limit
    cursor = db.bookings.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    booking_docs = await cursor.to_list(length=limit)

    bookings = []
    for doc in booking_docs:
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        bookings.append(Booking(**doc))

    return BookingListResponse(bookings=bookings, total=total, page=page, pages=pages)


@router.get("/{booking_id}", response_model=Booking)
async def get_booking(booking_id: str, request: Request):
    db = request.app.state.db
    current_user = await get_current_user(request)

    booking_doc = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking_doc["user_id"] != current_user.user_id and current_user.role not in ["admin", "host"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if isinstance(booking_doc.get("created_at"), str):
        booking_doc["created_at"] = datetime.fromisoformat(booking_doc["created_at"])
    if isinstance(booking_doc.get("updated_at"), str):
        booking_doc["updated_at"] = datetime.fromisoformat(booking_doc["updated_at"])

    return Booking(**booking_doc)


@router.post("/{booking_id}/pay")
async def create_payment(booking_id: str, payment_data: PaymentCreate, request: Request):
    db = request.app.state.db
    current_user = await get_current_user(request)

    booking_doc = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking_doc["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if booking_doc["payment_status"] == PaymentStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Booking is already fully paid")

    # Validate amount
    remaining = booking_doc["total_amount"] - booking_doc.get("paid_amount", 0)
    if payment_data.amount > remaining:
        raise HTTPException(status_code=400, detail=f"Amount exceeds remaining balance of {remaining}")
    if payment_data.amount < 2:
        raise HTTPException(status_code=400, detail="Minimum payment amount is RM2")

    # Calculate processing fees
    processing_fee = 0.0
    if payment_data.payment_method == PaymentMethod.BILLPLZ:
        processing_fee = BILLPLZ_FEE  # RM1.50
    elif payment_data.payment_method == PaymentMethod.STRIPE:
        processing_fee = round(payment_data.amount * (STRIPE_FEE_PERCENT / 100), 2)  # 4%
    elif payment_data.payment_method == PaymentMethod.BAYARCASH:
        processing_fee = 0.0  # No extra fee for Bayarcash

    charge_amount = round(payment_data.amount + processing_fee, 2)

    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    if payment_data.payment_method == PaymentMethod.BILLPLZ:
        amount_cents = int(charge_amount * 100)
        billplz = get_billplz_config()
        base_url = get_billplz_base_url()
        # Derive URLs from request origin for portability
        request_origin = request.headers.get("origin", os.environ.get("FRONTEND_URL", ""))
        backend_base = os.environ.get("BACKEND_URL", request_origin)
        callback_url = f"{backend_base}/api/payments/webhook/billplz"
        redirect_url = f"{request_origin}/bookings/{booking_id}?payment=success"

        try:
            response = requests.post(
                f"{base_url}/v3/bills",
                auth=HTTPBasicAuth(billplz["api_key"], ""),
                data={
                    "collection_id": billplz["collection_id"],
                    "email": current_user.email,
                    "name": current_user.name,
                    "amount": amount_cents,
                    "description": f"Payment for booking {booking_id}",
                    "callback_url": callback_url,
                    "redirect_url": redirect_url,
                    "reference_1_label": "Booking ID",
                    "reference_1": booking_id,
                    "reference_2_label": "Payment ID",
                    "reference_2": payment_id
                },
                timeout=10
            )
            response.raise_for_status()
            bill_data = response.json()

            payment_record = {
                "payment_id": payment_id,
                "bill_id": bill_data["id"],
                "amount": payment_data.amount,
                "processing_fee": processing_fee,
                "charge_amount": charge_amount,
                "payment_method": PaymentMethod.BILLPLZ.value,
                "status": PaymentStatus.PENDING.value,
                "paid_at": None,
                "bill_url": bill_data["url"],
                "created_at": now.isoformat()
            }

            await db.bookings.update_one(
                {"booking_id": booking_id},
                {
                    "$push": {"payments": payment_record},
                    "$set": {"updated_at": now.isoformat()}
                }
            )

            return {
                "payment_id": payment_id,
                "bill_url": bill_data["url"],
                "payment_method": "billplz",
                "amount": payment_data.amount,
                "processing_fee": processing_fee,
                "charge_amount": charge_amount,
                "message": f"Payment bill created (RM{processing_fee:.2f} processing fee included)."
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Billplz API error: {e}")
            raise HTTPException(status_code=500, detail="Failed to create payment bill")

    elif payment_data.payment_method == PaymentMethod.STRIPE:
        # Stripe Checkout
        try:
            from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

            stripe_checkout = StripeCheckout(api_key=get_stripe_key())

            # Build success/cancel URLs from request origin for portability
            request_origin = request.headers.get("origin", os.environ.get("FRONTEND_URL", ""))
            success_url = f"{request_origin}/bookings/{booking_id}?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{request_origin}/bookings/{booking_id}?payment=cancelled"

            checkout_request = CheckoutSessionRequest(
                amount=float(charge_amount),
                currency="myr",
                success_url=success_url,
                cancel_url=cancel_url,
                payment_methods=["card"],
                metadata={
                    "booking_id": booking_id,
                    "payment_id": payment_id,
                    "user_id": current_user.user_id
                }
            )

            logger.info(f"Creating Stripe session for booking {booking_id}, amount={payment_data.amount}")
            session = await stripe_checkout.create_checkout_session(checkout_request)
            logger.info(f"Stripe session created: {session.session_id}")

            payment_record = {
                "payment_id": payment_id,
                "bill_id": session.session_id,
                "amount": payment_data.amount,
                "processing_fee": processing_fee,
                "charge_amount": charge_amount,
                "payment_method": PaymentMethod.STRIPE.value,
                "status": PaymentStatus.PENDING.value,
                "paid_at": None,
                "bill_url": session.url,
                "created_at": now.isoformat()
            }

            await db.bookings.update_one(
                {"booking_id": booking_id},
                {
                    "$push": {"payments": payment_record},
                    "$set": {"updated_at": now.isoformat()}
                }
            )

            # Record in payment_transactions collection
            await db.payment_transactions.insert_one({
                "session_id": session.session_id,
                "payment_id": payment_id,
                "booking_id": booking_id,
                "user_id": current_user.user_id,
                "email": current_user.email,
                "amount": payment_data.amount,
                "currency": "myr",
                "payment_status": "initiated",
                "metadata": {"booking_id": booking_id, "payment_id": payment_id},
                "created_at": now.isoformat()
            })

            return {
                "payment_id": payment_id,
                "bill_url": session.url,
                "session_id": session.session_id,
                "payment_method": "stripe",
                "amount": payment_data.amount,
                "processing_fee": processing_fee,
                "charge_amount": charge_amount,
                "message": f"Stripe checkout created (4% processing fee included)."
            }

        except Exception as e:
            import traceback
            logger.error(f"Stripe checkout error: {e}\n{traceback.format_exc()}")
            error_msg = str(e)
            if "amount_too_small" in error_msg or "at least" in error_msg:
                raise HTTPException(status_code=400, detail="Minimum payment amount for Stripe is RM2.00")
            raise HTTPException(status_code=400, detail=f"Payment failed: {error_msg}")

    elif payment_data.payment_method == PaymentMethod.BAYARCASH:
        # Bayarcash Payment
        try:
            bayarcash = get_bayarcash_config()
            bayarcash_url = get_bayarcash_base_url()
            request_origin = request.headers.get("origin", os.environ.get("FRONTEND_URL", ""))

            callback_url = f"{os.environ.get('BACKEND_URL', request_origin)}/api/webhooks/bayarcash"
            return_url = f"{request_origin}/bookings/{booking_id}?payment=success"

            payload = {
                "portal_key": bayarcash["portal_key"],
                "order_number": f"{booking_id}-{payment_id}",
                "amount": int(charge_amount * 100),
                "payer_name": current_user.name,
                "payer_email": current_user.email,
                "payer_telephone_number": current_user.phone or "0000000000",
                "payment_channel": "1",
                "callback_url": callback_url,
                "return_url": return_url
            }

            headers = {
                "Authorization": f"Bearer {bayarcash['api_token']}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            resp = requests.post(
                f"{bayarcash_url}/payment-intents",
                json=payload,
                headers=headers,
                timeout=15
            )
            resp.raise_for_status()
            bc_data = resp.json()

            payment_url = bc_data.get("url") or bc_data.get("payment_url") or bc_data.get("data", {}).get("url", "")

            payment_record = {
                "payment_id": payment_id,
                "bill_id": bc_data.get("id") or bc_data.get("transaction_id", ""),
                "amount": payment_data.amount,
                "processing_fee": 0,
                "charge_amount": charge_amount,
                "payment_method": PaymentMethod.BAYARCASH.value,
                "status": PaymentStatus.PENDING.value,
                "paid_at": None,
                "bill_url": payment_url,
                "created_at": now.isoformat()
            }

            await db.bookings.update_one(
                {"booking_id": booking_id},
                {
                    "$push": {"payments": payment_record},
                    "$set": {"updated_at": now.isoformat()}
                }
            )

            return {
                "payment_id": payment_id,
                "bill_url": payment_url,
                "payment_method": "bayarcash",
                "amount": payment_data.amount,
                "processing_fee": 0,
                "charge_amount": charge_amount,
                "message": "Bayarcash payment created. No processing fee."
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Bayarcash API error: {e}")
            raise HTTPException(status_code=400, detail=f"Bayarcash payment failed: {str(e)}")

    else:  # Bank Transfer
        payment_record = {
            "payment_id": payment_id,
            "bill_id": None,
            "amount": payment_data.amount,
            "payment_method": PaymentMethod.BANK_TRANSFER.value,
            "status": PaymentStatus.PENDING.value,
            "paid_at": None,
            "bill_url": None,
            "created_at": now.isoformat()
        }

        await db.bookings.update_one(
            {"booking_id": booking_id},
            {
                "$push": {"payments": payment_record},
                "$set": {"updated_at": now.isoformat()}
            }
        )

        return {
            "payment_id": payment_id,
            "payment_method": "bank_transfer",
            "bank_details": {
                "bank_name": "Maybank",
                "account_number": "5123 4567 8901",
                "account_name": "Seeker Adventure Sdn Bhd",
                "reference": booking_id
            },
            "message": "Please transfer to the bank account and upload proof of payment."
        }


@router.get("/{booking_id}/payment-status/{session_id}")
async def check_stripe_payment_status(booking_id: str, session_id: str, request: Request):
    """Poll Stripe checkout status and update booking"""
    db = request.app.state.db
    current_user = await get_current_user(request)

    booking_doc = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking_doc["user_id"] != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        from emergentintegrations.payments.stripe.checkout import StripeCheckout

        host_url = str(request.base_url).rstrip("/")
        webhook_url = f"{host_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=get_stripe_key())

        status = await stripe_checkout.get_checkout_status(session_id)

        # Check if already processed
        tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if tx and tx.get("payment_status") == "paid":
            return {"status": "paid", "already_processed": True}

        if status.payment_status == "paid":
            # Update payment_transactions
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid", "status": status.status, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )

            # Find and update the payment record in booking
            now = datetime.now(timezone.utc)
            payment_id = tx.get("payment_id") if tx else None

            if payment_id:
                await db.bookings.update_one(
                    {"booking_id": booking_id, "payments.payment_id": payment_id},
                    {"$set": {
                        "payments.$.status": PaymentStatus.COMPLETED.value,
                        "payments.$.paid_at": now.isoformat(),
                        "updated_at": now.isoformat()
                    }}
                )

                # Recalculate totals
                booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
                if booking:
                    total_paid = sum(
                        p["amount"] for p in booking.get("payments", [])
                        if p["status"] == PaymentStatus.COMPLETED.value
                    )
                    remaining = booking["total_amount"] - total_paid
                    payment_status = PaymentStatus.COMPLETED.value if remaining <= 0 else PaymentStatus.PARTIAL.value
                    booking_status = BookingStatus.CONFIRMED.value if total_paid > 0 else BookingStatus.PENDING.value

                    await db.bookings.update_one(
                        {"booking_id": booking_id},
                        {"$set": {
                            "paid_amount": total_paid,
                            "remaining_amount": max(0, remaining),
                            "payment_status": payment_status,
                            "booking_status": booking_status
                        }}
                    )

        return {
            "status": status.status,
            "payment_status": status.payment_status,
            "amount_total": status.amount_total,
            "currency": status.currency
        }

    except Exception as e:
        logger.error(f"Stripe status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{booking_id}/check-payment")
async def check_billplz_payment(booking_id: str, request: Request):
    """Check and update pending Billplz payments by querying Billplz API"""
    db = request.app.state.db
    current_user = await get_current_user(request)

    booking_doc = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking_doc["user_id"] != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    updated = False
    billplz = get_billplz_config()
    base_url = get_billplz_base_url()

    for payment in booking_doc.get("payments", []):
        if payment["status"] == "pending" and payment["payment_method"] == "billplz" and payment.get("bill_id"):
            try:
                resp = requests.get(
                    f"{base_url}/v3/bills/{payment['bill_id']}",
                    auth=HTTPBasicAuth(billplz["api_key"], ""),
                    timeout=5
                )
                if resp.ok:
                    bill = resp.json()
                    if bill.get("paid"):
                        now = datetime.now(timezone.utc)
                        await db.bookings.update_one(
                            {"booking_id": booking_id, "payments.payment_id": payment["payment_id"]},
                            {"$set": {
                                "payments.$.status": PaymentStatus.COMPLETED.value,
                                "payments.$.paid_at": now.isoformat(),
                                "updated_at": now.isoformat()
                            }}
                        )
                        updated = True
            except Exception as e:
                logger.warning(f"Failed to check Billplz bill {payment['bill_id']}: {e}")

    if updated:
        # Recalculate totals
        booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
        total_paid = sum(p["amount"] for p in booking.get("payments", []) if p["status"] == PaymentStatus.COMPLETED.value)
        remaining = booking["total_amount"] - total_paid
        ps = PaymentStatus.COMPLETED.value if remaining <= 0 else PaymentStatus.PARTIAL.value
        bs = BookingStatus.CONFIRMED.value if total_paid > 0 else BookingStatus.PENDING.value

        await db.bookings.update_one(
            {"booking_id": booking_id},
            {"$set": {"paid_amount": total_paid, "remaining_amount": max(0, remaining), "payment_status": ps, "booking_status": bs}}
        )

    return {"updated": updated, "booking_id": booking_id}



@router.put("/{booking_id}/cancel")
async def cancel_booking(booking_id: str, request: Request):
    db = request.app.state.db
    current_user = await get_current_user(request)

    booking_doc = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking_doc["user_id"] != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    if booking_doc["booking_status"] in [BookingStatus.CANCELLED.value, BookingStatus.COMPLETED.value]:
        raise HTTPException(status_code=400, detail="Cannot cancel this booking")

    await db.bookings.update_one(
        {"booking_id": booking_id},
        {"$set": {
            "booking_status": BookingStatus.CANCELLED.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return {"message": "Booking cancelled successfully"}


# Billplz Webhook Handler
@router.post("/webhook/billplz")
async def billplz_webhook(request: Request):
    db = request.app.state.db

    raw_body = await request.body()
    billplz = get_billplz_config()

    if billplz["x_signature_key"]:
        signature_header = request.headers.get("X-Signature")
        if signature_header:
            expected_signature = hmac.new(
                billplz["x_signature_key"].encode('utf-8'),
                msg=raw_body,
                digestmod=hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, signature_header):
                raise HTTPException(status_code=403, detail="Invalid signature")

    form_data = await request.form()

    bill_id = form_data.get("id")
    paid = form_data.get("paid") == "true"
    booking_id = form_data.get("reference_1")
    payment_id = form_data.get("reference_2")

    if not booking_id:
        logger.warning(f"Webhook received without booking_id: {bill_id}")
        return {"status": "ignored"}

    now = datetime.now(timezone.utc)

    if paid:
        await db.bookings.update_one(
            {"booking_id": booking_id, "payments.payment_id": payment_id},
            {"$set": {
                "payments.$.status": PaymentStatus.COMPLETED.value,
                "payments.$.paid_at": now.isoformat(),
                "updated_at": now.isoformat()
            }}
        )

        booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
        if booking:
            total_paid = sum(
                p["amount"] for p in booking.get("payments", [])
                if p["status"] == PaymentStatus.COMPLETED.value
            )
            remaining = booking["total_amount"] - total_paid

            payment_status = PaymentStatus.COMPLETED.value if remaining <= 0 else PaymentStatus.PARTIAL.value
            booking_status = BookingStatus.CONFIRMED.value if total_paid > 0 else BookingStatus.PENDING.value

            await db.bookings.update_one(
                {"booking_id": booking_id},
                {"$set": {
                    "paid_amount": total_paid,
                    "remaining_amount": max(0, remaining),
                    "payment_status": payment_status,
                    "booking_status": booking_status
                }}
            )

    logger.info(f"Billplz webhook processed: bill={bill_id}, booking={booking_id}, paid={paid}")
    return {"status": "received"}


# Bayarcash Webhook Handler
@router.post("/webhook/bayarcash")
async def bayarcash_webhook(request: Request):
    """Handle Bayarcash payment callback"""
    db = request.app.state.db
    try:
        body = await request.json()
    except Exception:
        body = dict(await request.form())

    logger.info(f"Bayarcash webhook: {body}")

    transaction_id = body.get("transaction_id") or body.get("id", "")
    status = body.get("status") or body.get("payment_status", "")
    order_number = body.get("order_number") or body.get("record_token", "")

    # Extract booking_id from order_number (format: BK-000001-pay_xxxx)
    booking_id = order_number.split("-pay_")[0] if "-pay_" in order_number else ""

    if not booking_id:
        logger.warning(f"Bayarcash webhook: no booking_id from order: {order_number}")
        return {"status": "received"}

    # Check if payment successful
    is_success = str(status).lower() in ["3", "success", "successful", "completed", "paid"]

    if is_success:
        booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
        if booking:
            for i, p in enumerate(booking.get("payments", [])):
                if p.get("payment_method") == "bayarcash" and p.get("status") == "pending":
                    payment_amount = p.get("amount", 0)
                    new_paid = booking.get("paid_amount", 0) + payment_amount
                    total = booking.get("total_amount", 0)

                    update_fields = {
                        f"payments.{i}.status": "completed",
                        f"payments.{i}.paid_at": datetime.now(timezone.utc).isoformat(),
                        f"payments.{i}.transaction_id": transaction_id,
                        "paid_amount": new_paid,
                        "payment_status": "completed" if new_paid >= total else "partial",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    if new_paid >= total:
                        update_fields["booking_status"] = "confirmed"

                    await db.bookings.update_one({"booking_id": booking_id}, {"$set": update_fields})
                    logger.info(f"Bayarcash payment confirmed: {booking_id}, amount: {payment_amount}")
                    break

    return {"status": "received"}
