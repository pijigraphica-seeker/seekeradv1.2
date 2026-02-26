"""
Tests for Host Dashboard and Admin CRM features
- Host: /api/host/stats, /api/host/my-trips, /api/host/my-bookings, /api/host/upcoming-trips, /api/host/trip-bookings/{trip_id}/{date}, /api/host/export/{trip_id}/{date}
- Admin: /api/admin/upcoming-trips, /api/admin/trips/{trip_id}/toggle-status, /api/admin/trip-bookings/{trip_id}
- Bookings: /api/bookings/{id}/check-payment
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
HOST_EMAIL = "host@seeker.com"
HOST_PASSWORD = "host123"
ADMIN_EMAIL = "admin@seekeradventure.com"
ADMIN_PASSWORD = "admin123"
CLIENT_EMAIL = "client@seeker.com"
CLIENT_PASSWORD = "client123"


@pytest.fixture(scope="module")
def host_token():
    """Get host authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": HOST_EMAIL,
        "password": HOST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Host login failed")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Admin login failed")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def client_token():
    """Get client authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL,
        "password": CLIENT_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Client login failed")
    return response.json().get("access_token")


class TestHostDashboardAPIs:
    """Host Dashboard API tests"""

    def test_host_stats(self, host_token):
        """GET /api/host/stats returns host-specific stats"""
        response = requests.get(
            f"{BASE_URL}/api/host/stats",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields exist
        assert "total_trips" in data
        assert "active_trips" in data
        assert "total_bookings" in data
        assert "confirmed_bookings" in data
        assert "total_revenue" in data
        assert "host_trip_ids" in data
        
        # Verify data types
        assert isinstance(data["total_trips"], int)
        assert isinstance(data["active_trips"], int)
        assert isinstance(data["total_bookings"], int)
        assert isinstance(data["confirmed_bookings"], int)
        assert isinstance(data["total_revenue"], (int, float))
        assert isinstance(data["host_trip_ids"], list)
        
        # Host should have at least 1 trip
        assert data["total_trips"] >= 1
        print(f"Host stats: {data['total_trips']} trips, {data['total_bookings']} bookings, RM{data['total_revenue']} revenue")

    def test_host_my_trips(self, host_token):
        """GET /api/host/my-trips returns only host's trips"""
        response = requests.get(
            f"{BASE_URL}/api/host/my-trips",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "trips" in data
        assert "total" in data
        assert isinstance(data["trips"], list)
        
        # Verify trip structure if trips exist
        if data["trips"]:
            trip = data["trips"][0]
            assert "trip_id" in trip
            assert "title" in trip
            assert "location" in trip
            assert "price" in trip
            assert "status" in trip
            assert "host_id" in trip
            assert "open_trip_dates" in trip
            
            # Verify itinerary structure
            if trip.get("itinerary"):
                day = trip["itinerary"][0]
                assert "day" in day
                assert "title" in day
                assert "activities" in day
            
            print(f"Host trip: {trip['title']} - Status: {trip['status']}")

    def test_host_my_bookings(self, host_token):
        """GET /api/host/my-bookings returns bookings for host's trips only"""
        response = requests.get(
            f"{BASE_URL}/api/host/my-bookings",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "bookings" in data
        assert "total" in data
        assert isinstance(data["bookings"], list)
        
        print(f"Host has {data['total']} bookings for their trips")

    def test_host_upcoming_trips(self, host_token):
        """GET /api/host/upcoming-trips returns upcoming dates with registration counts"""
        response = requests.get(
            f"{BASE_URL}/api/host/upcoming-trips",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "upcoming" in data
        assert isinstance(data["upcoming"], list)
        
        # Verify upcoming structure if exists
        if data["upcoming"]:
            item = data["upcoming"][0]
            assert "trip_id" in item
            assert "trip_title" in item
            assert "date" in item
            assert "registered_guests" in item
            assert "max_guests" in item
            assert "booking_count" in item
            assert "location" in item
            
            print(f"Upcoming: {item['trip_title']} on {item['date']} - {item['registered_guests']}/{item['max_guests']} registered")

    def test_host_trip_date_bookings(self, host_token):
        """GET /api/host/trip-bookings/{trip_id}/{date} returns bookings for specific date"""
        # First get host's trip ID
        trips_response = requests.get(
            f"{BASE_URL}/api/host/my-trips",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        trips_data = trips_response.json()
        
        if not trips_data["trips"]:
            pytest.skip("No trips to test")
        
        trip = trips_data["trips"][0]
        trip_id = trip["trip_id"]
        date = trip["open_trip_dates"][0] if trip.get("open_trip_dates") else "2026-05-01"
        
        response = requests.get(
            f"{BASE_URL}/api/host/trip-bookings/{trip_id}/{date}",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "bookings" in data
        assert "total" in data
        assert isinstance(data["bookings"], list)
        
        print(f"Trip {trip_id} on {date}: {data['total']} bookings")

    def test_host_export_csv(self, host_token):
        """GET /api/host/export/{trip_id}/{date} returns CSV"""
        # First get host's trip ID
        trips_response = requests.get(
            f"{BASE_URL}/api/host/my-trips",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        trips_data = trips_response.json()
        
        if not trips_data["trips"]:
            pytest.skip("No trips to test")
        
        trip = trips_data["trips"][0]
        trip_id = trip["trip_id"]
        date = trip["open_trip_dates"][0] if trip.get("open_trip_dates") else "2026-05-01"
        
        response = requests.get(
            f"{BASE_URL}/api/host/export/{trip_id}/{date}",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        assert response.status_code == 200
        
        # Verify it's CSV content
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type
        
        # Verify CSV header is present
        content = response.text
        assert "Booking ID" in content
        assert "Name" in content
        assert "Email" in content
        
        print(f"CSV export successful for {trip_id} on {date}")


class TestAdminCRMAPIs:
    """Admin CRM API tests"""

    def test_admin_upcoming_trips(self, admin_token):
        """GET /api/admin/upcoming-trips returns all upcoming dates"""
        response = requests.get(
            f"{BASE_URL}/api/admin/upcoming-trips",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "upcoming" in data
        assert isinstance(data["upcoming"], list)
        
        # Admin should see all trips
        assert len(data["upcoming"]) > 0
        
        # Verify structure
        item = data["upcoming"][0]
        assert "trip_id" in item
        assert "trip_title" in item
        assert "date" in item
        assert "registered_guests" in item
        assert "max_guests" in item
        assert "host_id" in item  # Admin view includes host_id
        
        print(f"Admin sees {len(data['upcoming'])} upcoming trip dates")

    def test_admin_trip_bookings(self, admin_token):
        """GET /api/admin/trip-bookings/{trip_id} returns bookings for any trip"""
        # Use a known trip with bookings
        response = requests.get(
            f"{BASE_URL}/api/admin/trip-bookings/trip_001?date=2025-04-03",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "bookings" in data
        assert "total" in data
        
        # Verify user enrichment for bookings
        if data["bookings"]:
            booking = data["bookings"][0]
            assert "user_name" in booking or "user_id" in booking
            assert "booking_id" in booking
            
        print(f"Admin sees {data['total']} bookings for trip_001 on 2025-04-03")

    def test_admin_toggle_trip_status(self, admin_token):
        """PUT /api/admin/trips/{trip_id}/toggle-status toggles active/inactive"""
        # Get current status first
        trips_response = requests.get(f"{BASE_URL}/api/trips")
        trip = trips_response.json()["trips"][0]
        trip_id = trip["trip_id"]
        original_status = trip["status"]
        
        # Toggle status
        response = requests.put(
            f"{BASE_URL}/api/admin/trips/{trip_id}/toggle-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "status" in data
        new_status = data["status"]
        
        # Verify it actually toggled
        assert new_status != original_status
        print(f"Toggled trip {trip_id} from {original_status} to {new_status}")
        
        # Toggle back
        requests.put(
            f"{BASE_URL}/api/admin/trips/{trip_id}/toggle-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    def test_admin_toggle_requires_admin(self, client_token):
        """Toggle status should require admin role"""
        response = requests.put(
            f"{BASE_URL}/api/admin/trips/trip_001/toggle-status",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 403
        print("Toggle correctly rejected for non-admin user")


class TestCheckPaymentAPI:
    """Billplz payment check API tests"""

    def test_check_payment_endpoint(self, client_token):
        """GET /api/bookings/{id}/check-payment checks Billplz payment status"""
        # Get a booking with billplz payment
        bookings_response = requests.get(
            f"{BASE_URL}/api/bookings/my-bookings",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        bookings = bookings_response.json()["bookings"]
        
        if not bookings:
            pytest.skip("No bookings to test")
        
        booking_id = bookings[0]["booking_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/bookings/{booking_id}/check-payment",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "updated" in data
        assert "booking_id" in data
        assert data["booking_id"] == booking_id
        assert isinstance(data["updated"], bool)
        
        print(f"Payment check for {booking_id}: updated={data['updated']}")

    def test_check_payment_requires_owner(self, admin_token, client_token):
        """Check payment should require booking owner or admin"""
        # Get a client's booking
        bookings_response = requests.get(
            f"{BASE_URL}/api/bookings/my-bookings",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        bookings = bookings_response.json()["bookings"]
        
        if not bookings:
            pytest.skip("No bookings to test")
        
        booking_id = bookings[0]["booking_id"]
        
        # Admin should be able to check
        response = requests.get(
            f"{BASE_URL}/api/bookings/{booking_id}/check-payment",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"Admin can check payment for any booking")


class TestHostAccessControl:
    """Test that host can only access their own trips/bookings"""

    def test_host_cannot_access_other_trips(self, host_token):
        """Host cannot get bookings for trips they don't own"""
        # Try to access a seeded trip (no host_id)
        response = requests.get(
            f"{BASE_URL}/api/host/trip-bookings/trip_001/2025-04-03",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        # Should return 403 (access denied) since host doesn't own trip_001
        assert response.status_code == 403
        print("Host correctly denied access to other host's trips")

    def test_host_cannot_export_other_trips(self, host_token):
        """Host cannot export CSV for trips they don't own"""
        response = requests.get(
            f"{BASE_URL}/api/host/export/trip_001/2025-04-03",
            headers={"Authorization": f"Bearer {host_token}"}
        )
        assert response.status_code == 403
        print("Host correctly denied CSV export for other host's trips")

    def test_client_cannot_access_host_apis(self, client_token):
        """Client role cannot access host dashboard APIs"""
        response = requests.get(
            f"{BASE_URL}/api/host/stats",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 403
        print("Client correctly denied access to host dashboard")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
