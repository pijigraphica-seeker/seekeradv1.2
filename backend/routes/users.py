from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File
from models.user import User, UserProfileUpdate
from routes.auth import get_current_user
from datetime import datetime, timezone
import uuid
import base64
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=User)
async def get_current_user_profile(request: Request):
    """Get current user profile"""
    return await get_current_user(request)


@router.put("/me", response_model=User)
async def update_profile(
    profile_data: UserProfileUpdate,
    request: Request
):
    """Update current user profile"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    # Build update data
    update_data = {}
    for field, value in profile_data.model_dump(exclude_unset=True).items():
        if value is not None:
            update_data[field] = value
    
    if not update_data:
        return current_user
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one(
        {"user_id": current_user.user_id},
        {"$set": update_data}
    )
    
    # Get updated user
    user_doc = await db.users.find_one(
        {"user_id": current_user.user_id},
        {"_id": 0}
    )
    
    user_doc.pop("password_hash", None)
    
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    if isinstance(user_doc.get("updated_at"), str):
        user_doc["updated_at"] = datetime.fromisoformat(user_doc["updated_at"])
    
    return User(**user_doc)


@router.post("/me/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...)
):
    """Upload user avatar"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, WebP, and GIF are allowed.")
    
    # Validate file size (max 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
    
    # Store as base64 data URL (for simplicity - in production use cloud storage)
    avatar_data = f"data:{file.content_type};base64,{base64.b64encode(content).decode()}"
    
    await db.users.update_one(
        {"user_id": current_user.user_id},
        {"$set": {
            "avatar": avatar_data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Avatar uploaded successfully", "avatar": avatar_data}


@router.get("/{user_id}", response_model=User)
async def get_user_by_id(user_id: str, request: Request):
    """Get user by ID (public profile)"""
    db = request.app.state.db
    
    user_doc = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0, "password_hash": 0, "nric": 0}  # Exclude sensitive data
    )
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    if isinstance(user_doc.get("updated_at"), str):
        user_doc["updated_at"] = datetime.fromisoformat(user_doc["updated_at"])
    
    return User(**user_doc)


@router.get("/client/{client_id}")
async def get_user_by_client_id(client_id: str, request: Request):
    """Get user by client ID (e.g., SA-000001)"""
    db = request.app.state.db
    
    user_doc = await db.users.find_one(
        {"client_id": client_id},
        {"_id": 0, "password_hash": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    if isinstance(user_doc.get("updated_at"), str):
        user_doc["updated_at"] = datetime.fromisoformat(user_doc["updated_at"])
    
    return User(**user_doc)
