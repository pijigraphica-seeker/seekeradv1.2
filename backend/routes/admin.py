from fastapi import APIRouter, HTTPException, Request, Query
from models.user import UserRole
from routes.auth import get_current_user
from datetime import datetime, timezone
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
async def get_admin_stats(request: Request):
    """Get admin dashboard statistics"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get counts
    total_users = await db.users.count_documents({})
    total_trips = await db.trips.count_documents({"status": "active"})
    total_bookings = await db.bookings.count_documents({})
    pending_hosts = await db.host_applications.count_documents({"status": "pending"})
    
    # Get revenue
    bookings = await db.bookings.find(
        {"payment_status": {"$in": ["partial", "completed"]}},
        {"paid_amount": 1, "_id": 0}
    ).to_list(length=1000)
    total_revenue = sum(b.get("paid_amount", 0) for b in bookings)
    
    # Recent bookings
    recent_bookings = await db.bookings.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(length=5)
    
    return {
        "total_users": total_users,
        "total_trips": total_trips,
        "total_bookings": total_bookings,
        "pending_hosts": pending_hosts,
        "total_revenue": total_revenue,
        "recent_bookings": recent_bookings
    }


@router.get("/users")
async def get_all_users(
    request: Request,
    role: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get all users (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if role:
        query["role"] = role
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"client_id": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.users.count_documents(query)
    pages = math.ceil(total / limit) if total > 0 else 1
    
    skip = (page - 1) * limit
    cursor = db.users.find(
        query,
        {"_id": 0, "password_hash": 0}
    ).sort("created_at", -1).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "pages": pages
    }


@router.get("/bookings")
async def get_all_bookings(
    request: Request,
    status: str = Query(None),
    payment_status: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get all bookings (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["booking_status"] = status
    if payment_status:
        query["payment_status"] = payment_status
    
    total = await db.bookings.count_documents(query)
    pages = math.ceil(total / limit) if total > 0 else 1
    
    skip = (page - 1) * limit
    cursor = db.bookings.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    bookings = await cursor.to_list(length=limit)
    
    return {
        "bookings": bookings,
        "total": total,
        "page": page,
        "pages": pages
    }


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, request: Request):
    """Update user role (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "role": role,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User role updated to {role}"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    """Delete a user (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Clean up sessions
    await db.user_sessions.delete_many({"user_id": user_id})
    
    return {"message": "User deleted successfully"}


@router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str, request: Request):
    """Delete a booking (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.bookings.delete_one({"booking_id": booking_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return {"message": "Booking deleted successfully"}



@router.put("/bookings/{booking_id}/status")
async def update_booking_status(booking_id: str, status: str, request: Request):
    """Update booking status (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_statuses = ["pending", "confirmed", "cancelled", "completed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    result = await db.bookings.update_one(
        {"booking_id": booking_id},
        {"$set": {
            "booking_status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return {"message": f"Booking status updated to {status}"}


@router.put("/bookings/{booking_id}/payment-confirm")
async def confirm_bank_transfer(booking_id: str, payment_id: str, request: Request):
    """Confirm bank transfer payment (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    
    # Update payment status
    await db.bookings.update_one(
        {"booking_id": booking_id, "payments.payment_id": payment_id},
        {"$set": {
            "payments.$.status": "completed",
            "payments.$.paid_at": now.isoformat(),
            "updated_at": now.isoformat()
        }}
    )
    
    # Recalculate booking totals
    booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if booking:
        total_paid = sum(
            p["amount"] for p in booking.get("payments", [])
            if p["status"] == "completed"
        )
        remaining = booking["total_amount"] - total_paid
        
        payment_status = "completed" if remaining <= 0 else "partial"
        booking_status = "confirmed" if total_paid > 0 else "pending"
        
        await db.bookings.update_one(
            {"booking_id": booking_id},
            {"$set": {
                "paid_amount": total_paid,
                "remaining_amount": max(0, remaining),
                "payment_status": payment_status,
                "booking_status": booking_status
            }}
        )
    
    return {"message": "Payment confirmed"}


@router.put("/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status: str = Query(...),
    request: Request = None
):
    """Update booking status (admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    valid_statuses = ["pending", "confirmed", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    result = await db.bookings.update_one(
        {"booking_id": booking_id},
        {"$set": {
            "booking_status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return {"message": f"Booking status updated to {status}"}


@router.get("/trip-bookings/{trip_id}")
async def admin_get_trip_bookings(trip_id: str, request: Request, date: str = Query(None)):
    """Admin: Get all bookings for a specific trip, optionally filtered by date"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    query = {"trip_id": trip_id, "booking_status": {"$ne": "cancelled"}}
    if date:
        query["start_date"] = date

    bookings = await db.bookings.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)

    for b in bookings:
        user = await db.users.find_one({"user_id": b["user_id"]}, {"_id": 0, "password_hash": 0})
        if user:
            b["user_name"] = user.get("name", "")
            b["user_email"] = user.get("email", "")
            b["client_id"] = user.get("client_id", "")

    return {"bookings": bookings, "total": len(bookings)}


@router.get("/upcoming-trips")
async def admin_upcoming_trips(request: Request):
    """Admin: Get all upcoming open trip dates with registration counts"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    trips = await db.trips.find({"status": "active"}, {"_id": 0}).to_list(100)

    upcoming = []
    for trip in trips:
        dates = trip.get("open_trip_dates", [])
        for date_str in dates:
            booking_count = await db.bookings.count_documents({
                "trip_id": trip["trip_id"], "start_date": date_str, "booking_status": {"$ne": "cancelled"}
            })
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
                "location": trip.get("location", ""),
                "host_id": trip.get("host_id", "")
            })

    upcoming.sort(key=lambda x: x["date"])
    return {"upcoming": upcoming}


@router.put("/trips/{trip_id}/toggle-status")
async def admin_toggle_trip_status(trip_id: str, request: Request):
    """Admin: Toggle trip between active/inactive"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    trip = await db.trips.find_one({"trip_id": trip_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    new_status = "inactive" if trip.get("status") == "active" else "active"
    await db.trips.update_one(
        {"trip_id": trip_id},
        {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    return {"message": f"Trip status changed to {new_status}", "status": new_status}


@router.put("/trips/{trip_id}/toggle-featured")
async def admin_toggle_trip_featured(trip_id: str, request: Request):
    """Admin: Toggle trip featured status"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    trip = await db.trips.find_one({"trip_id": trip_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    new_featured = not trip.get("featured", False)
    await db.trips.update_one(
        {"trip_id": trip_id},
        {"$set": {"featured": new_featured, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    return {"message": f"Trip {'featured' if new_featured else 'unfeatured'}", "featured": new_featured}
