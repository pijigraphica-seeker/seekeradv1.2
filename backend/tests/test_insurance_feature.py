"""
Test Insurance Feature for Trips
Tests: 
- GET /api/trips returns has_insurance field
- PUT /api/trips/{trip_id} with has_insurance updates correctly
- Insurance field defaults to true for existing trips
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@seekeradventure.com"
ADMIN_PASSWORD = "admin123"

class TestInsuranceFeature:
    """Tests for the insurance toggle feature on trips"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in login response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_trips_returns_has_insurance_field(self):
        """Verify GET /api/trips returns trips with has_insurance field"""
        response = requests.get(f"{BASE_URL}/api/trips?limit=10")
        assert response.status_code == 200, f"GET trips failed: {response.text}"
        
        data = response.json()
        assert "trips" in data, "No trips key in response"
        
        trips = data["trips"]
        assert len(trips) > 0, "No trips found in database"
        
        # Check that all trips have has_insurance field
        for trip in trips:
            assert "has_insurance" in trip, f"Trip {trip.get('trip_id')} missing has_insurance field"
            assert isinstance(trip["has_insurance"], bool), f"has_insurance should be boolean"
            print(f"Trip {trip['trip_id']}: has_insurance={trip['has_insurance']}")
    
    def test_get_single_trip_returns_has_insurance(self):
        """Verify GET /api/trips/{trip_id} returns has_insurance"""
        # First get a trip
        response = requests.get(f"{BASE_URL}/api/trips?limit=1")
        assert response.status_code == 200
        trips = response.json()["trips"]
        assert len(trips) > 0, "No trips to test"
        
        trip_id = trips[0]["trip_id"]
        
        # Get single trip
        response = requests.get(f"{BASE_URL}/api/trips/{trip_id}")
        assert response.status_code == 200, f"GET trip failed: {response.text}"
        
        trip = response.json()
        assert "has_insurance" in trip, "Single trip missing has_insurance"
        print(f"Single trip {trip_id}: has_insurance={trip['has_insurance']}")
    
    def test_update_trip_insurance_to_false(self, admin_headers):
        """Verify PUT /api/trips/{trip_id} with has_insurance=false works"""
        # Get a trip first
        response = requests.get(f"{BASE_URL}/api/trips?limit=5")
        assert response.status_code == 200
        trips = response.json()["trips"]
        assert len(trips) > 0, "No trips to test"
        
        # Find trip_001 or use first trip
        trip = next((t for t in trips if t["trip_id"] == "trip_001"), trips[0])
        trip_id = trip["trip_id"]
        original_insurance = trip.get("has_insurance", True)
        print(f"Testing with trip {trip_id}, original has_insurance={original_insurance}")
        
        # Update to false
        response = requests.put(
            f"{BASE_URL}/api/trips/{trip_id}",
            json={"has_insurance": False},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Update trip failed: {response.text}"
        
        updated = response.json()
        assert updated["has_insurance"] == False, f"Insurance not updated to False"
        print(f"Updated {trip_id}: has_insurance={updated['has_insurance']}")
        
        # Verify persistence with GET
        response = requests.get(f"{BASE_URL}/api/trips/{trip_id}")
        assert response.status_code == 200
        verified = response.json()
        assert verified["has_insurance"] == False, "Insurance change did not persist"
        print(f"Verified {trip_id}: has_insurance={verified['has_insurance']}")
    
    def test_update_trip_insurance_to_true(self, admin_headers):
        """Verify PUT /api/trips/{trip_id} with has_insurance=true works"""
        # Get trips
        response = requests.get(f"{BASE_URL}/api/trips?limit=5")
        assert response.status_code == 200
        trips = response.json()["trips"]
        
        # Find trip_001 or use first trip
        trip = next((t for t in trips if t["trip_id"] == "trip_001"), trips[0])
        trip_id = trip["trip_id"]
        
        # Update to true
        response = requests.put(
            f"{BASE_URL}/api/trips/{trip_id}",
            json={"has_insurance": True},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Update trip failed: {response.text}"
        
        updated = response.json()
        assert updated["has_insurance"] == True, f"Insurance not updated to True"
        print(f"Updated {trip_id}: has_insurance={updated['has_insurance']}")
        
        # Verify persistence
        response = requests.get(f"{BASE_URL}/api/trips/{trip_id}")
        assert response.status_code == 200
        verified = response.json()
        assert verified["has_insurance"] == True, "Insurance change did not persist"
        print(f"Verified {trip_id}: has_insurance={verified['has_insurance']}")
    
    def test_update_trip_insurance_requires_auth(self):
        """Verify updating trip insurance requires authentication"""
        response = requests.get(f"{BASE_URL}/api/trips?limit=1")
        trips = response.json()["trips"]
        trip_id = trips[0]["trip_id"]
        
        # Try to update without auth
        response = requests.put(
            f"{BASE_URL}/api/trips/{trip_id}",
            json={"has_insurance": False},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"
        print("Correctly rejected unauthenticated update")
    
    def test_create_trip_with_insurance_false(self, admin_headers):
        """Verify creating trip with has_insurance=false works"""
        # Create a test trip with insurance=false
        test_trip = {
            "title": "TEST Insurance Off Trip",
            "description": "Test trip with insurance disabled",
            "location": "Test Location",
            "activity_type": "hiking",
            "duration": "2D1N",
            "difficulty": "Moderate",
            "price": 100,
            "deposit_price": 50,
            "max_guests": 10,
            "meeting_point": "Test Meeting Point",
            "has_insurance": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/trips",
            json=test_trip,
            headers=admin_headers
        )
        assert response.status_code == 200, f"Create trip failed: {response.text}"
        
        created = response.json()
        assert "trip_id" in created, "No trip_id in response"
        assert created["has_insurance"] == False, "Insurance should be False"
        print(f"Created trip {created['trip_id']} with has_insurance=False")
        
        # Cleanup - archive the test trip
        trip_id = created["trip_id"]
        requests.delete(f"{BASE_URL}/api/trips/{trip_id}", headers=admin_headers)
    
    def test_create_trip_with_insurance_true_default(self, admin_headers):
        """Verify creating trip defaults has_insurance to true"""
        # Create a test trip without specifying insurance
        test_trip = {
            "title": "TEST Insurance Default Trip",
            "description": "Test trip with default insurance",
            "location": "Test Location",
            "activity_type": "hiking",
            "duration": "2D1N",
            "difficulty": "Moderate",
            "price": 100,
            "deposit_price": 50,
            "max_guests": 10,
            "meeting_point": "Test Meeting Point"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/trips",
            json=test_trip,
            headers=admin_headers
        )
        assert response.status_code == 200, f"Create trip failed: {response.text}"
        
        created = response.json()
        assert created.get("has_insurance", True) == True, "Insurance should default to True"
        print(f"Created trip {created['trip_id']} with default has_insurance=True")
        
        # Cleanup
        trip_id = created["trip_id"]
        requests.delete(f"{BASE_URL}/api/trips/{trip_id}", headers=admin_headers)


class TestInsuranceRegression:
    """Regression tests for CMS, Reviews, WebDev, and Role change features"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    def test_cms_content_accessible(self, admin_headers):
        """Verify CMS content API still works"""
        response = requests.get(f"{BASE_URL}/api/content")
        assert response.status_code == 200, f"GET content failed: {response.text}"
        
        content = response.json()
        assert "hero" in content or "footer" in content, "CMS content structure unexpected"
        print("CMS content accessible")
    
    def test_cms_update_content(self, admin_headers):
        """Verify admin can update CMS content"""
        response = requests.put(
            f"{BASE_URL}/api/content/hero",
            json={"title": "Seeker Adventure", "subtitle": "Discover Your Next Adventure"},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Update content failed: {response.text}"
        print("CMS update working")
    
    def test_reviews_accessible(self, admin_headers):
        """Verify admin can access reviews"""
        response = requests.get(
            f"{BASE_URL}/api/reviews/admin/all?limit=10",
            headers=admin_headers
        )
        assert response.status_code == 200, f"GET reviews failed: {response.text}"
        
        data = response.json()
        assert "reviews" in data, "Reviews response missing reviews key"
        print(f"Reviews accessible: {len(data['reviews'])} reviews found")
    
    def test_users_accessible(self, admin_headers):
        """Verify admin can access users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users?limit=10",
            headers=admin_headers
        )
        assert response.status_code == 200, f"GET users failed: {response.text}"
        
        data = response.json()
        assert "users" in data, "Users response missing users key"
        print(f"Users accessible: {len(data['users'])} users found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
