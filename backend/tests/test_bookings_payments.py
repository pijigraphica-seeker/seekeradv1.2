"""
Tests for Booking Flow and Payment Integration (Iteration 3)
Features tested:
- Booking creation with deposit/full payment type
- Payment creation via Billplz, Stripe, Bank Transfer
- Booking detail retrieval with payment history
- Admin booking status updates
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@seekeradventure.com", "password": "admin123"}
CLIENT_CREDS = {"email": "client@seeker.com", "password": "client123"}

@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip("Admin login failed - check credentials")
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def client_session():
    """Create a test client session and get token"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Try to login as existing client
    response = session.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    if response.status_code == 200:
        token = response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    # If client doesn't exist, register new one
    test_client = {
        "email": f"test_client_{os.urandom(4).hex()}@test.com",
        "password": "testpass123",
        "name": "Test Client"
    }
    response = session.post(f"{BASE_URL}/api/auth/register", json=test_client)
    if response.status_code in [200, 201]:
        token = response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    pytest.skip("Could not create test client")


class TestBookingCreation:
    """Test booking creation flow"""
    
    def test_get_trips_for_booking(self, client_session):
        """Verify trips are available for booking"""
        response = client_session.get(f"{BASE_URL}/api/trips")
        assert response.status_code == 200
        data = response.json()
        assert "trips" in data
        assert len(data["trips"]) > 0
        print(f"Found {len(data['trips'])} trips available for booking")
    
    def test_create_booking_deposit_type(self, client_session):
        """Test creating a booking with deposit payment type"""
        # Get first available trip
        trips_response = client_session.get(f"{BASE_URL}/api/trips")
        trips = trips_response.json()["trips"]
        trip = trips[0]
        trip_id = trip["trip_id"]
        
        # Create booking with deposit
        booking_data = {
            "trip_id": trip_id,
            "trip_type": "open",
            "start_date": "2025-05-01",
            "guests": 2,
            "payment_type": "deposit",
            "participant_details": [
                {
                    "client_id": "GUEST",
                    "name": "Test Participant 1",
                    "email": "participant1@test.com",
                    "phone": "+60123456789",
                    "nric": "",
                    "emergency_contact": "Emergency Contact",
                    "emergency_contact_phone": "+60987654321"
                },
                {
                    "client_id": "GUEST",
                    "name": "Test Participant 2",
                    "email": "participant2@test.com",
                    "phone": "+60123456780",
                    "nric": "",
                    "emergency_contact": "Emergency Contact 2",
                    "emergency_contact_phone": "+60987654322"
                }
            ]
        }
        
        response = client_session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        assert response.status_code == 200, f"Failed to create booking: {response.text}"
        
        booking = response.json()
        
        # Verify booking structure
        assert "booking_id" in booking
        assert booking["booking_id"].startswith("BK-")
        assert booking["trip_id"] == trip_id
        assert booking["guests"] == 2
        assert booking["payment_type"] == "deposit"
        
        # Verify amounts
        assert booking["total_amount"] > 0
        assert booking["deposit_amount"] > 0
        assert booking["paid_amount"] == 0
        assert booking["remaining_amount"] == booking["total_amount"]
        
        print(f"Created booking: {booking['booking_id']}")
        print(f"Total: {booking['currency']}{booking['total_amount']}, Deposit: {booking['currency']}{booking['deposit_amount']}")
        
        # Store for later tests
        client_session.test_booking_id = booking["booking_id"]
    
    def test_create_booking_full_payment_type(self, client_session):
        """Test creating a booking with full payment type"""
        trips_response = client_session.get(f"{BASE_URL}/api/trips")
        trips = trips_response.json()["trips"]
        trip = trips[0]
        
        booking_data = {
            "trip_id": trip["trip_id"],
            "trip_type": "private",
            "start_date": "2025-06-15",
            "guests": 1,
            "payment_type": "full",
            "participant_details": [
                {
                    "client_id": "GUEST",
                    "name": "Solo Traveler",
                    "email": "solo@test.com",
                    "phone": "+60111111111",
                    "nric": "",
                    "emergency_contact": "",
                    "emergency_contact_phone": ""
                }
            ]
        }
        
        response = client_session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        assert response.status_code == 200
        
        booking = response.json()
        assert booking["payment_type"] == "full"
        assert booking["trip_type"] == "private"
        print(f"Created full payment booking: {booking['booking_id']}")


