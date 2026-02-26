from fastapi import APIRouter, HTTPException, Request, Query
from models.host import HostApplication, HostApplicationCreate, HostApproval, HostStatus
from models.user import UserRole
from routes.auth import get_current_user
from datetime import datetime, timezone
import uuid
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hosts", tags=["Hosts"])


@router.post("/apply", response_model=HostApplication)
async def apply_as_host(data: HostApplicationCreate, request: Request):
    """Apply to become a host"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    # Check if already applied
    existing = await db.host_applications.find_one(
        {"user_id": current_user.user_id},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied. Please wait for approval.")
    
    host_id = f"host_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    application_doc = {
        "host_id": host_id,
        "user_id": current_user.user_id,
        "user_name": current_user.name,
        "user_email": current_user.email,
        **data.model_dump(),
        "status": HostStatus.PENDING.value,
        "rejection_reason": None,
        "approved_by": None,
        "approved_at": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.host_applications.insert_one(application_doc)
    
    application_doc["created_at"] = now
    application_doc["updated_at"] = now
    
    return HostApplication(**application_doc)


@router.get("/my-application", response_model=HostApplication)
async def get_my_application(request: Request):
    """Get current user's host application"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    application = await db.host_applications.find_one(
        {"user_id": current_user.user_id},
        {"_id": 0}
    )
    
    if not application:
        raise HTTPException(status_code=404, detail="No application found")
    
    if isinstance(application.get("created_at"), str):
        application["created_at"] = datetime.fromisoformat(application["created_at"])
    if isinstance(application.get("updated_at"), str):
        application["updated_at"] = datetime.fromisoformat(application["updated_at"])
    if isinstance(application.get("approved_at"), str):
        application["approved_at"] = datetime.fromisoformat(application["approved_at"])
    
    return HostApplication(**application)


# Admin endpoints
@router.get("/applications")
async def get_all_applications(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    """Get all host applications (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    
    total = await db.host_applications.count_documents(query)
    pages = math.ceil(total / limit) if total > 0 else 1
    
    skip = (page - 1) * limit
    cursor = db.host_applications.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    
    applications = []
    for doc in docs:
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        if isinstance(doc.get("approved_at"), str):
            doc["approved_at"] = datetime.fromisoformat(doc["approved_at"])
        applications.append(HostApplication(**doc))
    
    return {
        "applications": applications,
        "total": total,
        "page": page,
        "pages": pages
    }


@router.put("/applications/{host_id}", response_model=HostApplication)
async def update_application_status(
    host_id: str,
    approval: HostApproval,
    request: Request
):
    """Approve or reject a host application (Admin only)"""
    db = request.app.state.db
    current_user = await get_current_user(request)
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    application = await db.host_applications.find_one({"host_id": host_id}, {"_id": 0})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    now = datetime.now(timezone.utc)
    
    update_data = {
        "status": approval.status.value,
        "updated_at": now.isoformat()
    }
    
    if approval.status == HostStatus.APPROVED:
        update_data["approved_by"] = current_user.user_id
        update_data["approved_at"] = now.isoformat()
        
        # Update user role to host
        await db.users.update_one(
            {"user_id": application["user_id"]},
            {"$set": {"role": UserRole.HOST.value, "updated_at": now.isoformat()}}
        )
    elif approval.status == HostStatus.REJECTED:
        update_data["rejection_reason"] = approval.rejection_reason
    
    await db.host_applications.update_one(
        {"host_id": host_id},
        {"$set": update_data}
    )
    
    updated = await db.host_applications.find_one({"host_id": host_id}, {"_id": 0})
    
    if isinstance(updated.get("created_at"), str):
        updated["created_at"] = datetime.fromisoformat(updated["created_at"])
    if isinstance(updated.get("updated_at"), str):
        updated["updated_at"] = datetime.fromisoformat(updated["updated_at"])
    if isinstance(updated.get("approved_at"), str):
        updated["approved_at"] = datetime.fromisoformat(updated["approved_at"])
    
    return HostApplication(**updated)
