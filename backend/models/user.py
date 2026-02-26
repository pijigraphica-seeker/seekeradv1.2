from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    CLIENT = "client"
    HOST = "host"
    ADMIN = "admin"
    WEBDEV = "webdev"


class AuthProvider(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    FACEBOOK = "facebook"
    APPLE = "apple"


class UserBase(BaseModel):
    """Base user model with common fields"""
    email: EmailStr
    name: str
    phone: Optional[str] = None
    avatar: Optional[str] = None


class UserCreate(BaseModel):
    """Request model for creating a new user"""
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    """Request model for user login"""
    email: EmailStr
    password: str


class ClientProfile(BaseModel):
    """Extended profile fields for clients"""
    nric: Optional[str] = None  # National ID
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    height: Optional[float] = None  # in cm
    weight: Optional[float] = None  # in kg


class UserProfileUpdate(BaseModel):
    """Request model for updating user profile"""
    name: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    nric: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None


class User(BaseModel):
    """Complete user model for responses"""
    model_config = ConfigDict(extra="ignore")
    
    user_id: str
    client_id: str  # Unique client ID like SA-000001
    email: EmailStr
    name: str
    role: UserRole = UserRole.CLIENT
    auth_provider: AuthProvider = AuthProvider.EMAIL
    phone: Optional[str] = None
    avatar: Optional[str] = None
    # Client profile fields
    nric: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    # Metadata
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime
    updated_at: datetime


class UserSession(BaseModel):
    """User session model"""
    model_config = ConfigDict(extra="ignore")
    
    session_id: str
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime


class TokenResponse(BaseModel):
    """Response model for auth endpoints"""
    access_token: str
    token_type: str = "bearer"
    user: User
