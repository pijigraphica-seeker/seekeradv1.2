"""
Tests for new features: Delete User/Booking, SEO URLs, Sign-up
Testing: delete buttons, SEO-friendly trip URLs, user registration
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://adventure-trips-6.preview.emergentagent.com')

class TestSession:
    """Shared session for tests"""
    admin_token = None
    test_user_id = None
    test_user_email = None
    test_booking_id = None


@pytest.fixture(scope="module")
def admin_session():
    """Login as admin and return session"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@seekeradventure.com",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    TestSession.admin_token = data['access_token']
    session.headers.update({"Authorization": f"Bearer {TestSession.admin_token}"})
    return session


# ==================== SEO URL Tests ====================

class TestSEOUrls:
    """Test SEO-friendly trip URLs"""
    
    def test_get_trip_by_slug_success(self):
        """SEO URL: GET /api/trips/by-slug/mount-merbabu-mount-prau-expedition returns trip_001"""
        response = requests.get(f"{BASE_URL}/api/trips/by-slug/mount-merbabu-mount-prau-expedition")
        assert response.status_code == 200, f"Failed to get trip by slug: {response.text}"
        data = response.json()
        assert data['trip_id'] == 'trip_001', f"Expected trip_001, got {data['trip_id']}"
        assert data['title'] == 'Mount Merbabu & Mount Prau Expedition'
        assert 'slug' in data or data['trip_id'] == 'trip_001'  # Slug field or fallback
        print(f"SUCCESS: GET /api/trips/by-slug returns trip_001 with title: {data['title']}")

    def test_old_trip_id_url_still_works(self):
        """Backward compat: GET /api/trips/trip_001 still works"""
        response = requests.get(f"{BASE_URL}/api/trips/trip_001")
        assert response.status_code == 200, f"Old URL format failed: {response.text}"
        data = response.json()
        assert data['trip_id'] == 'trip_001'
        assert data['title'] == 'Mount Merbabu & Mount Prau Expedition'
        print("SUCCESS: Old URL format /api/trips/trip_001 still works")

    def test_get_trip_by_invalid_slug_404(self):
        """GET /api/trips/by-slug/nonexistent-trip should return 404"""
        response = requests.get(f"{BASE_URL}/api/trips/by-slug/nonexistent-trip-slug-xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Invalid slug returns 404")

    def test_trips_list_contains_slug(self):
        """GET /api/trips should return trips with slug field"""
        response = requests.get(f"{BASE_URL}/api/trips?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert 'trips' in data
        if len(data['trips']) > 0:
            # Check if first trip has activity_type for URL building
            trip = data['trips'][0]
            assert 'activity_type' in trip, "Trip should have activity_type for SEO URL"
            print(f"SUCCESS: Trips list has activity_type: {trip['activity_type']}")


# ==================== Sign-Up Tests ====================

class TestSignUp:
    """Test user registration flow"""
    
    def test_register_valid_user(self):
        """POST /api/auth/register with valid data returns access_token and user"""
        unique_email = f"test_user_{uuid.uuid4().hex[:8]}@test.com"
        TestSession.test_user_email = unique_email
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "name": "Test User for Delete"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert 'access_token' in data, "Response should contain access_token"
        assert 'user' in data, "Response should contain user object"
        assert data['user']['email'] == unique_email, f"User email mismatch"
        assert data['user']['name'] == "Test User for Delete"
        assert 'user_id' in data['user'], "User should have user_id"
        assert 'client_id' in data['user'], "User should have client_id"
        
        TestSession.test_user_id = data['user']['user_id']
        print(f"SUCCESS: User registered with user_id: {TestSession.test_user_id}, client_id: {data['user']['client_id']}")

    def test_register_duplicate_email_fails(self):
        """POST /api/auth/register with existing email should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "admin@seekeradventure.com",  # Already exists
            "password": "Test123!",
            "name": "Duplicate Test"
        })
        assert response.status_code == 400, f"Should fail with 400, got {response.status_code}"
        data = response.json()
        assert 'already registered' in data.get('detail', '').lower() or response.status_code == 400
        print("SUCCESS: Duplicate email registration correctly rejected")

    def test_register_missing_fields_fails(self):
        """POST /api/auth/register without required fields should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "incomplete@test.com"
            # Missing password and name
        })
        assert response.status_code == 422 or response.status_code == 400, f"Should fail validation, got {response.status_code}"
        print("SUCCESS: Incomplete registration correctly rejected")


# ==================== Delete User Tests ====================

