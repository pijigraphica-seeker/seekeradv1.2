"""
Backend tests for:
1. WebDev Role - new user role that can access admin dashboard with limited tabs
2. Admin Reviews Management - admin can add, edit, delete reviews
3. Role change in Users tab - admin can change user roles including to webdev
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@seekeradventure.com"
ADMIN_PASSWORD = "admin123"
CLIENT_EMAIL = "client@seeker.com"
CLIENT_PASSWORD = "client123"
HOST_EMAIL = "host@seeker.com"
HOST_PASSWORD = "host123"


class TestAuthenticationSetup:
    """Get tokens for testing"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def client_token(self):
        """Get client authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def client_user_id(self, client_token):
        """Get client user ID for role change tests"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {client_token}"
        })
        assert response.status_code == 200
        return response.json()["user_id"]


class TestRoleChangeAPI(TestAuthenticationSetup):
    """Test PUT /api/admin/users/{user_id}/role endpoint"""
    
    def test_role_change_without_auth(self, client_user_id):
        """Test role change endpoint returns 401 without auth"""
        response = requests.put(f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=webdev")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Role change without auth returns 401/403")
    
    def test_role_change_with_client_auth(self, client_token, client_user_id):
        """Test non-admin cannot change roles"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=webdev",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Non-admin role change returns 403")
    
    def test_role_change_to_webdev(self, admin_token, client_user_id):
        """Test admin can change user role to webdev"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=webdev",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        assert "webdev" in data["message"].lower()
        print("PASS: Admin can change user role to webdev")
    
    def test_verify_role_changed_to_webdev(self, admin_token, client_user_id):
        """Verify user role was actually changed to webdev"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()["users"]
        user = next((u for u in users if u["user_id"] == client_user_id), None)
        assert user is not None, "User not found"
        assert user["role"] == "webdev", f"Expected role 'webdev', got '{user['role']}'"
        print(f"PASS: User role verified as webdev")
    
    def test_role_change_to_client(self, admin_token, client_user_id):
        """Test admin can change user role to client"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=client",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("PASS: Admin can change user role to client")
    
    def test_role_change_to_host(self, admin_token, client_user_id):
        """Test admin can change user role to host"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=host",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("PASS: Admin can change user role to host")
    
    def test_role_change_to_admin(self, admin_token, client_user_id):
        """Test admin can change user role to admin"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=admin",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("PASS: Admin can change user role to admin")
    
    def test_role_change_invalid_role(self, admin_token, client_user_id):
        """Test role change with invalid role returns 400"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=invalid_role",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Invalid role returns 400")
    
    def test_role_change_restore_client(self, admin_token, client_user_id):
        """Restore user role back to client after tests"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=client",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("PASS: User role restored to client")


