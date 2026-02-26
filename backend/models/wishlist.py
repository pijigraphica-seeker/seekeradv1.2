from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class WishlistItem(BaseModel):
    """Wishlist item model"""
    model_config = ConfigDict(extra="ignore")
    
    wishlist_id: str
    user_id: str
    trip_id: str
    trip_title: str
    trip_image: Optional[str] = None
    trip_price: float
    trip_location: str
    created_at: datetime


class WishlistAdd(BaseModel):
    """Request model for adding to wishlist"""
    trip_id: str
