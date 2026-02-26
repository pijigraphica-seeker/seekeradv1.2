from fastapi import APIRouter, HTTPException, Request
from routes.auth import get_current_user
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/content", tags=["Content"])

# Default content structure
DEFAULT_CONTENT = {
    "hero": {
        "title": "Discover Your Next Adventure",
        "subtitle": "Explore breathtaking destinations with expert guides. From mountain peaks to ocean depths, your adventure starts here.",
        "search_placeholder": "Search adventures..."
    },
    "features": {
        "feature_1_title": "Expert Guides",
        "feature_1_text": "Certified adventure guides with years of experience in the field.",
        "feature_2_title": "Licensed & Professional",
        "feature_2_text": "Professional guides, permits, and certified adventure operators for your safety.",
        "feature_3_title": "Small Groups",
        "feature_3_text": "Intimate group sizes for a more personal and immersive experience."
    },
    "footer": {
        "company_description": "Your trusted partner for unforgettable adventure travel experiences across Indonesia.",
        "phone_1": "+60 11-7000 1232",
        "phone_2": "+60 11-7000 1232",
        "email": "sales@seekeradventure.com",
        "location": "Indonesia",
        "whatsapp": "601170001232",
        "facebook_url": "#",
        "instagram_url": "#",
        "tiktok_url": "#"
    },
    "about": {
        "title": "About Seeker Adventure",
        "story": "Seeker Adventure was born from a passion for exploring the great outdoors. We believe that adventure travel should be accessible, safe, and unforgettable.",
        "mission": "To connect adventure seekers with the most breathtaking destinations and experienced guides across Southeast Asia.",
        "vision": "To be the leading adventure travel platform in Southeast Asia, making extraordinary experiences accessible to everyone.",
        "why_choose_us": "With years of experience and a network of certified guides, we ensure every trip is safe, well-organized, and truly memorable."
    },
    "booking_policy": {
        "non_refundable_text": "All bookings are non-refundable as per our Terms & Conditions.",
        "full_payment_text": "Full payment is required 1 month before the trip date.",
        "min_installment": "Minimum installment payment is RM100/month."
    }
}


@router.get("")
async def get_all_content(request: Request):
    db = request.app.state.db
    content = await db.site_content.find_one({"_id": "main"})
    if not content:
        return DEFAULT_CONTENT
    content.pop("_id", None)
    return content


@router.get("/{section}")
async def get_content_section(section: str, request: Request):
    db = request.app.state.db
    content = await db.site_content.find_one({"_id": "main"})
    if not content or section not in content:
        if section in DEFAULT_CONTENT:
            return DEFAULT_CONTENT[section]
        raise HTTPException(status_code=404, detail="Section not found")
    return content[section]


@router.put("/{section}")
async def update_content_section(section: str, request: Request):
    db = request.app.state.db
    current_user = await get_current_user(request)

    if current_user.role not in ["admin", "webdev"]:
        raise HTTPException(status_code=403, detail="Admin or WebDev access required")

    if section not in DEFAULT_CONTENT:
        raise HTTPException(status_code=400, detail=f"Invalid section. Valid: {list(DEFAULT_CONTENT.keys())}")

    body = await request.json()

    # Ensure main document exists
    existing = await db.site_content.find_one({"_id": "main"})
    if not existing:
        await db.site_content.insert_one({"_id": "main", **DEFAULT_CONTENT})

    await db.site_content.update_one(
        {"_id": "main"},
        {"$set": {section: body, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": current_user.user_id}}
    )

    logger.info(f"Content updated: {section} by {current_user.email}")
    return {"message": f"{section} content updated successfully"}
