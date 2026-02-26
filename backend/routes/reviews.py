from fastapi import APIRouter, HTTPException, Request, Query
from models.review import ReviewCreate, Review
from routes.auth import get_current_user
from datetime import datetime, timezone
import uuid
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("")
async def create_review(review_data: ReviewCreate, request: Request):
    db = request.app.state.db
    current_user = await get_current_user(request)

    # Check if user has a confirmed booking for this trip
    booking = await db.bookings.find_one({
        "booking_id": review_data.booking_id,
        "user_id": current_user.user_id,
        "trip_id": review_data.trip_id,
        "booking_status": {"$in": ["confirmed", "completed"]}
    }, {"_id": 0})

    if not booking:
        raise HTTPException(status_code=400, detail="You can only review trips you have a confirmed booking for")

    # Check if user already reviewed this trip
    existing = await db.reviews.find_one({
        "user_id": current_user.user_id,
        "trip_id": review_data.trip_id
    }, {"_id": 0})

    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this trip")

    now = datetime.now(timezone.utc)
    review_id = f"rev_{uuid.uuid4().hex[:12]}"

    review_doc = {
        "review_id": review_id,
        "user_id": current_user.user_id,
        "user_name": current_user.name,
        "user_avatar": current_user.avatar,
        "trip_id": review_data.trip_id,
        "booking_id": review_data.booking_id,
        "rating": review_data.rating,
        "comment": review_data.comment,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    await db.reviews.insert_one(review_doc)

    # Update trip's average rating
    pipeline = [
        {"$match": {"trip_id": review_data.trip_id}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    result = await db.reviews.aggregate(pipeline).to_list(1)
    if result:
        avg_rating = round(result[0]["avg_rating"], 1)
        review_count = result[0]["count"]
        await db.trips.update_one(
            {"trip_id": review_data.trip_id},
            {"$set": {"rating": avg_rating, "review_count": review_count}}
        )

    review_doc.pop("_id", None)
    return {"message": "Review submitted successfully", "review": review_doc}


@router.get("/trip/{trip_id}")
async def get_trip_reviews(
    trip_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    db = request.app.state.db

    total = await db.reviews.count_documents({"trip_id": trip_id})
    pages = math.ceil(total / limit) if total > 0 else 1

    skip = (page - 1) * limit
    cursor = db.reviews.find(
        {"trip_id": trip_id}, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit)

    reviews = await cursor.to_list(length=limit)

    # Get rating breakdown
    pipeline = [
        {"$match": {"trip_id": trip_id}},
        {"$group": {"_id": "$rating", "count": {"$sum": 1}}}
    ]
    breakdown_result = await db.reviews.aggregate(pipeline).to_list(5)
    rating_breakdown = {str(i): 0 for i in range(1, 6)}
    for item in breakdown_result:
        rating_breakdown[str(item["_id"])] = item["count"]

    avg_pipeline = [
        {"$match": {"trip_id": trip_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}}
    ]
    avg_result = await db.reviews.aggregate(avg_pipeline).to_list(1)
    avg_rating = round(avg_result[0]["avg"], 1) if avg_result else 0

    return {
        "reviews": reviews,
        "total": total,
        "page": page,
        "pages": pages,
        "average_rating": avg_rating,
        "rating_breakdown": rating_breakdown
    }


@router.get("/my-reviews")
async def get_my_reviews(request: Request):
    db = request.app.state.db
    current_user = await get_current_user(request)

    cursor = db.reviews.find(
        {"user_id": current_user.user_id}, {"_id": 0}
    ).sort("created_at", -1)
    reviews = await cursor.to_list(length=50)

    return {"reviews": reviews}


@router.delete("/{review_id}")
async def delete_review(review_id: str, request: Request):
    db = request.app.state.db
    current_user = await get_current_user(request)

    review = await db.reviews.find_one({"review_id": review_id}, {"_id": 0})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review["user_id"] != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    trip_id = review["trip_id"]
    await db.reviews.delete_one({"review_id": review_id})

    # Recalculate trip rating
    pipeline = [
        {"$match": {"trip_id": trip_id}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    result = await db.reviews.aggregate(pipeline).to_list(1)
    if result:
        await db.trips.update_one(
            {"trip_id": trip_id},
            {"$set": {"rating": round(result[0]["avg_rating"], 1), "review_count": result[0]["count"]}}
        )
    else:
        await db.trips.update_one(
            {"trip_id": trip_id},
            {"$set": {"rating": 0, "review_count": 0}}
        )

    return {"message": "Review deleted successfully"}


@router.get("/admin/all")
async def admin_get_all_reviews(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get all reviews (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)

    if current_user.role not in ["admin", "webdev"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    total = await db.reviews.count_documents({})
    pages = math.ceil(total / limit) if total > 0 else 1

    skip = (page - 1) * limit
    cursor = db.reviews.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    reviews = await cursor.to_list(length=limit)

    # Enrich with trip titles
    for r in reviews:
        trip = await db.trips.find_one({"trip_id": r.get("trip_id")}, {"_id": 0, "title": 1})
        r["trip_title"] = trip["title"] if trip else "Unknown"

    return {"reviews": reviews, "total": total, "page": page, "pages": pages}


@router.put("/admin/{review_id}")
async def admin_update_review(review_id: str, request: Request):
    """Edit a review (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)

    if current_user.role not in ["admin", "webdev"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    body = await request.json()
    review = await db.reviews.find_one({"review_id": review_id}, {"_id": 0})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    update_fields = {}
    if "rating" in body:
        update_fields["rating"] = int(body["rating"])
    if "comment" in body:
        update_fields["comment"] = body["comment"]
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.reviews.update_one({"review_id": review_id}, {"$set": update_fields})

    # Recalculate trip rating
    trip_id = review["trip_id"]
    pipeline = [
        {"$match": {"trip_id": trip_id}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    result = await db.reviews.aggregate(pipeline).to_list(1)
    if result:
        await db.trips.update_one(
            {"trip_id": trip_id},
            {"$set": {"rating": round(result[0]["avg_rating"], 1), "review_count": result[0]["count"]}}
        )

    return {"message": "Review updated successfully"}


@router.post("/admin/create")
async def admin_create_review(request: Request):
    """Create a review as admin (no booking check)"""
    db = request.app.state.db
    current_user = await get_current_user(request)

    if current_user.role not in ["admin", "webdev"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    body = await request.json()
    trip_id = body.get("trip_id")
    if not trip_id:
        raise HTTPException(status_code=400, detail="trip_id is required")

    trip = await db.trips.find_one({"trip_id": trip_id}, {"_id": 0, "title": 1})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    now = datetime.now(timezone.utc)
    review_id = f"rev_{uuid.uuid4().hex[:12]}"

    review_doc = {
        "review_id": review_id,
        "user_id": current_user.user_id,
        "user_name": body.get("user_name", current_user.name),
        "user_avatar": None,
        "trip_id": trip_id,
        "booking_id": None,
        "rating": int(body.get("rating", 5)),
        "comment": body.get("comment", ""),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "admin_created": True
    }

    await db.reviews.insert_one(review_doc)

    # Recalculate trip rating
    pipeline = [
        {"$match": {"trip_id": trip_id}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    result = await db.reviews.aggregate(pipeline).to_list(1)
    if result:
        await db.trips.update_one(
            {"trip_id": trip_id},
            {"$set": {"rating": round(result[0]["avg_rating"], 1), "review_count": result[0]["count"]}}
        )

    review_doc.pop("_id", None)
    return {"message": "Review created successfully", "review": review_doc}
