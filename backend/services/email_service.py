import os
import asyncio
import logging
import resend
from datetime import datetime

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")


def is_email_configured():
    return bool(RESEND_API_KEY and RESEND_API_KEY != "")


async def send_email(to_email: str, subject: str, html_content: str):
    if not is_email_configured():
        logger.warning("Email not configured (RESEND_API_KEY missing). Skipping email send.")
        return None

    resend.api_key = RESEND_API_KEY

    params = {
        "from": SENDER_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }

    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email}: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return None


def generate_booking_confirmation_html(booking: dict, trip: dict, user_name: str) -> str:
    currency = booking.get("currency", "RM")
    total_amount = booking.get("total_amount", 0)
    deposit_amount = booking.get("deposit_amount", 0)
    payment_type = booking.get("payment_type", "deposit")
    amount_due = deposit_amount if payment_type == "deposit" else total_amount
    guests = booking.get("guests", 1)
    start_date = booking.get("start_date", "TBD")
    booking_id = booking.get("booking_id", "")
    trip_title = trip.get("title", booking.get("trip_title", ""))
    trip_location = trip.get("location", "")
    created_at = booking.get("created_at", datetime.now().isoformat())

    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at).strftime("%d %b %Y, %I:%M %p")
        except Exception:
            pass

    participants_html = ""
    for i, p in enumerate(booking.get("participant_details", [])):
        participants_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:14px;">{i+1}. {p.get('name','')}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:14px;">{p.get('email','')}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:14px;">{p.get('phone','')}</td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background-color:#f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f4;padding:20px 0;">
            <tr><td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#EB5A7E,#F5A623);padding:30px;text-align:center;">
                            <h1 style="color:#fff;margin:0;font-size:24px;">Seeker Adventure</h1>
                            <p style="color:rgba(255,255,255,0.9);margin:8px 0 0;font-size:14px;">Booking Confirmation</p>
                        </td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td style="padding:30px;">
                            <p style="font-size:16px;color:#333;">Hi {user_name},</p>
                            <p style="font-size:14px;color:#666;line-height:1.6;">
                                Thank you for booking with Seeker Adventure! Your adventure awaits.
                            </p>

                            <!-- Invoice Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;margin:20px 0;">
                                <tr>
                                    <td style="padding:20px;">
                                        <h2 style="margin:0 0 15px;font-size:18px;color:#EB5A7E;">Invoice #{booking_id}</h2>
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding:6px 0;font-size:14px;color:#666;">Trip:</td>
                                                <td style="padding:6px 0;font-size:14px;color:#333;font-weight:bold;text-align:right;">{trip_title}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:6px 0;font-size:14px;color:#666;">Location:</td>
                                                <td style="padding:6px 0;font-size:14px;color:#333;text-align:right;">{trip_location}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:6px 0;font-size:14px;color:#666;">Date:</td>
                                                <td style="padding:6px 0;font-size:14px;color:#333;text-align:right;">{start_date}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:6px 0;font-size:14px;color:#666;">Guests:</td>
                                                <td style="padding:6px 0;font-size:14px;color:#333;text-align:right;">{guests} person(s)</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:6px 0;font-size:14px;color:#666;">Booking Date:</td>
                                                <td style="padding:6px 0;font-size:14px;color:#333;text-align:right;">{created_at}</td>
                                            </tr>
                                            <tr><td colspan="2"><hr style="border:none;border-top:1px solid #e5e7eb;margin:10px 0;"></td></tr>
                                            <tr>
                                                <td style="padding:6px 0;font-size:14px;color:#666;">Total Trip Price:</td>
                                                <td style="padding:6px 0;font-size:14px;color:#333;text-align:right;">{currency}{total_amount:,.2f}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:6px 0;font-size:14px;color:#666;">Payment Type:</td>
                                                <td style="padding:6px 0;font-size:14px;color:#333;text-align:right;">{"Deposit" if payment_type == "deposit" else "Full Payment"}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:8px 0;font-size:16px;color:#333;font-weight:bold;">Amount Due Now:</td>
                                                <td style="padding:8px 0;font-size:18px;color:#EB5A7E;font-weight:bold;text-align:right;">{currency}{amount_due:,.2f}</td>
                                            </tr>
                                            {"<tr><td colspan='2' style='padding:6px 0;font-size:12px;color:#F5A623;'>Remaining balance: " + currency + str(total_amount - deposit_amount) + " (payable in installments, min RM100/month)</td></tr>" if payment_type == "deposit" else ""}
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- Participants -->
                            <h3 style="font-size:16px;color:#333;margin:20px 0 10px;">Participants</h3>
                            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;">
                                <tr style="background:#f3f4f6;">
                                    <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Name</th>
                                    <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Email</th>
                                    <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Phone</th>
                                </tr>
                                {participants_html}
                            </table>

                            <p style="font-size:13px;color:#999;margin-top:20px;line-height:1.5;">
                                All bookings are non-refundable as per our Terms & Conditions.
                                Full payment is required 1 month before the trip date.
                            </p>

                            <!-- CTA -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin:25px 0;">
                                <tr><td align="center">
                                    <a href="{os.environ.get('FRONTEND_URL', '')}/bookings/{booking_id}"
                                       style="display:inline-block;padding:12px 30px;background:#EB5A7E;color:#fff;text-decoration:none;border-radius:25px;font-weight:bold;font-size:14px;">
                                        View Booking & Make Payment
                                    </a>
                                </td></tr>
                            </table>

                            <!-- WhatsApp -->
                            <p style="font-size:13px;color:#666;text-align:center;">
                                Need help? <a href="https://wa.me/601170001232" style="color:#25D366;text-decoration:none;font-weight:bold;">Chat with us on WhatsApp</a>
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background:#1f2937;padding:20px;text-align:center;">
                            <p style="color:#9ca3af;font-size:12px;margin:0;">Seeker Adventure Sdn Bhd</p>
                            <p style="color:#6b7280;font-size:11px;margin:5px 0 0;">sales@seekeradventure.com | +60 11-7000 1232</p>
                        </td>
                    </tr>
                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """


async def send_booking_confirmation(booking: dict, trip: dict, user_email: str, user_name: str):
    subject = f"Booking Confirmed - {trip.get('title', booking.get('trip_title', 'Adventure'))} | Seeker Adventure"
    html = generate_booking_confirmation_html(booking, trip, user_name)
    return await send_email(user_email, subject, html)
