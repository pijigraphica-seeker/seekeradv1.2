from fastapi import FastAPI, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Import routes
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.trips import router as trips_router
from routes.bookings import router as bookings_router
from routes.wishlist import router as wishlist_router
from routes.hosts import router as hosts_router
from routes.admin import router as admin_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    mongo_url = os.environ['MONGO_URL']
    app.state.mongo_client = AsyncIOMotorClient(mongo_url)
    app.state.db = app.state.mongo_client[os.environ['DB_NAME']]
    
    # Seed initial data
    await seed_data(app.state.db)
    
    # Generate slugs for trips missing them
    await generate_missing_slugs(app.state.db)
    
    logger.info("Connected to MongoDB")
    yield
    
    # Shutdown
    app.state.mongo_client.close()
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title="Seeker Adventure API",
    description="API for Seeker Adventure booking platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(trips_router, prefix="/api")
app.include_router(bookings_router, prefix="/api")
app.include_router(wishlist_router, prefix="/api")
app.include_router(hosts_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

from routes.host_dashboard import router as host_dashboard_router
app.include_router(host_dashboard_router, prefix="/api")

from routes.reviews import router as reviews_router
app.include_router(reviews_router, prefix="/api")

from routes.content import router as content_router
app.include_router(content_router, prefix="/api")

# Move webhook to root level for Billplz callback
from routes.bookings import billplz_webhook
app.post("/api/payments/webhook/billplz")(billplz_webhook)


# Stripe webhook handler
@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe payment webhook"""
    db = request.app.state.db
    try:
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        stripe_key = os.environ.get("STRIPE_API_KEY")
        stripe_checkout = StripeCheckout(api_key=stripe_key)

        body = await request.body()
        sig = request.headers.get("Stripe-Signature")
        webhook_response = await stripe_checkout.handle_webhook(body, sig)

        logger.info(f"Stripe webhook: event={webhook_response.event_type}, session={webhook_response.session_id}, status={webhook_response.payment_status}")

        if webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            metadata = webhook_response.metadata or {}
            booking_id = metadata.get("booking_id")
            payment_id = metadata.get("payment_id")

            if booking_id and payment_id:
                # Check if already processed
                tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
                if tx and tx.get("payment_status") == "paid":
                    return {"status": "already_processed"}

                from datetime import datetime, timezone
                from models.booking import PaymentStatus, BookingStatus
                now = datetime.now(timezone.utc)

                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {"payment_status": "paid", "updated_at": now.isoformat()}}
                )

                await db.bookings.update_one(
                    {"booking_id": booking_id, "payments.payment_id": payment_id},
                    {"$set": {
                        "payments.$.status": PaymentStatus.COMPLETED.value,
                        "payments.$.paid_at": now.isoformat(),
                        "updated_at": now.isoformat()
                    }}
                )

                booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
                if booking:
                    total_paid = sum(
                        p["amount"] for p in booking.get("payments", [])
                        if p["status"] == PaymentStatus.COMPLETED.value
                    )
                    remaining = booking["total_amount"] - total_paid
                    ps = PaymentStatus.COMPLETED.value if remaining <= 0 else PaymentStatus.PARTIAL.value
                    bs = BookingStatus.CONFIRMED.value if total_paid > 0 else BookingStatus.PENDING.value

                    await db.bookings.update_one(
                        {"booking_id": booking_id},
                        {"$set": {
                            "paid_amount": total_paid,
                            "remaining_amount": max(0, remaining),
                            "payment_status": ps,
                            "booking_status": bs
                        }}
                    )

        return {"status": "received"}
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api")
async def root():
    return {"message": "Seeker Adventure API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


async def generate_missing_slugs(db):
    """Generate slugs for trips that don't have them"""
    import re
    cursor = db.trips.find({"slug": {"$exists": False}}, {"_id": 0, "trip_id": 1, "title": 1})
    count = 0
    async for trip in cursor:
        title = trip.get("title", "")
        slug = re.sub(r'[^a-z0-9\s-]', '', title.lower().strip())
        slug = re.sub(r'[\s]+', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        await db.trips.update_one({"trip_id": trip["trip_id"]}, {"$set": {"slug": slug}})
        count += 1
    if count:
        logger.info(f"Generated slugs for {count} trips")


async def seed_data(db):
    """Seed initial trips data if empty"""
    from datetime import datetime, timezone
    
    # Check if trips already exist
    trip_count = await db.trips.count_documents({})
    if trip_count > 0:
        logger.info(f"Database already has {trip_count} trips, skipping seed")
        return
    
    logger.info("Seeding initial trip data...")
    
    now = datetime.now(timezone.utc).isoformat()
    
    trips = [
        {
            "trip_id": "trip_001",
            "title": "Mount Merbabu & Mount Prau Expedition",
            "description": "Conquer two magnificent peaks in Central Java. This all-inclusive expedition takes you through stunning mountain landscapes with experienced guides.",
            "location": "Central Java, Indonesia",
            "activity_type": "hiking",
            "duration": "5D4N",
            "difficulty": "Moderate",
            "price": 899,
            "deposit_price": 50,
            "currency": "RM",
            "images": [
                "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b",
                "https://images.pexels.com/photos/4763809/pexels-photo-4763809.jpeg",
                "https://images.unsplash.com/photo-1510312305653-8ed496efae75",
                "https://images.unsplash.com/photo-1568736333626-be878c584b98"
            ],
            "max_guests": 12,
            "trip_type": "both",
            "open_trip_dates": ["2025-04-03", "2025-04-24", "2025-05-01", "2025-05-28", "2025-08-07"],
            "included": [
                "Licensed mountain guides",
                "Group porters for shared equipment",
                "National park permits & hiking insurance",
                "Tents (1 tent for 3 people)",
                "All meals & snacks during the hike",
                "Transportation from YIA Airport",
                "Post-hike hotel accommodation",
                "Group photographer"
            ],
            "meeting_point": "Yogyakarta International Airport (YIA)",
            "itinerary": [
                {"day": 1, "title": "Arrival & Journey to Base Camp", "activities": ["Pick up from Yogyakarta International Airport (YIA)", "Drive to Selo Village (3 hours)", "Meet the team & equipment check", "Light lunch at local warung", "Trek to Merbabu Base Camp (2-3 hours)", "Set up camp & orientation briefing", "Dinner and rest"], "meals": "Lunch, Dinner", "accommodation": "Mountain tent camping", "distance": "5km trek", "elevation": "2,400m"},
                {"day": 2, "title": "Summit Mount Merbabu", "activities": ["Wake up at 2:00 AM", "Light breakfast & preparation", "Start summit push at 3:00 AM", "Reach Merbabu Summit (3,145m) for sunrise", "Explore crater & photo session", "Descend back to base camp", "Rest and lunch", "Afternoon: Trek to Prau base area", "Set up camp & enjoy sunset views", "Dinner and stargazing"], "meals": "Breakfast, Lunch, Dinner", "accommodation": "Mountain tent camping", "distance": "12km trek", "elevation": "3,145m summit"},
                {"day": 3, "title": "Mount Prau Sunrise & Descent", "activities": ["Wake up at 4:00 AM", "Light breakfast", "Trek to Prau Summit (2,565m)", "Witness spectacular 360° sunrise views", "Photography session at the famous Prau meadow", "Return to camp for full breakfast", "Pack up and start descent", "Lunch at checkpoint", "Arrive at pickup point", "Transfer to hotel in Yogyakarta"], "meals": "Breakfast, Lunch, Dinner", "accommodation": "Hotel in Yogyakarta", "distance": "8km trek", "elevation": "2,565m summit"},
                {"day": 4, "title": "Rest & Cultural Experience", "activities": ["Free breakfast at hotel", "Morning: Rest and recovery", "Optional: Visit Borobudur Temple", "Lunch at local restaurant", "Afternoon: Explore Malioboro Street", "Traditional Javanese dinner", "Return to hotel"], "meals": "Breakfast, Lunch, Dinner", "accommodation": "Hotel in Yogyakarta", "distance": "Free day", "elevation": "Sea level"},
                {"day": 5, "title": "Departure", "activities": ["Breakfast at hotel", "Check out", "Last minute shopping (optional)", "Transfer to Yogyakarta Airport", "End of adventure - Safe travels!"], "meals": "Breakfast", "accommodation": "N/A", "distance": "Transfer only", "elevation": "N/A"}
            ],
            "host_id": None,
            "featured": True,
            "status": "active",
            "rating": 4.9,
            "review_count": 127,
            "created_at": now,
            "updated_at": now
        },
        {
            "trip_id": "trip_002",
            "title": "Mount Rinjani Summit Trek",
            "description": "Trek to the summit of Mount Rinjani, one of Indonesia's most iconic volcanoes. Experience breathtaking crater lake views.",
            "location": "Lombok, Indonesia",
            "activity_type": "hiking",
            "duration": "4D3N",
            "difficulty": "Challenging",
            "price": 750,
            "deposit_price": 50,
            "currency": "RM",
            "images": [
                "https://images.unsplash.com/photo-1501555088652-021faa106b9b",
                "https://images.pexels.com/photos/5653212/pexels-photo-5653212.jpeg",
                "https://images.unsplash.com/photo-1510312305653-8ed496efae75"
            ],
            "max_guests": 10,
            "trip_type": "both",
            "open_trip_dates": ["2025-04-10", "2025-05-15", "2025-06-20", "2025-07-25"],
            "included": ["Experienced trekking guides", "Porter services", "Camping equipment", "All meals during trek", "Park entrance fees", "Transportation"],
            "meeting_point": "Lombok International Airport",
            "itinerary": [],
            "host_id": None,
            "featured": True,
            "status": "active",
            "rating": 4.8,
            "review_count": 98,
            "created_at": now,
            "updated_at": now
        },
        {
            "trip_id": "trip_003",
            "title": "Komodo Island Diving Expedition",
            "description": "Explore world-class diving sites in Komodo National Park. Encounter manta rays, sharks, and vibrant coral reefs.",
            "location": "Komodo National Park, Indonesia",
            "activity_type": "diving",
            "duration": "4D3N",
            "difficulty": "Moderate",
            "price": 1200,
            "deposit_price": 100,
            "currency": "RM",
            "images": [
                "https://images.unsplash.com/photo-1517627043994-b991abb62fc8",
                "https://images.unsplash.com/photo-1682687982167-d7fb3ed8541d",
                "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b"
            ],
            "max_guests": 8,
            "trip_type": "both",
            "open_trip_dates": ["2025-05-05", "2025-06-10", "2025-07-15", "2025-08-20"],
            "included": ["Certified dive masters", "10 dives", "Full diving equipment", "Liveaboard accommodation", "All meals", "Marine park fees", "Airport transfers"],
            "meeting_point": "Labuan Bajo Airport",
            "itinerary": [],
            "host_id": None,
            "featured": True,
            "status": "active",
            "rating": 5.0,
            "review_count": 156,
            "created_at": now,
            "updated_at": now
        },
        {
            "trip_id": "trip_004",
            "title": "Raja Ampat Kayaking Adventure",
            "description": "Paddle through the pristine waters of Raja Ampat, exploring hidden lagoons and remote islands.",
            "location": "Raja Ampat, West Papua",
            "activity_type": "kayaking",
            "duration": "6D5N",
            "difficulty": "Moderate",
            "price": 1350,
            "deposit_price": 100,
            "currency": "RM",
            "images": [
                "https://images.unsplash.com/photo-1588472235276-7638965471e2",
                "https://images.unsplash.com/photo-1620903669944-de50fbe78210",
                "https://images.unsplash.com/photo-1576176539998-0237d1ac6a85"
            ],
            "max_guests": 12,
            "trip_type": "both",
            "open_trip_dates": ["2025-06-01", "2025-07-10", "2025-08-15", "2025-09-20"],
            "included": ["Expert kayak guides", "Kayaking equipment", "Snorkeling gear", "Island hopping tours", "Camping equipment", "All meals", "Boat transfers"],
            "meeting_point": "Sorong Airport",
            "itinerary": [],
            "host_id": None,
            "featured": False,
            "status": "active",
            "rating": 4.9,
            "review_count": 82,
            "created_at": now,
            "updated_at": now
        },
        {
            "trip_id": "trip_005",
            "title": "Bromo Sunrise Camping Trek",
            "description": "Experience the iconic Mount Bromo sunrise from a camping perspective. Perfect for beginners.",
            "location": "East Java, Indonesia",
            "activity_type": "camping",
            "duration": "3D2N",
            "difficulty": "Easy",
            "price": 450,
            "deposit_price": 50,
            "currency": "RM",
            "images": [
                "https://images.unsplash.com/photo-1510312305653-8ed496efae75",
                "https://images.pexels.com/photos/4484242/pexels-photo-4484242.jpeg",
                "https://images.unsplash.com/photo-1576176539998-0237d1ac6a85"
            ],
            "max_guests": 15,
            "trip_type": "both",
            "open_trip_dates": ["2025-04-15", "2025-05-20", "2025-06-25", "2025-07-30"],
            "included": ["Camping equipment", "Local guides", "Meals during trek", "Jeep to sunrise viewpoint", "Park entrance fees", "Transportation from Surabaya"],
            "meeting_point": "Surabaya Airport",
            "itinerary": [],
            "host_id": None,
            "featured": False,
            "status": "active",
            "rating": 4.7,
            "review_count": 203,
            "created_at": now,
            "updated_at": now
        },
        {
            "trip_id": "trip_006",
            "title": "Bali Waterfall Canyoning",
            "description": "Rappel down stunning waterfalls and navigate natural water slides in Bali's hidden canyons.",
            "location": "Bali, Indonesia",
            "activity_type": "canyoning",
            "duration": "1D",
            "difficulty": "Moderate",
            "price": 280,
            "deposit_price": 30,
            "currency": "RM",
            "images": [
                "https://images.unsplash.com/photo-1528543606781-2f6e6857f318",
                "https://images.unsplash.com/photo-1568736333626-be878c584b98"
            ],
            "max_guests": 8,
            "trip_type": "both",
            "open_trip_dates": ["2025-04-05", "2025-04-12", "2025-04-19", "2025-04-26"],
            "included": ["Professional canyoning guides", "Safety equipment", "Lunch", "Transportation", "Insurance"],
            "meeting_point": "Ubud Center",
            "itinerary": [],
            "host_id": None,
            "featured": False,
            "status": "active",
            "rating": 4.8,
            "review_count": 145,
            "created_at": now,
            "updated_at": now
        },
        {
            "trip_id": "trip_007",
            "title": "Sumatra Jungle Trekking",
            "description": "Trek through pristine rainforest and encounter wild orangutans in their natural habitat.",
            "location": "Sumatra, Indonesia",
            "activity_type": "hiking",
            "duration": "5D4N",
            "difficulty": "Challenging",
            "price": 980,
            "deposit_price": 80,
            "currency": "RM",
            "images": [
                "https://images.unsplash.com/photo-1501555088652-021faa106b9b",
                "https://images.pexels.com/photos/4763809/pexels-photo-4763809.jpeg",
                "https://images.unsplash.com/photo-1568736333626-be878c584b98"
            ],
            "max_guests": 10,
            "trip_type": "both",
            "open_trip_dates": ["2025-05-10", "2025-06-15", "2025-07-20"],
            "included": ["Jungle guides", "Camping equipment", "All meals", "Orangutan viewing permits", "Transportation", "Porter services"],
            "meeting_point": "Medan Airport",
            "itinerary": [],
            "host_id": None,
            "featured": False,
            "status": "active",
            "rating": 4.9,
            "review_count": 67,
            "created_at": now,
            "updated_at": now
        },
        {
            "trip_id": "trip_008",
            "title": "Paragliding Bali Adventure",
            "description": "Soar above Bali's stunning coastline with experienced tandem pilots. No experience needed!",
            "location": "Bali, Indonesia",
            "activity_type": "paragliding",
            "duration": "1D",
            "difficulty": "Easy",
            "price": 350,
            "deposit_price": 50,
            "currency": "RM",
            "images": [
                "https://images.unsplash.com/photo-1618083707368-b3823daa2626",
                "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b",
                "https://images.unsplash.com/photo-1510312305653-8ed496efae75"
            ],
            "max_guests": 6,
            "trip_type": "both",
            "open_trip_dates": ["2025-04-08", "2025-04-15", "2025-04-22", "2025-04-29"],
            "included": ["Certified tandem pilot", "All equipment", "Photo & video package", "Insurance", "Hotel pickup"],
            "meeting_point": "Hotel Pickup (Bali)",
            "itinerary": [],
            "host_id": None,
            "featured": False,
            "status": "active",
            "rating": 5.0,
            "review_count": 189,
            "created_at": now,
            "updated_at": now
        }
    ]
    
    await db.trips.insert_many(trips)
    
    # Create admin user
    admin_exists = await db.users.find_one({"email": "admin@seekeradventure.com"})
    if not admin_exists:
        import hashlib
        admin_doc = {
            "user_id": "user_admin001",
            "client_id": "SA-000000",
            "email": "admin@seekeradventure.com",
            "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
            "name": "Admin Seeker",
            "role": "admin",
            "auth_provider": "email",
            "phone": None,
            "avatar": None,
            "nric": None,
            "address": None,
            "emergency_contact": None,
            "emergency_contact_phone": None,
            "height": None,
            "weight": None,
            "is_active": True,
            "email_verified": True,
            "created_at": now,
            "updated_at": now
        }
        await db.users.insert_one(admin_doc)
        logger.info("Admin user created: admin@seekeradventure.com / admin123")
    
    # Initialize counters
    await db.counters.update_one(
        {"_id": "client_id"},
        {"$setOnInsert": {"seq": 1}},
        upsert=True
    )
    await db.counters.update_one(
        {"_id": "booking_id"},
        {"$setOnInsert": {"seq": 0}},
        upsert=True
    )
    
    logger.info(f"Seeded {len(trips)} trips")