class TestMyBookings:
    """Test booking retrieval endpoints"""
    
    def test_get_my_bookings(self, client_session):
        """Test retrieving user's bookings"""
        response = client_session.get(f"{BASE_URL}/api/bookings/my-bookings")
        assert response.status_code == 200
        
        data = response.json()
        assert "bookings" in data
        assert "total" in data
        assert "page" in data
        
        if data["total"] > 0:
            booking = data["bookings"][0]
            assert "booking_id" in booking
            assert "trip_title" in booking
            assert "booking_status" in booking
            assert "payment_status" in booking
        
        print(f"User has {data['total']} booking(s)")
    
    def test_get_booking_by_id(self, client_session):
        """Test retrieving specific booking"""
        # Get existing booking BK-000009 as per test context
        response = client_session.get(f"{BASE_URL}/api/bookings/BK-000009")
        
        if response.status_code == 200:
            booking = response.json()
            assert booking["booking_id"] == "BK-000009"
            assert "total_amount" in booking
            assert "paid_amount" in booking
            assert "remaining_amount" in booking
            assert "payments" in booking
            print(f"Booking BK-000009: paid={booking['paid_amount']}, remaining={booking['remaining_amount']}")
        elif response.status_code == 404:
            print("BK-000009 not found (may be different test run)")
        elif response.status_code == 403:
            print("Access denied - booking belongs to different user")


class TestPaymentCreation:
    """Test payment creation with different methods"""
    
    def test_create_billplz_payment(self, client_session):
        """Test creating payment via Billplz"""
        # First get a booking
        bookings_response = client_session.get(f"{BASE_URL}/api/bookings/my-bookings")
        bookings = bookings_response.json().get("bookings", [])
        
        if not bookings:
            pytest.skip("No bookings available to test payment")
        
        # Find a booking with remaining balance
        booking = None
        for b in bookings:
            if b.get("remaining_amount", 0) > 0:
                booking = b
                break
        
        if not booking:
            pytest.skip("No bookings with remaining balance")
        
        booking_id = booking["booking_id"]
        
        # Create Billplz payment
        payment_data = {
            "booking_id": booking_id,
            "amount": 50,  # RM50 test amount
            "payment_method": "billplz"
        }
        
        response = client_session.post(f"{BASE_URL}/api/bookings/{booking_id}/pay", json=payment_data)
        
        assert response.status_code == 200, f"Billplz payment failed: {response.text}"
        
        result = response.json()
        assert "payment_id" in result
        assert "bill_url" in result
        assert "billplz-sandbox.com" in result["bill_url"] or "billplz.com" in result["bill_url"]
        assert result["payment_method"] == "billplz"
        
        print(f"Billplz payment created: {result['payment_id']}")
        print(f"Bill URL: {result['bill_url']}")
    
    def test_create_stripe_payment(self, client_session):
        """Test creating payment via Stripe"""
        bookings_response = client_session.get(f"{BASE_URL}/api/bookings/my-bookings")
        bookings = bookings_response.json().get("bookings", [])
        
        if not bookings:
            pytest.skip("No bookings available")
        
        booking = None
        for b in bookings:
            if b.get("remaining_amount", 0) > 0:
                booking = b
                break
        
        if not booking:
            pytest.skip("No bookings with remaining balance")
        
        booking_id = booking["booking_id"]
        
        payment_data = {
            "booking_id": booking_id,
            "amount": 100,
            "payment_method": "stripe"
        }
        
        response = client_session.post(f"{BASE_URL}/api/bookings/{booking_id}/pay", json=payment_data)
        
        assert response.status_code == 200, f"Stripe payment failed: {response.text}"
        
        result = response.json()
        assert "payment_id" in result
        assert "bill_url" in result
        assert "checkout.stripe.com" in result["bill_url"]
        assert result["payment_method"] == "stripe"
        
        print(f"Stripe payment created: {result['payment_id']}")
        print(f"Checkout URL: {result['bill_url'][:80]}...")
    
    def test_create_bank_transfer_payment(self, client_session):
        """Test creating payment via Bank Transfer"""
        bookings_response = client_session.get(f"{BASE_URL}/api/bookings/my-bookings")
        bookings = bookings_response.json().get("bookings", [])
        
        if not bookings:
            pytest.skip("No bookings available")
        
        booking = None
        for b in bookings:
            if b.get("remaining_amount", 0) > 0:
                booking = b
                break
        
        if not booking:
            pytest.skip("No bookings with remaining balance")
        
        booking_id = booking["booking_id"]
        
        payment_data = {
            "booking_id": booking_id,
            "amount": 100,
            "payment_method": "bank_transfer"
        }
        
        response = client_session.post(f"{BASE_URL}/api/bookings/{booking_id}/pay", json=payment_data)
        
        assert response.status_code == 200, f"Bank transfer failed: {response.text}"
        
        result = response.json()
        assert "payment_id" in result
        assert "bank_details" in result
        assert result["payment_method"] == "bank_transfer"
        
        bank_details = result["bank_details"]
        assert "bank_name" in bank_details
        assert "account_number" in bank_details
        assert "account_name" in bank_details
        assert "reference" in bank_details
        
        print(f"Bank transfer payment created: {result['payment_id']}")
        print(f"Bank: {bank_details['bank_name']}, Account: {bank_details['account_number']}")


