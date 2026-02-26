"""
Comprehensive API Tests for Seeker Adventure Platform
Tests cover: Health, Trips, Auth, Users, Bookings, Wishlist, Admin APIs
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://adventure-trips-6.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@seekeradventure.com"
ADMIN_PASSWORD = "admin123"
TEST_USER_PREFIX = f"test_{uuid.uuid4().hex[:6]}"
TEST_USER_EMAIL = f"{TEST_USER_PREFIX}@example.com"
TEST_USER_PASSWORD = "testpass123"
TEST_USER_NAME = "Test User"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def registered_user(api_client):
    """Register a test user and return credentials"""
    response = api_client.post(f"{BASE_URL}/api/auth/register", json={
        "name": TEST_USER_NAME,
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return {
            "token": data["access_token"],
            "user": data["user"],
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
    pytest.skip(f"Could not register test user: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin access token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip(f"Admin login failed: {response.status_code}")


@pytest.fixture(scope="module")
def auth_headers(registered_user):
    """Get auth headers for authenticated requests"""
    return {"Authorization": f"Bearer {registered_user['token']}"}


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Get admin auth headers"""
    return {"Authorization": f"Bearer {admin_token}"}


# ============== HEALTH CHECKS ==============

class TestHealthEndpoints:
    """Test health and root endpoints"""
    
    def test_health_check(self, api_client):
        """Test health endpoint returns healthy status"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("Health check passed")
    
    def test_api_root(self, api_client):
        """Test API root endpoint"""
        response = api_client.get(f"{BASE_URL}/api")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        print(f"API version: {data['version']}")


# ============== TRIPS API ==============

class TestTripsAPI:
    """Test trips CRUD operations"""
    
    def test_get_all_trips(self, api_client):
        """Test fetching all trips"""
        response = api_client.get(f"{BASE_URL}/api/trips")
        assert response.status_code == 200
        data = response.json()
        assert "trips" in data
        assert "total" in data
        assert "page" in data
        assert len(data["trips"]) > 0
        print(f"Found {data['total']} trips")
    
    def test_get_trips_with_filters(self, api_client):
        """Test filtering trips by activity type"""
        response = api_client.get(f"{BASE_URL}/api/trips?activity_type=hiking")
        assert response.status_code == 200
        data = response.json()
        for trip in data["trips"]:
            assert trip["activity_type"] == "hiking"
        print(f"Found {len(data['trips'])} hiking trips")
    
    def test_get_featured_trips(self, api_client):
        """Test fetching featured trips"""
        response = api_client.get(f"{BASE_URL}/api/trips?featured=true")
        assert response.status_code == 200
        data = response.json()
        for trip in data["trips"]:
            assert trip["featured"] == True
        print(f"Found {len(data['trips'])} featured trips")
    
    def test_get_trips_sorted_by_price(self, api_client):
        """Test sorting trips by price"""
        response = api_client.get(f"{BASE_URL}/api/trips?sort_by=price_asc")
        assert response.status_code == 200
        data = response.json()
        prices = [trip["price"] for trip in data["trips"]]
        assert prices == sorted(prices)
        print("Trips correctly sorted by price ascending")
    
    def test_get_single_trip(self, api_client):
        """Test fetching a single trip by ID"""
        # First get a trip ID from list
        list_response = api_client.get(f"{BASE_URL}/api/trips?limit=1")
        assert list_response.status_code == 200
        trip_id = list_response.json()["trips"][0]["trip_id"]
        
        # Get single trip
        response = api_client.get(f"{BASE_URL}/api/trips/{trip_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["trip_id"] == trip_id
        assert "title" in data
        assert "description" in data
        assert "price" in data
        assert "itinerary" in data
        print(f"Trip detail fetched: {data['title']}")
    
    def test_get_trip_not_found(self, api_client):
        """Test 404 for non-existent trip"""
        response = api_client.get(f"{BASE_URL}/api/trips/nonexistent_trip_id")
        assert response.status_code == 404
        print("Correctly returns 404 for non-existent trip")
    
    def test_search_trips(self, api_client):
        """Test searching trips by keyword"""
        response = api_client.get(f"{BASE_URL}/api/trips?search=merbabu")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0
        print(f"Search returned {data['total']} results")


# ============== AUTH API ==============

class TestAuthAPI:
    """Test authentication endpoints"""
    
    def test_register_new_user(self, api_client):
        """Test user registration"""
        unique_email = f"reg_test_{uuid.uuid4().hex[:8]}@test.com"
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Registration Test",
            "email": unique_email,
            "password": "test123456"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == unique_email
        assert data["user"]["client_id"].startswith("SA-")
        print(f"Registered user with client ID: {data['user']['client_id']}")
    
    def test_register_duplicate_email(self, api_client, registered_user):
        """Test registration with existing email fails"""
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Duplicate Test",
            "email": registered_user["email"],
            "password": "test123456"
        })
        assert response.status_code == 400
        print("Correctly rejects duplicate email registration")
    
    def test_login_valid_credentials(self, api_client, registered_user):
        """Test login with valid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == registered_user["email"]
        print("Login successful")
    
    def test_login_invalid_password(self, api_client, registered_user):
        """Test login with wrong password"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("Correctly rejects invalid password")
    
    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent email"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        })
        assert response.status_code == 401
        print("Correctly rejects non-existent user")
    
    def test_admin_login(self, api_client):
        """Test admin login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "admin"
        print("Admin login successful")
    
    def test_get_me_authenticated(self, api_client, auth_headers):
        """Test getting current user info"""
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert "client_id" in data
        print(f"Current user: {data['email']}")
    
    def test_get_me_unauthenticated(self, api_client):
        """Test getting me without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("Correctly requires authentication for /me")
    
    def test_logout(self, api_client, registered_user):
        """Test logout endpoint"""
        headers = {"Authorization": f"Bearer {registered_user['token']}"}
        response = api_client.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        assert response.status_code == 200
        print("Logout successful")


# ============== USERS API ==============

class TestUsersAPI:
    """Test user profile operations"""
    
    def test_update_profile(self, api_client, auth_headers, registered_user):
        """Test profile update"""
        # Re-login to get fresh token after logout test
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        new_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {new_token}"}
        
        response = api_client.put(f"{BASE_URL}/api/users/me", headers=headers, json={
            "name": "Updated Test Name",
            "phone": "+60123456789",
            "height": 175.5,
            "weight": 70.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Test Name"
        assert data["phone"] == "+60123456789"
        print("Profile updated successfully")
    
    def test_get_user_by_client_id(self, api_client, registered_user):
        """Test fetching user by client ID"""
        client_id = registered_user["user"]["client_id"]
        response = api_client.get(f"{BASE_URL}/api/users/client/{client_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == client_id
        print(f"Found user by client ID: {client_id}")
    
    def test_get_user_by_invalid_client_id(self, api_client):
        """Test 404 for invalid client ID"""
        response = api_client.get(f"{BASE_URL}/api/users/client/SA-999999")
        assert response.status_code == 404
        print("Correctly returns 404 for invalid client ID")


# ============== WISHLIST API ==============

class TestWishlistAPI:
    """Test wishlist operations"""
    
    def test_add_to_wishlist(self, api_client, registered_user):
        """Test adding trip to wishlist"""
        # Login to get fresh token
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get a trip ID
        trips_response = api_client.get(f"{BASE_URL}/api/trips?limit=1")
        trip_id = trips_response.json()["trips"][0]["trip_id"]
        
        response = api_client.post(f"{BASE_URL}/api/wishlist", headers=headers, json={
            "trip_id": trip_id
        })
        assert response.status_code == 200
        print(f"Added trip {trip_id} to wishlist")
    
    def test_get_wishlist(self, api_client, registered_user):
        """Test getting user's wishlist"""
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = api_client.get(f"{BASE_URL}/api/wishlist", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "wishlist" in data
        print(f"Wishlist has {len(data['wishlist'])} items")
    
    def test_check_wishlist_status(self, api_client, registered_user):
        """Test checking if trip is in wishlist"""
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get a trip ID
        trips_response = api_client.get(f"{BASE_URL}/api/trips?limit=1")
        trip_id = trips_response.json()["trips"][0]["trip_id"]
        
        response = api_client.get(f"{BASE_URL}/api/wishlist/check/{trip_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "in_wishlist" in data
        print(f"Wishlist check for {trip_id}: {data['in_wishlist']}")
    
    def test_remove_from_wishlist(self, api_client, registered_user):
        """Test removing trip from wishlist"""
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get a trip from wishlist
        wishlist_response = api_client.get(f"{BASE_URL}/api/wishlist", headers=headers)
        wishlist = wishlist_response.json()["wishlist"]
        
        if len(wishlist) > 0:
            trip_id = wishlist[0]["trip_id"]
            response = api_client.delete(f"{BASE_URL}/api/wishlist/{trip_id}", headers=headers)
            assert response.status_code == 200
            print(f"Removed trip {trip_id} from wishlist")
        else:
            print("No items in wishlist to remove")


# ============== BOOKINGS API ==============

class TestBookingsAPI:
    """Test booking operations"""
    
    def test_create_booking(self, api_client, registered_user):
        """Test creating a new booking"""
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        token = login_response.json()["access_token"]
        user = login_response.json()["user"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get a trip ID
        trips_response = api_client.get(f"{BASE_URL}/api/trips?limit=1")
        trip = trips_response.json()["trips"][0]
        trip_id = trip["trip_id"]
        open_dates = trip.get("open_trip_dates", ["2025-06-01"])
        
        booking_data = {
            "trip_id": trip_id,
            "trip_type": "open",
            "start_date": open_dates[0] if open_dates else "2025-06-01",
            "guests": 1,
            "payment_type": "deposit",
            "participant_details": [{
                "client_id": user.get("client_id", "GUEST"),
                "name": user.get("name", "Test User"),
                "email": user.get("email"),
                "phone": "+60123456789",
                "nric": "123456-78-9012",
                "emergency_contact": "Emergency Contact",
                "emergency_contact_phone": "+60987654321"
            }]
        }
        
        response = api_client.post(f"{BASE_URL}/api/bookings", headers=headers, json=booking_data)
        assert response.status_code == 200
        data = response.json()
        assert "booking_id" in data
        assert data["booking_id"].startswith("BK-")
        assert data["booking_status"] == "pending"
        print(f"Created booking: {data['booking_id']}")
        return data["booking_id"]
    
    def test_get_my_bookings(self, api_client, registered_user):
        """Test fetching user's bookings"""
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = api_client.get(f"{BASE_URL}/api/bookings/my-bookings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "bookings" in data
        assert "total" in data
        print(f"User has {data['total']} bookings")
    
    def test_get_booking_detail(self, api_client, registered_user):
        """Test fetching a specific booking"""
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get bookings
        bookings_response = api_client.get(f"{BASE_URL}/api/bookings/my-bookings", headers=headers)
        bookings = bookings_response.json()["bookings"]
        
        if len(bookings) > 0:
            booking_id = bookings[0]["booking_id"]
            response = api_client.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["booking_id"] == booking_id
            assert "participant_details" in data
            print(f"Fetched booking detail: {booking_id}")
        else:
            print("No bookings to fetch")
    
    def test_cancel_booking(self, api_client, registered_user):
        """Test cancelling a booking"""
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        token = login_response.json()["access_token"]
        user = login_response.json()["user"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a booking to cancel
        trips_response = api_client.get(f"{BASE_URL}/api/trips?limit=1")
        trip = trips_response.json()["trips"][0]
        
        booking_data = {
            "trip_id": trip["trip_id"],
            "trip_type": "open",
            "start_date": trip.get("open_trip_dates", ["2025-06-01"])[0],
            "guests": 1,
            "payment_type": "deposit",
            "participant_details": [{
                "client_id": user.get("client_id", "GUEST"),
                "name": user.get("name", "Test User"),
                "email": user.get("email"),
                "phone": "+60123456789",
                "nric": "",
                "emergency_contact": "",
                "emergency_contact_phone": ""
            }]
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/bookings", headers=headers, json=booking_data)
        booking_id = create_response.json()["booking_id"]
        
        # Cancel the booking
        response = api_client.put(f"{BASE_URL}/api/bookings/{booking_id}/cancel", headers=headers)
        assert response.status_code == 200
        
        # Verify cancellation
        verify_response = api_client.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers)
        assert verify_response.json()["booking_status"] == "cancelled"
        print(f"Cancelled booking: {booking_id}")


# ============== ADMIN API ==============

class TestAdminAPI:
    """Test admin-only endpoints"""
    
    def test_admin_stats(self, api_client, admin_headers):
        """Test admin dashboard stats"""
        response = api_client.get(f"{BASE_URL}/api/admin/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_trips" in data
        assert "total_bookings" in data
        assert "pending_hosts" in data
        print(f"Admin stats - Users: {data['total_users']}, Trips: {data['total_trips']}, Bookings: {data['total_bookings']}")
    
    def test_admin_get_all_users(self, api_client, admin_headers):
        """Test admin fetching all users"""
        response = api_client.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        print(f"Total users in system: {data['total']}")
    
    def test_admin_get_all_bookings(self, api_client, admin_headers):
        """Test admin fetching all bookings"""
        response = api_client.get(f"{BASE_URL}/api/admin/bookings", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "bookings" in data
        assert "total" in data
        print(f"Total bookings in system: {data['total']}")
    
    def test_admin_access_denied_for_regular_user(self, api_client, auth_headers):
        """Test regular user cannot access admin endpoints"""
        # Re-login to get fresh token
        response = api_client.get(f"{BASE_URL}/api/admin/stats", headers=auth_headers)
        assert response.status_code in [401, 403]
        print("Admin access correctly denied for regular user")
    
    def test_admin_users_search(self, api_client, admin_headers):
        """Test admin user search"""
        response = api_client.get(f"{BASE_URL}/api/admin/users?search=admin", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        print(f"Search for 'admin' returned {len(data['users'])} users")


# ============== EDGE CASES ==============

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_invalid_json_body(self, api_client):
        """Test handling of invalid JSON"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
        print("Correctly handles invalid JSON")
    
    def test_missing_required_fields(self, api_client):
        """Test validation for missing required fields"""
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test"
            # Missing email and password
        })
        assert response.status_code == 422
        print("Correctly validates required fields")
    
    def test_pagination(self, api_client):
        """Test pagination parameters"""
        response = api_client.get(f"{BASE_URL}/api/trips?page=1&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["trips"]) <= 2
        assert data["page"] == 1
        print(f"Pagination working - Page 1, {len(data['trips'])} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
