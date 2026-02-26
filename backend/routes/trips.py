from fastapi import APIRouter, HTTPException, Request, Query
from models.trip import Trip, TripCreate, TripUpdate, TripListResponse, TripStatus
from routes.auth import get_current_user
from datetime import datetime, timezone
import uuid
import logging
import math

import re

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trips", tags=["Trips"])


def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from trip title"""
    slug = title.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


@router.get("", response_model=TripListResponse)
async def get_trips(
    request: Request,
    activity_type: str = Query(None),
    difficulty: str = Query(None),
    search: str = Query(None),
    featured: bool = Query(None),
    sort_by: str = Query("created_at"),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50)
):
    """Get all active trips with filters"""
    db = request.app.state.db
    
    # Build query
    query = {"status": TripStatus.ACTIVE.value}
    
    if activity_type and activity_type != "all":
        query["activity_type"] = activity_type
    
    if difficulty:
        query["difficulty"] = difficulty
    
    if featured is not None:
        query["featured"] = featured
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    # Count total
    total = await db.trips.count_documents(query)
    pages = math.ceil(total / limit) if total > 0 else 1
    
    # Sort options
    sort_options = {
        "created_at": [("created_at", -1)],
        "price_asc": [("price", 1)],
        "price_desc": [("price", -1)],
        "rating": [("rating", -1)],
        "title": [("title", 1)]
    }
    sort = sort_options.get(sort_by, [("created_at", -1)])
    
    # Fetch trips
    skip = (page - 1) * limit
    cursor = db.trips.find(query, {"_id": 0}).sort(sort).skip(skip).limit(limit)
    trip_docs = await cursor.to_list(length=limit)
    
    # Parse dates
    trips = []
    for doc in trip_docs:
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        trips.append(Trip(**doc))
    
    return TripListResponse(trips=trips, total=total, page=page, pages=pages)


@router.get("/by-slug/{slug}")
async def get_trip_by_slug(slug: str, request: Request):
    """Get a single trip by slug"""
    db = request.app.state.db
    
    trip_doc = await db.trips.find_one({"slug": slug}, {"_id": 0})
    
    # Fallback: generate slug on-the-fly and try matching
    if not trip_doc:
        cursor = db.trips.find({"status": "active"}, {"_id": 0})
        async for doc in cursor:
            doc_slug = generate_slug(doc.get("title", ""))
            if doc_slug == slug:
                # Save the slug for future lookups
                await db.trips.update_one({"trip_id": doc["trip_id"]}, {"$set": {"slug": doc_slug}})
                trip_doc = doc
                break
    
    if not trip_doc:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if isinstance(trip_doc.get("created_at"), str):
        trip_doc["created_at"] = datetime.fromisoformat(trip_doc["created_at"])
    if isinstance(trip_doc.get("updated_at"), str):
        trip_doc["updated_at"] = datetime.fromisoformat(trip_doc["updated_at"])
    
    return Trip(**trip_doc)


@router.get("/{trip_id}", response_model=Trip)
async def get_trip(trip_id: str, request: Request):
    """Get a single trip by ID"""
    db = request.app.state.db
    
    trip_doc = await db.trips.find_one({"trip_id": trip_id}, {"_id": 0})
    
    if not trip_doc:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if isinstance(trip_doc.get("created_at"), str):
        trip_doc["created_at"] = datetime.fromisoformat(trip_doc["created_at"])
    if isinstance(trip_doc.get("updated_at"), str):
        trip_doc["updated_at"] = datetime.fromisoformat(trip_doc["updated_at"])
    
    return Trip(**trip_doc)


@router.post("", response_model=Trip)
async def create_trip(trip_data: TripCreate, request: Request):
    """Create a new trip (Host/Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    # Check permissions
    if current_user.role not in ["host", "admin"]:
        raise HTTPException(status_code=403, detail="Only hosts and admins can create trips")
    
    trip_id = f"trip_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    trip_doc = {
        "trip_id": trip_id,
        **trip_data.model_dump(),
        "slug": generate_slug(trip_data.title),
        "host_id": current_user.user_id,
        "featured": False,
        "status": TripStatus.ACTIVE.value,
        "rating": 0.0,
        "review_count": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Convert itinerary to dict
    if "itinerary" in trip_doc:
        trip_doc["itinerary"] = [day.model_dump() if hasattr(day, 'model_dump') else day for day in trip_doc["itinerary"]]
    
    await db.trips.insert_one(trip_doc)
    
    trip_doc["created_at"] = now
    trip_doc["updated_at"] = now
    
    return Trip(**trip_doc)


@router.put("/{trip_id}", response_model=Trip)
async def update_trip(trip_id: str, trip_data: TripUpdate, request: Request):
    """Update a trip (Host/Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    # Get existing trip
    trip_doc = await db.trips.find_one({"trip_id": trip_id}, {"_id": 0})
    if not trip_doc:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check permissions
    if current_user.role != "admin" and trip_doc.get("host_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only update your own trips")
    
    # Build update
    update_data = trip_data.model_dump(exclude_unset=True)
    if not update_data:
        if isinstance(trip_doc.get("created_at"), str):
            trip_doc["created_at"] = datetime.fromisoformat(trip_doc["created_at"])
        if isinstance(trip_doc.get("updated_at"), str):
            trip_doc["updated_at"] = datetime.fromisoformat(trip_doc["updated_at"])
        return Trip(**trip_doc)
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Convert itinerary if present
    if "itinerary" in update_data and update_data["itinerary"]:
        update_data["itinerary"] = [day.model_dump() if hasattr(day, 'model_dump') else day for day in update_data["itinerary"]]
    
    await db.trips.update_one({"trip_id": trip_id}, {"$set": update_data})
    
    # Get updated trip
    trip_doc = await db.trips.find_one({"trip_id": trip_id}, {"_id": 0})
    
    if isinstance(trip_doc.get("created_at"), str):
        trip_doc["created_at"] = datetime.fromisoformat(trip_doc["created_at"])
    if isinstance(trip_doc.get("updated_at"), str):
        trip_doc["updated_at"] = datetime.fromisoformat(trip_doc["updated_at"])
    
    return Trip(**trip_doc)


@router.delete("/{trip_id}")
async def delete_trip(trip_id: str, request: Request):
    """Delete/archive a trip (Host/Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    trip_doc = await db.trips.find_one({"trip_id": trip_id}, {"_id": 0})
    if not trip_doc:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check permissions
    if current_user.role != "admin" and trip_doc.get("host_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own trips")
    
    # Soft delete by archiving
    await db.trips.update_one(
        {"trip_id": trip_id},
        {"$set": {
            "status": TripStatus.ARCHIVED.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Trip archived successfully"}
