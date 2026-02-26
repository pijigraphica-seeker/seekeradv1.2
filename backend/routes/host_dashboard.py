from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from models.trip import Trip, TripCreate, TripUpdate, TripListResponse, TripStatus
from routes.auth import get_current_user
from datetime import datetime, timezone
import math
import io
import csv
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/host", tags=["Host Dashboard"])


@router.get("/stats")
async def get_host_stats(request: Request):
    """Get stats for the logged-in host only"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role not in ["host", "admin"]:
        raise HTTPException(status_code=403, detail="Host access required")

    host_id = current_user.user_id

    # Count host's trips
    total_trips = await db.trips.count_documents({"host_id": host_id})
    active_trips = await db.trips.count_documents({"host_id": host_id, "status": "active"})

    # Get host's trip IDs
    host_trip_ids = []
    async for t in db.trips.find({"host_id": host_id}, {"trip_id": 1, "_id": 0}):
        host_trip_ids.append(t["trip_id"])

    # Bookings for host's trips
    booking_query = {"trip_id": {"$in": host_trip_ids}} if host_trip_ids else {"trip_id": "__none__"}
    total_bookings = await db.bookings.count_documents(booking_query)
    confirmed_bookings = await db.bookings.count_documents({**booking_query, "booking_status": {"$in": ["confirmed", "completed"]}})

    # Revenue
    pipeline = [
        {"$match": {**booking_query}},
        {"$group": {"_id": None, "total": {"$sum": "$paid_amount"}}}
    ]
    rev_result = await db.bookings.aggregate(pipeline).to_list(1)
    total_revenue = rev_result[0]["total"] if rev_result else 0

    return {
        "total_trips": total_trips,
        "active_trips": active_trips,
        "total_bookings": total_bookings,
        "confirmed_bookings": confirmed_bookings,
        "total_revenue": total_revenue,
        "host_trip_ids": host_trip_ids
    }


@router.get("/my-trips")
async def get_host_trips(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Get trips owned by the logged-in host"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role not in ["host", "admin"]:
        raise HTTPException(status_code=403, detail="Host access required")

    query = {"host_id": current_user.user_id}
    if status:
        query["status"] = status

    total = await db.trips.count_documents(query)
    skip = (page - 1) * limit
    cursor = db.trips.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    trip_docs = await cursor.to_list(length=limit)

    trips = []
    for doc in trip_docs:
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        trips.append(doc)

    return {"trips": trips, "total": total}


@router.get("/my-bookings")
async def get_host_bookings(
    request: Request,
    trip_id: str = Query(None),
    start_date: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Get bookings for host's trips only"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role not in ["host", "admin"]:
        raise HTTPException(status_code=403, detail="Host access required")

    # Get host trip IDs
    host_trip_ids = []
    async for t in db.trips.find({"host_id": current_user.user_id}, {"trip_id": 1, "_id": 0}):
        host_trip_ids.append(t["trip_id"])

    if not host_trip_ids:
        return {"bookings": [], "total": 0}

    query = {"trip_id": {"$in": host_trip_ids}}
    if trip_id:
        query["trip_id"] = trip_id
    if start_date:
        query["start_date"] = start_date

    total = await db.bookings.count_documents(query)
    skip = (page - 1) * limit
    cursor = db.bookings.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    booking_docs = await cursor.to_list(length=limit)

    return {"bookings": booking_docs, "total": total}


@router.get("/upcoming-trips")
async def get_upcoming_trip_dates(request: Request):
    """Get upcoming open trip dates with registration counts"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role not in ["host", "admin"]:
        raise HTTPException(status_code=403, detail="Host access required")

    # Get host's trips
    query = {"host_id": current_user.user_id, "status": "active"}
    trips = await db.trips.find(query, {"_id": 0}).to_list(100)

    upcoming = []
    for trip in trips:
        dates = trip.get("open_trip_dates", [])
        for date_str in dates:
            # Count registrations for this date
            booking_count = await db.bookings.count_documents({
                "trip_id": trip["trip_id"],
                "start_date": date_str,
                "booking_status": {"$ne": "cancelled"}
            })
            # Sum guests
            pipeline = [
                {"$match": {"trip_id": trip["trip_id"], "start_date": date_str, "booking_status": {"$ne": "cancelled"}}},
                {"$group": {"_id": None, "total_guests": {"$sum": "$guests"}}}
            ]
            guest_result = await db.bookings.aggregate(pipeline).to_list(1)
            total_guests = guest_result[0]["total_guests"] if guest_result else 0

            upcoming.append({
                "trip_id": trip["trip_id"],
                "trip_title": trip["title"],
                "trip_image": trip.get("images", [None])[0] if trip.get("images") else None,
                "date": date_str,
                "registered_guests": total_guests,
                "max_guests": trip.get("max_guests", 12),
                "booking_count": booking_count,
                "location": trip.get("location", "")
            })

    # Sort by date
    upcoming.sort(key=lambda x: x["date"])
    return {"upcoming": upcoming}