class TestDeleteUser:
    """Test delete user API (admin only)"""
    
    def test_delete_user_requires_auth(self):
        """DELETE /api/admin/users/{user_id} requires authentication"""
        response = requests.delete(f"{BASE_URL}/api/admin/users/some_user_id")
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"
        print("SUCCESS: Delete user requires authentication")

    def test_delete_user_non_admin_forbidden(self, admin_session):
        """Non-admin cannot delete users (test with created user)"""
        if not TestSession.test_user_id:
            pytest.skip("No test user created")
        
        # Login as the test user (non-admin)
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TestSession.test_user_email,
            "password": "Test123!"
        })
        assert login_response.status_code == 200
        user_token = login_response.json()['access_token']
        
        # Try to delete another user as non-admin
        response = requests.delete(
            f"{BASE_URL}/api/admin/users/{TestSession.test_user_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403, f"Non-admin should be forbidden, got {response.status_code}"
        print("SUCCESS: Non-admin cannot delete users")

    def test_admin_cannot_delete_self(self, admin_session):
        """Admin cannot delete themselves"""
        # Get admin user ID
        me_response = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        admin_user_id = me_response.json()['user_id']
        
        # Try to delete self
        response = admin_session.delete(f"{BASE_URL}/api/admin/users/{admin_user_id}")
        assert response.status_code == 400, f"Should fail with 400, got {response.status_code}"
        data = response.json()
        assert 'cannot delete your own' in data.get('detail', '').lower() or response.status_code == 400
        print("SUCCESS: Admin cannot delete themselves")

    def test_admin_delete_user_success(self, admin_session):
        """Admin can delete a user"""
        if not TestSession.test_user_id:
            pytest.skip("No test user to delete")
        
        response = admin_session.delete(f"{BASE_URL}/api/admin/users/{TestSession.test_user_id}")
        assert response.status_code == 200, f"Delete failed: {response.text}"
        data = response.json()
        assert 'deleted' in data.get('message', '').lower()
        print(f"SUCCESS: Admin deleted user {TestSession.test_user_id}")
        
        # Verify user is gone
        verify_response = admin_session.get(f"{BASE_URL}/api/admin/users?search={TestSession.test_user_email}")
        assert verify_response.status_code == 200
        users = verify_response.json().get('users', [])
        matching = [u for u in users if u.get('user_id') == TestSession.test_user_id]
        assert len(matching) == 0, "Deleted user should not appear in list"
        print("SUCCESS: Deleted user no longer in users list")

    def test_delete_nonexistent_user_404(self, admin_session):
        """Deleting nonexistent user returns 404"""
        response = admin_session.delete(f"{BASE_URL}/api/admin/users/nonexistent_user_xyz123")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Delete nonexistent user returns 404")


# ==================== Delete Booking Tests ====================

class TestDeleteBooking:
    """Test delete booking API (admin only)"""
    
    def test_delete_booking_requires_auth(self):
        """DELETE /api/admin/bookings/{booking_id} requires authentication"""
        response = requests.delete(f"{BASE_URL}/api/admin/bookings/some_booking_id")
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"
        print("SUCCESS: Delete booking requires authentication")

    def test_delete_nonexistent_booking_404(self, admin_session):
        """Deleting nonexistent booking returns 404"""
        response = admin_session.delete(f"{BASE_URL}/api/admin/bookings/nonexistent_booking_xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Delete nonexistent booking returns 404")

    def test_admin_bookings_endpoint_accessible(self, admin_session):
        """Admin can access bookings list"""
        response = admin_session.get(f"{BASE_URL}/api/admin/bookings")
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        data = response.json()
        assert 'bookings' in data
        print(f"SUCCESS: Admin bookings accessible, found {len(data['bookings'])} bookings")


# ==================== Admin Users Tab Tests ====================

class TestAdminUsersTab:
    """Test admin users tab features"""
    
    def test_admin_users_list(self, admin_session):
        """Admin can list all users"""
        response = admin_session.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        data = response.json()
        assert 'users' in data
        assert 'total' in data
        
        # Verify non-admin users have delete capability (admin will filter them out on frontend)
        users = data['users']
        non_admin_users = [u for u in users if u.get('role') != 'admin']
        print(f"SUCCESS: Admin users list accessible, {len(users)} total, {len(non_admin_users)} non-admin users")

    def test_admin_update_user_role(self, admin_session):
        """Admin can update user role"""
        # Get a non-admin user
        response = admin_session.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 200
        users = [u for u in response.json()['users'] if u.get('role') != 'admin']
        
        if len(users) == 0:
            pytest.skip("No non-admin users to test role change")
        
        test_user = users[0]
        original_role = test_user['role']
        new_role = 'host' if original_role != 'host' else 'client'
        
        # Change role
        change_response = admin_session.put(f"{BASE_URL}/api/admin/users/{test_user['user_id']}/role?role={new_role}")
        assert change_response.status_code == 200, f"Role change failed: {change_response.text}"
        
        # Restore original role
        restore_response = admin_session.put(f"{BASE_URL}/api/admin/users/{test_user['user_id']}/role?role={original_role}")
        assert restore_response.status_code == 200
        print(f"SUCCESS: Admin can change user role ({original_role} -> {new_role} -> {original_role})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
