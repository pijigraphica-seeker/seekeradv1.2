from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PaymentType(str, Enum):
    DEPOSIT = "deposit"
    FULL = "full"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    BILLPLZ = "billplz"
    STRIPE = "stripe"
    BAYARCASH = "bayarcash"
    BANK_TRANSFER = "bank_transfer"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class BookingTripType(str, Enum):
    OPEN = "open"
    PRIVATE = "private"


class ParticipantDetail(BaseModel):
    """Details of a trip participant"""
    client_id: str  # Seeker Adventure Client ID (e.g., SA-000001)
    name: str
    email: EmailStr
    phone: str
    nric: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class BookingCreate(BaseModel):
    """Request model for creating a new booking"""
    trip_id: str
    trip_type: BookingTripType
    start_date: str  # ISO date string
    guests: int
    payment_type: PaymentType
    participant_details: List[ParticipantDetail]


class PaymentCreate(BaseModel):
    """Request model for creating a payment"""
    booking_id: str
    amount: float  # in RM
    payment_method: PaymentMethod


class PaymentRecord(BaseModel):
    """Record of a single payment"""
    payment_id: str
    bill_id: Optional[str] = None  # Billplz bill ID
    amount: float
    payment_method: PaymentMethod
    status: PaymentStatus
    paid_at: Optional[datetime] = None
    bill_url: Optional[str] = None
    created_at: datetime


class Booking(BaseModel):
    """Complete booking model for responses"""
    model_config = ConfigDict(extra="ignore")
    
    booking_id: str  # e.g., "BK-001247"
    user_id: str
    trip_id: str
    trip_title: str
    trip_image: Optional[str] = None
    trip_type: BookingTripType
    start_date: str
    guests: int
    total_amount: float
    deposit_amount: float = 0
    paid_amount: float
    remaining_amount: float
    currency: str = "RM"
    payment_type: PaymentType
    payment_status: PaymentStatus
    booking_status: BookingStatus
    participant_details: List[ParticipantDetail] = []
    payments: List[PaymentRecord] = []
    created_at: datetime
    updated_at: datetime


class BookingListResponse(BaseModel):
    """Response model for paginated booking list"""
    bookings: List[Booking]
    total: int
    page: int
    pages: int


class BillplzWebhookPayload(BaseModel):
    """Payload received from Billplz webhook"""
    model_config = ConfigDict(extra="ignore")
    
    id: str
    collection_id: str
    paid: bool
    state: str
    amount: int  # in cents
    paid_amount: int
    due_at: Optional[str] = None
    email: str
    mobile: Optional[str] = None
    name: str
    description: str
    reference_1_label: Optional[str] = None
    reference_1: Optional[str] = None
    reference_2_label: Optional[str] = None
    reference_2: Optional[str] = None
    paid_at: Optional[str] = None
    url: str
