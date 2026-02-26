from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class HostStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class HostApplicationCreate(BaseModel):
    """Request model for host registration"""
    company_name: Optional[str] = None
    description: str
    experience_years: int
    certifications: List[str] = []
    activity_types: List[str] = []
    phone: str
    address: str


class HostApplication(BaseModel):
    """Host application/registration model"""
    model_config = ConfigDict(extra="ignore")
    
    host_id: str
    user_id: str
    user_name: str
    user_email: str
    company_name: Optional[str] = None
    description: str
    experience_years: int
    certifications: List[str] = []
    activity_types: List[str] = []
    phone: str
    address: str
    status: HostStatus = HostStatus.PENDING
    rejection_reason: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class HostApproval(BaseModel):
    """Request model for approving/rejecting host"""
    status: HostStatus
    rejection_reason: Optional[str] = None