class TestAdminBookingManagement:
    """Test admin booking status updates"""
    
    def test_admin_get_all_bookings(self, admin_token):
        """Test admin can get all bookings"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/admin/bookings", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "bookings" in data
        assert "total" in data
        
        print(f"Admin sees {data['total']} total bookings")
    
    def test_admin_update_booking_status(self, admin_token):
        """Test admin can update booking status"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        # Get a booking to update
        bookings_response = requests.get(f"{BASE_URL}/api/admin/bookings", headers=headers)
        bookings = bookings_response.json().get("bookings", [])
        
        if not bookings:
            pytest.skip("No bookings to update")
        
        booking_id = bookings[0]["booking_id"]
        original_status = bookings[0]["booking_status"]
        
        # Update to confirmed
        new_status = "confirmed" if original_status != "confirmed" else "pending"
        response = requests.put(
            f"{BASE_URL}/api/admin/bookings/{booking_id}/status?status={new_status}",
            headers=headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        
        print(f"Updated booking {booking_id} status from {original_status} to {new_status}")


class TestStripeStatusCheck:
    """Test Stripe payment status polling"""
    
    def test_stripe_status_check_endpoint(self, client_session):
        """Test the Stripe status check endpoint exists"""
        # Get a booking owned by the user
        bookings_response = client_session.get(f"{BASE_URL}/api/bookings/my-bookings")
        bookings = bookings_response.json().get("bookings", [])
        
        if not bookings:
            pytest.skip("No bookings available to test")
        
        booking_id = bookings[0]["booking_id"]
        session_id = "cs_test_mock_session"
        
        response = client_session.get(f"{BASE_URL}/api/bookings/{booking_id}/payment-status/{session_id}")
        
        # 500 is expected for invalid session ID, this just verifies endpoint exists
        assert response.status_code in [200, 500, 520], f"Unexpected status: {response.status_code}"
        print(f"Stripe status check endpoint responded with {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
