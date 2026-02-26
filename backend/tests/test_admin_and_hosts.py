"""
Backend API Tests for Admin Dashboard, Host Applications, and New Features
Tests: Admin stats, bookings management, booking status update, host applications, trips CRUD
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAdminLogin:
    """Admin authentication tests"""
    
    def test_admin_login(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@seekeradventure.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful - role: {data['user']['role']}")
        return data["access_token"]


class TestAdminStats:
    """Admin stats endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@seekeradventure.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_admin_stats(self, admin_token):
        """Test admin stats returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/admin/stats", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify all stats fields exist
        assert "total_users" in data
        assert "total_trips" in data
        assert "total_bookings" in data
        assert "pending_hosts" in data
        assert "total_revenue" in data
        assert "recent_bookings" in data
        
        print(f"✓ Admin stats: Users={data['total_users']}, Trips={data['total_trips']}, Bookings={data['total_bookings']}")


class TestAdminBookings:
    """Admin bookings management tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@seekeradventure.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_get_all_bookings(self, admin_token):
        """Test admin can get all bookings"""
        response = requests.get(f"{BASE_URL}/api/admin/bookings", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "bookings" in data
        assert "total" in data
        print(f"✓ Admin bookings: Found {data['total']} bookings")
    
    def test_update_booking_status(self, admin_token):
        """Test admin can update booking status"""
        # First get a booking
        response = requests.get(f"{BASE_URL}/api/admin/bookings?limit=1", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        if response.status_code == 200 and response.json().get("bookings"):
            booking = response.json()["bookings"][0]
            booking_id = booking["booking_id"]
            
            # Update status to confirmed
            update_response = requests.put(
                f"{BASE_URL}/api/admin/bookings/{booking_id}/status?status=confirmed",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert update_response.status_code == 200
            print(f"✓ Booking {booking_id} status updated to confirmed")
        else:
            pytest.skip("No bookings found to test")


class TestAdminUsers:
    """Admin users management tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@seekeradventure.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_get_all_users(self, admin_token):
        """Test admin can get all users"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        print(f"✓ Admin users: Found {data['total']} users")


class TestHostApplications:
    """Host application endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@seekeradventure.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_get_host_applications(self, admin_token):
        """Test admin can get host applications"""
        response = requests.get(f"{BASE_URL}/api/hosts/applications", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "applications" in data
        assert "total" in data
        print(f"✓ Host applications: Found {data['total']} applications")
    
    def test_get_pending_host_applications(self, admin_token):
        """Test admin can filter pending host applications"""
        response = requests.get(f"{BASE_URL}/api/hosts/applications?status=pending", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "applications" in data
        print(f"✓ Pending host applications: Found {data['total']} pending")


class TestTripsAPI:
    """Trips API tests for admin features"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@seekeradventure.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_get_all_trips(self):
        """Test public trips endpoint"""
        response = requests.get(f"{BASE_URL}/api/trips")
        assert response.status_code == 200
        data = response.json()
        assert "trips" in data
        assert "total" in data
        print(f"✓ Trips: Found {data['total']} trips")
    
    def test_get_featured_trips(self):
        """Test featured trips filter"""
        response = requests.get(f"{BASE_URL}/api/trips?featured=true")
        assert response.status_code == 200
        data = response.json()
        assert "trips" in data
        print(f"✓ Featured trips: Found {len(data['trips'])} featured")
    
    def test_create_trip_admin(self, admin_token):
        """Test admin can create a new trip"""
        trip_data = {
            "title": "TEST_Admin Created Trip",
            "description": "Test trip created by admin",
            "location": "Test Location, Indonesia",
            "activity_type": "hiking",
            "duration": "2D1N",
            "difficulty": "Easy",
            "price": 500,
            "deposit_price": 50,
            "currency": "RM",
            "max_guests": 10,
            "trip_type": "both",
            "meeting_point": "Test Meeting Point",
            "images": ["https://images.unsplash.com/photo-test"],
            "included": ["Guide", "Meals"],
            "open_trip_dates": []
        }
        
        response = requests.post(f"{BASE_URL}/api/trips", json=trip_data, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TEST_Admin Created Trip"
        assert "trip_id" in data
        print(f"✓ Trip created: {data['trip_id']}")
        
        # Cleanup - archive the test trip
        requests.delete(f"{BASE_URL}/api/trips/{data['trip_id']}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        print(f"✓ Test trip archived")


class TestAccessControl:
    """Test proper access control for admin endpoints"""
    
    def test_admin_stats_requires_auth(self):
        """Test admin stats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 401
        print("✓ Admin stats properly requires authentication")
    
    def test_admin_stats_requires_admin_role(self):
        """Test admin stats requires admin role"""
        # First create/login as regular user
        reg_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "testuser@example.com",
            "password": "testpass123"
        })
        
        if reg_response.status_code == 200:
            token = reg_response.json()["access_token"]
            response = requests.get(f"{BASE_URL}/api/admin/stats", headers={
                "Authorization": f"Bearer {token}"
            })
            assert response.status_code == 403
            print("✓ Admin stats properly requires admin role")
        else:
            pytest.skip("Test user not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
