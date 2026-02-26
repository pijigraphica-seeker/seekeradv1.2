from fastapi import APIRouter, HTTPException, Request
from models.wishlist import WishlistItem, WishlistAdd
from routes.auth import get_current_user
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get("")
async def get_wishlist(request: Request):
    """Get user's wishlist"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    cursor = db.wishlist.find({"user_id": current_user.user_id}, {"_id": 0})
    wishlist_docs = await cursor.to_list(length=100)
    
    items = []
    for doc in wishlist_docs:
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        items.append(WishlistItem(**doc))
    
    return {"wishlist": items}


@router.post("")
async def add_to_wishlist(data: WishlistAdd, request: Request):
    """Add a trip to wishlist"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    # Check if trip exists
    trip = await db.trips.find_one({"trip_id": data.trip_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check if already in wishlist
    existing = await db.wishlist.find_one({
        "user_id": current_user.user_id,
        "trip_id": data.trip_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Trip already in wishlist")
    
    wishlist_doc = {
        "wishlist_id": f"wish_{uuid.uuid4().hex[:12]}",
        "user_id": current_user.user_id,
        "trip_id": data.trip_id,
        "trip_title": trip.get("title", ""),
        "trip_image": trip.get("images", [None])[0] if trip.get("images") else None,
        "trip_price": trip.get("price", 0),
        "trip_location": trip.get("location", ""),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.wishlist.insert_one(wishlist_doc)
    
    return {"message": "Added to wishlist"}


@router.delete("/{trip_id}")
async def remove_from_wishlist(trip_id: str, request: Request):
    """Remove a trip from wishlist"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    result = await db.wishlist.delete_one({
        "user_id": current_user.user_id,
        "trip_id": trip_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")
    
    return {"message": "Removed from wishlist"}


@router.get("/check/{trip_id}")
async def check_wishlist(trip_id: str, request: Request):
    """Check if a trip is in user's wishlist"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    item = await db.wishlist.find_one({
        "user_id": current_user.user_id,
        "trip_id": trip_id
    })
    
    return {"in_wishlist": item is not None}
