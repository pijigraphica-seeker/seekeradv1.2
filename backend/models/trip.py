from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class ActivityType(str, Enum):
    HIKING = "hiking"
    CAMPING = "camping"
    DIVING = "diving"
    KAYAKING = "kayaking"
    CANYONING = "canyoning"
    PARAGLIDING = "paragliding"


class Difficulty(str, Enum):
    EASY = "Easy"
    MODERATE = "Moderate"
    CHALLENGING = "Challenging"


class TripType(str, Enum):
    OPEN = "open"
    PRIVATE = "private"
    BOTH = "both"


class TripStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ItineraryDay(BaseModel):
    """Model for a single day in the trip itinerary"""
    day: int
    title: str
    activities: List[str] = []
    meals: Optional[str] = None
    accommodation: Optional[str] = None
    distance: Optional[str] = None
    elevation: Optional[str] = None


class TripCreate(BaseModel):
    """Request model for creating a new trip"""
    title: str
    description: str
    location: str
    activity_type: ActivityType
    duration: str  # e.g., "3D2N", "5D4N"
    difficulty: Difficulty
    price: float
    deposit_price: float
    currency: str = "RM"
    images: List[str] = []
    max_guests: int
    trip_type: TripType = TripType.BOTH
    open_trip_dates: List[str] = []  # ISO date strings
    included: List[str] = []
    meeting_point: str
    itinerary: List[ItineraryDay] = []
    has_insurance: bool = True


class TripUpdate(BaseModel):
    """Request model for updating a trip"""
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    activity_type: Optional[ActivityType] = None
    duration: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    price: Optional[float] = None
    deposit_price: Optional[float] = None
    images: Optional[List[str]] = None
    max_guests: Optional[int] = None
    trip_type: Optional[TripType] = None
    open_trip_dates: Optional[List[str]] = None
    included: Optional[List[str]] = None
    meeting_point: Optional[str] = None
    itinerary: Optional[List[ItineraryDay]] = None
    status: Optional[TripStatus] = None
    featured: Optional[bool] = None
    has_insurance: Optional[bool] = None


class Trip(BaseModel):
    """Complete trip model for responses"""
    model_config = ConfigDict(extra="ignore")
    
    trip_id: str
    title: str
    description: str
    location: str
    activity_type: ActivityType
    duration: str
    difficulty: Difficulty
    price: float
    deposit_price: float
    currency: str = "RM"
    images: List[str] = []
    max_guests: int
    trip_type: TripType
    open_trip_dates: List[str] = []
    included: List[str] = []
    meeting_point: str
    itinerary: List[ItineraryDay] = []
    host_id: Optional[str] = None
    featured: bool = False
    has_insurance: bool = True
    status: TripStatus = TripStatus.ACTIVE
    rating: float = 0.0
    review_count: int = 0
    created_at: datetime
    updated_at: datetime


class TripListResponse(BaseModel):
    """Response model for paginated trip list"""
    trips: List[Trip]
    total: int
    page: int
    pages: int