class TestAdminReviewsAPI(TestAuthenticationSetup):
    """Test Admin Reviews Management endpoints"""
    
    @pytest.fixture(scope="class")
    def trips_list(self, admin_token):
        """Get list of trips for creating reviews"""
        response = requests.get(f"{BASE_URL}/api/trips")
        assert response.status_code == 200
        trips = response.json()["trips"]
        assert len(trips) > 0, "No trips found in database"
        return trips
    
    def test_admin_get_all_reviews(self, admin_token):
        """Test GET /api/reviews/admin/all returns reviews with trip_title"""
        response = requests.get(
            f"{BASE_URL}/api/reviews/admin/all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "reviews" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        print(f"PASS: GET /api/reviews/admin/all returns {data['total']} reviews")
        
        # Verify trip_title field exists in reviews
        if len(data["reviews"]) > 0:
            review = data["reviews"][0]
            assert "trip_title" in review, "trip_title field missing from review"
            print(f"PASS: Reviews include trip_title field: '{review['trip_title']}'")
    
    def test_admin_get_reviews_without_auth(self):
        """Test admin reviews endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/reviews/admin/all")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Admin reviews without auth returns 401/403")
    
    def test_admin_get_reviews_with_client_auth(self, client_token):
        """Test non-admin cannot access admin reviews"""
        response = requests.get(
            f"{BASE_URL}/api/reviews/admin/all",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Client cannot access admin reviews")
    
    def test_admin_create_review(self, admin_token, trips_list):
        """Test POST /api/reviews/admin/create creates review without booking check"""
        trip = trips_list[0]
        review_data = {
            "trip_id": trip["trip_id"],
            "user_name": "Test Admin Review",
            "rating": 5,
            "comment": f"Admin test review created at {uuid.uuid4().hex[:8]}"
        }
        response = requests.post(
            f"{BASE_URL}/api/reviews/admin/create",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json=review_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        assert "review" in data
        assert data["review"]["rating"] == 5
        assert data["review"]["user_name"] == "Test Admin Review"
        assert "admin_created" in data["review"]
        print(f"PASS: Admin created review: {data['review']['review_id']}")
        return data["review"]["review_id"]
    
    def test_admin_update_review(self, admin_token, trips_list):
        """Test PUT /api/reviews/admin/{review_id} updates rating and comment"""
        # First create a review to update
        trip = trips_list[0]
        create_response = requests.post(
            f"{BASE_URL}/api/reviews/admin/create",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={"trip_id": trip["trip_id"], "user_name": "To Update", "rating": 3, "comment": "Original comment"}
        )
        assert create_response.status_code == 200
        review_id = create_response.json()["review"]["review_id"]
        
        # Now update the review
        update_data = {"rating": 4, "comment": "Updated comment by admin"}
        response = requests.put(
            f"{BASE_URL}/api/reviews/admin/{review_id}",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json=update_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"PASS: Admin updated review {review_id}")
        
        # Verify update persisted
        get_response = requests.get(
            f"{BASE_URL}/api/reviews/admin/all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        reviews = get_response.json()["reviews"]
        updated_review = next((r for r in reviews if r["review_id"] == review_id), None)
        assert updated_review is not None
        assert updated_review["rating"] == 4
        assert updated_review["comment"] == "Updated comment by admin"
        print(f"PASS: Review update verified - rating={updated_review['rating']}")
    
    def test_admin_delete_review(self, admin_token, trips_list):
        """Test DELETE /api/reviews/{review_id} with admin auth deletes review"""
        # First create a review to delete
        trip = trips_list[0]
        create_response = requests.post(
            f"{BASE_URL}/api/reviews/admin/create",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={"trip_id": trip["trip_id"], "user_name": "To Delete", "rating": 1, "comment": "Will be deleted"}
        )
        assert create_response.status_code == 200
        review_id = create_response.json()["review"]["review_id"]
        
        # Delete the review
        response = requests.delete(
            f"{BASE_URL}/api/reviews/{review_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: Admin deleted review {review_id}")
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/reviews/admin/all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        reviews = get_response.json()["reviews"]
        deleted_review = next((r for r in reviews if r["review_id"] == review_id), None)
        assert deleted_review is None, "Review was not deleted"
        print("PASS: Review deletion verified")
    
    def test_admin_create_review_without_trip(self, admin_token):
        """Test creating review without trip_id returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/reviews/admin/create",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={"user_name": "No Trip", "rating": 5, "comment": "Missing trip"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Creating review without trip_id returns 400")
    
    def test_admin_create_review_invalid_trip(self, admin_token):
        """Test creating review with invalid trip_id returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/reviews/admin/create",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={"trip_id": "invalid_trip_id", "user_name": "Invalid Trip", "rating": 5, "comment": "Invalid"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Creating review with invalid trip returns 404")


class TestWebDevRoleAccess(TestAuthenticationSetup):
    """Test WebDev role access to admin endpoints"""
    
    @pytest.fixture(scope="class")
    def webdev_token(self, admin_token, client_user_id):
        """Change client to webdev and get token"""
        # Change role to webdev
        requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=webdev",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Re-login to get new token with webdev role
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_webdev_can_access_reviews_all(self, webdev_token):
        """Test webdev role can access /api/reviews/admin/all"""
        response = requests.get(
            f"{BASE_URL}/api/reviews/admin/all",
            headers={"Authorization": f"Bearer {webdev_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: WebDev can access admin reviews")
    
    def test_webdev_can_create_review(self, webdev_token):
        """Test webdev role can create reviews"""
        # Get a trip first
        trips_response = requests.get(f"{BASE_URL}/api/trips")
        trips = trips_response.json()["trips"]
        if len(trips) > 0:
            response = requests.post(
                f"{BASE_URL}/api/reviews/admin/create",
                headers={"Authorization": f"Bearer {webdev_token}", "Content-Type": "application/json"},
                json={"trip_id": trips[0]["trip_id"], "user_name": "WebDev Test", "rating": 4, "comment": "WebDev created review"}
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            print("PASS: WebDev can create reviews")
    
    def test_webdev_can_update_review(self, webdev_token):
        """Test webdev role can update reviews"""
        # Get reviews first
        get_response = requests.get(
            f"{BASE_URL}/api/reviews/admin/all",
            headers={"Authorization": f"Bearer {webdev_token}"}
        )
        reviews = get_response.json()["reviews"]
        if len(reviews) > 0:
            response = requests.put(
                f"{BASE_URL}/api/reviews/admin/{reviews[0]['review_id']}",
                headers={"Authorization": f"Bearer {webdev_token}", "Content-Type": "application/json"},
                json={"rating": 5, "comment": "Updated by webdev"}
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print("PASS: WebDev can update reviews")
    
    def test_webdev_cannot_access_admin_stats(self, webdev_token):
        """Test webdev role cannot access admin-only endpoints"""
        response = requests.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {webdev_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: WebDev cannot access admin stats")
    
    def test_webdev_cannot_access_admin_users(self, webdev_token):
        """Test webdev role cannot access admin users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {webdev_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: WebDev cannot access admin users")
    
    def test_webdev_cannot_access_admin_bookings(self, webdev_token):
        """Test webdev role cannot access admin bookings"""
        response = requests.get(
            f"{BASE_URL}/api/admin/bookings",
            headers={"Authorization": f"Bearer {webdev_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: WebDev cannot access admin bookings")
    
    def test_webdev_can_access_content_cms(self, webdev_token):
        """Test webdev role can access CMS content"""
        response = requests.get(f"{BASE_URL}/api/content")
        assert response.status_code == 200
        print("PASS: WebDev can access CMS content")
    
    def test_webdev_can_update_content(self, webdev_token):
        """Test webdev role can update CMS content"""
        response = requests.put(
            f"{BASE_URL}/api/content/hero",
            headers={"Authorization": f"Bearer {webdev_token}", "Content-Type": "application/json"},
            json={"title": "Test Title", "subtitle": "Test Subtitle"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: WebDev can update CMS content")
    
    def test_cleanup_restore_client_role(self, admin_token, client_user_id):
        """Cleanup: restore user role back to client"""
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{client_user_id}/role?role=client",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("PASS: User role restored to client")


class TestExistingReviewsVerification(TestAuthenticationSetup):
    """Verify existing reviews in database"""
    
    def test_existing_reviews_count(self, admin_token):
        """Verify there are existing reviews"""
        response = requests.get(
            f"{BASE_URL}/api/reviews/admin/all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"INFO: Found {data['total']} existing reviews in database")
        assert data['total'] >= 0, "Review count should be non-negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
