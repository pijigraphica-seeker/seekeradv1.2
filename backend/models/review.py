from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ReviewCreate(BaseModel):
    """Request model for creating a review"""
    trip_id: str
    booking_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: str


class Review(BaseModel):
    """Complete review model"""
    model_config = ConfigDict(extra="ignore")
    
    review_id: str
    user_id: str
    user_name: str
    user_avatar: Optional[str] = None
    trip_id: str
    booking_id: str
    rating: int
    comment: str
    created_at: datetime
    updated_at: datetime
