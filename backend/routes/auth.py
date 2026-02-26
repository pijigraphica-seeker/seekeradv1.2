from fastapi import APIRouter, HTTPException, Response, Request, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.user import (
    User, UserCreate, UserLogin, UserProfileUpdate, 
    TokenResponse, UserRole, AuthProvider
)
import uuid
import hashlib
import httpx
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_client_id(db) -> str:
    """Generate unique client ID like SA-000001"""
    # This will be called with await in async context
    return f"SA-{uuid.uuid4().hex[:6].upper()}"


async def get_next_client_id(db: AsyncIOMotorDatabase) -> str:
    """Get the next sequential client ID"""
    counter = await db.counters.find_one_and_update(
        {"_id": "client_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
        projection={"_id": 0}
    )
    seq = counter.get("seq", 1)
    return f"SA-{seq:06d}"


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, request: Request):
    """Register a new user with email and password"""
    db = request.app.state.db
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate IDs
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    client_id = await get_next_client_id(db)
    session_token = f"session_{uuid.uuid4().hex}"
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    
    # Create user document
    user_doc = {
        "user_id": user_id,
        "client_id": client_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": UserRole.CLIENT.value,
        "auth_provider": AuthProvider.EMAIL.value,
        "phone": None,
        "avatar": None,
        "nric": None,
        "address": None,
        "emergency_contact": None,
        "emergency_contact_phone": None,
        "height": None,
        "weight": None,
        "is_active": True,
        "email_verified": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Create session
    session_doc = {
        "session_id": f"sess_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Return user (exclude password_hash and _id)
    user_doc.pop("password_hash", None)
    user_doc["created_at"] = now
    user_doc["updated_at"] = now
    
    return TokenResponse(
        access_token=session_token,
        token_type="bearer",
        user=User(**user_doc)
    )


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, request: Request, response: Response):
    """Login with email and password"""
    db = request.app.state.db
    
    # Find user
    user_doc = await db.users.find_one(
        {"email": login_data.email},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check password
    if user_doc.get("password_hash") != hash_password(login_data.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is deactivated")
    
    # Create new session
    session_token = f"session_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    
    session_doc = {
        "session_id": f"sess_{uuid.uuid4().hex[:12]}",
        "user_id": user_doc["user_id"],
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    
    # Parse dates for response
    user_doc.pop("password_hash", None)
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    if isinstance(user_doc.get("updated_at"), str):
        user_doc["updated_at"] = datetime.fromisoformat(user_doc["updated_at"])
    
    return TokenResponse(
        access_token=session_token,
        token_type="bearer",
        user=User(**user_doc)
    )


@router.post("/session")
async def process_google_session(request: Request, response: Response):
    """Process Google OAuth session_id from Emergent Auth"""
    db = request.app.state.db
    
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    # Exchange session_id for user data with Emergent Auth
    try:
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            auth_data = auth_response.json()
    except httpx.RequestError as e:
        logger.error(f"Auth service error: {e}")
        raise HTTPException(status_code=500, detail="Authentication service unavailable")
    
    email = auth_data.get("email")
    name = auth_data.get("name")
    picture = auth_data.get("picture")
    session_token = auth_data.get("session_token")
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        # Update existing user
        user_id = existing_user["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": name,
                "avatar": picture,
                "updated_at": now.isoformat()
            }}
        )
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        client_id = await get_next_client_id(db)
        
        user_doc = {
            "user_id": user_id,
            "client_id": client_id,
            "email": email,
            "name": name,
            "role": UserRole.CLIENT.value,
            "auth_provider": AuthProvider.GOOGLE.value,
            "phone": None,
            "avatar": picture,
            "nric": None,
            "address": None,
            "emergency_contact": None,
            "emergency_contact_phone": None,
            "height": None,
            "weight": None,
            "is_active": True,
            "email_verified": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Create session
    session_doc = {
        "session_id": f"sess_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    
    # Parse dates
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    if isinstance(user_doc.get("updated_at"), str):
        user_doc["updated_at"] = datetime.fromisoformat(user_doc["updated_at"])
    
    user_doc.pop("password_hash", None)
    
    return TokenResponse(
        access_token=session_token,
        token_type="bearer",
        user=User(**user_doc)
    )


async def get_current_user(request: Request) -> User:
    """Dependency to get current authenticated user"""
    db = request.app.state.db
    
    # Check cookie first
    session_token = request.cookies.get("session_token")
    
    # Then check Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    user_doc.pop("password_hash", None)
    
    # Parse dates
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    if isinstance(user_doc.get("updated_at"), str):
        user_doc["updated_at"] = datetime.fromisoformat(user_doc["updated_at"])
    
    return User(**user_doc)


@router.get("/me", response_model=User)
async def get_me(request: Request):
    """Get current authenticated user"""
    return await get_current_user(request)


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session"""
    db = request.app.state.db
    
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        samesite="none"
    )
    
    return {"message": "Logged out successfully"}



@router.post("/forgot-password")
async def forgot_password(request: Request):
    """Send password reset token via email"""
    db = request.app.state.db
    body = await request.json()
    email = body.get("email", "").strip().lower()

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}

    if user_doc.get("auth_provider") == "google":
        raise HTTPException(status_code=400, detail="This account uses Google login. Please sign in with Google.")

    # Generate reset token
    reset_token = uuid.uuid4().hex
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    await db.password_resets.insert_one({
        "token": reset_token,
        "user_id": user_doc["user_id"],
        "email": email,
        "expires_at": expires.isoformat(),
        "used": False
    })

    # Send reset email
    try:
        import os
        from services.email_service import send_email
        frontend_url = os.environ.get("FRONTEND_URL", "")
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px;">
            <h2 style="color:#EB5A7E;">Seeker Adventure</h2>
            <p>Hi {user_doc.get('name', 'there')},</p>
            <p>You requested a password reset. Click the link below to set a new password:</p>
            <a href="{reset_link}" style="display:inline-block;padding:12px 24px;background:#EB5A7E;color:#fff;text-decoration:none;border-radius:6px;margin:16px 0;">Reset Password</a>
            <p style="color:#666;font-size:13px;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
        </div>
        """
        import asyncio
        asyncio.create_task(send_email(email, "Reset Your Password - Seeker Adventure", html))
    except Exception as e:
        logger.warning(f"Failed to send reset email: {e}")

    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(request: Request):
    """Reset password using token"""
    db = request.app.state.db
    body = await request.json()
    token = body.get("token", "")
    new_password = body.get("new_password", "")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and new password are required")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    reset_doc = await db.password_resets.find_one({"token": token, "used": False}, {"_id": 0})
    if not reset_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    expires_at = datetime.fromisoformat(reset_doc["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset link has expired")

    # Update password
    await db.users.update_one(
        {"user_id": reset_doc["user_id"]},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    # Mark token as used
    await db.password_resets.update_one({"token": token}, {"$set": {"used": True}})

    # Invalidate all sessions
    await db.user_sessions.delete_many({"user_id": reset_doc["user_id"]})

    return {"message": "Password reset successfully. Please login with your new password."}


@router.post("/change-password")
async def change_password(request: Request):
    """Change password for authenticated user"""
    db = request.app.state.db
    current_user = await get_current_user(request)

    body = await request.json()
    current_password = body.get("current_password", "")
    new_password = body.get("new_password", "")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Current and new password are required")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    # Verify current password
    user_doc = await db.users.find_one({"user_id": current_user.user_id}, {"_id": 0})
    if not user_doc or user_doc.get("password_hash") != hash_password(current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Update password
    await db.users.update_one(
        {"user_id": current_user.user_id},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    return {"message": "Password changed successfully"}