@router.get("/trip-bookings/{trip_id}/{date}")
async def get_trip_date_bookings(trip_id: str, date: str, request: Request):
    """Get all bookings for a specific trip on a specific date with full user details"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role not in ["host", "admin"]:
        raise HTTPException(status_code=403, detail="Host access required")

    # Verify host owns this trip (unless admin)
    if current_user.role == "host":
        trip = await db.trips.find_one({"trip_id": trip_id, "host_id": current_user.user_id}, {"_id": 0})
        if not trip:
            raise HTTPException(status_code=403, detail="Access denied")

    bookings = await db.bookings.find(
        {"trip_id": trip_id, "start_date": date, "booking_status": {"$ne": "cancelled"}},
        {"_id": 0}
    ).to_list(100)

    # Enrich with user data
    for booking in bookings:
        user = await db.users.find_one({"user_id": booking["user_id"]}, {"_id": 0, "password_hash": 0})
        if user:
            booking["user_name"] = user.get("name", "")
            booking["user_email"] = user.get("email", "")
            booking["user_phone"] = user.get("phone", "")
            booking["client_id"] = user.get("client_id", "")

    return {"bookings": bookings, "total": len(bookings)}


@router.get("/export/{trip_id}/{date}")
async def export_trip_bookings(trip_id: str, date: str, request: Request):
    """Export booking data as CSV for a specific trip date"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role not in ["host", "admin"]:
        raise HTTPException(status_code=403, detail="Host access required")

    if current_user.role == "host":
        trip = await db.trips.find_one({"trip_id": trip_id, "host_id": current_user.user_id}, {"_id": 0})
        if not trip:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        trip = await db.trips.find_one({"trip_id": trip_id}, {"_id": 0})

    bookings = await db.bookings.find(
        {"trip_id": trip_id, "start_date": date, "booking_status": {"$ne": "cancelled"}},
        {"_id": 0}
    ).to_list(100)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Booking ID", "Client ID", "Name", "Email", "Phone", "NRIC",
        "Emergency Contact", "Emergency Phone", "Guests", "Total Amount",
        "Paid Amount", "Remaining", "Payment Status", "Booking Status"
    ])

    for b in bookings:
        user = await db.users.find_one({"user_id": b["user_id"]}, {"_id": 0, "password_hash": 0})
        participants = b.get("participant_details", [])
        if participants:
            for p in participants:
                writer.writerow([
                    b.get("booking_id", ""), p.get("client_id", ""), p.get("name", ""),
                    p.get("email", ""), p.get("phone", ""), p.get("nric", ""),
                    p.get("emergency_contact", ""), p.get("emergency_contact_phone", ""),
                    b.get("guests", 0), b.get("total_amount", 0),
                    b.get("paid_amount", 0), b.get("remaining_amount", 0),
                    b.get("payment_status", ""), b.get("booking_status", "")
                ])
        else:
            writer.writerow([
                b.get("booking_id", ""), user.get("client_id", "") if user else "",
                user.get("name", "") if user else "", user.get("email", "") if user else "",
                "", "", "", "", b.get("guests", 0), b.get("total_amount", 0),
                b.get("paid_amount", 0), b.get("remaining_amount", 0),
                b.get("payment_status", ""), b.get("booking_status", "")
            ])

    output.seek(0)
    trip_title = trip.get("title", trip_id).replace(" ", "_") if trip else trip_id
    filename = f"{trip_title}_{date}_bookings.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
