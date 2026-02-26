"""
CMS Content API Tests for Seeker Adventure
Tests: GET /api/content, GET /api/content/{section}, PUT /api/content/{section}
Covers: hero, features, footer, about, booking_policy sections
Auth: Admin-only for PUT operations
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@seekeradventure.com"
ADMIN_PASSWORD = "admin123"
CLIENT_EMAIL = "client@seeker.com"
CLIENT_PASSWORD = "client123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.fail(f"Admin login failed: {response.text}")


@pytest.fixture(scope="module")
def client_token():
    """Get client (non-admin) authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.fail(f"Client login failed: {response.text}")


class TestCMSGetAllContent:
    """Tests for GET /api/content - returns all sections"""

    def test_get_all_content_returns_200(self):
        """GET /api/content returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/content")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_get_all_content_has_all_sections(self):
        """GET /api/content returns hero, features, footer, about, booking_policy sections"""
        response = requests.get(f"{BASE_URL}/api/content")
        data = response.json()
        
        required_sections = ["hero", "features", "footer", "about", "booking_policy"]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"

    def test_hero_section_has_required_fields(self):
        """Hero section has title, subtitle, search_placeholder"""
        response = requests.get(f"{BASE_URL}/api/content")
        hero = response.json().get("hero", {})
        
        assert "title" in hero, "Hero missing 'title'"
        assert "subtitle" in hero, "Hero missing 'subtitle'"
        assert isinstance(hero["title"], str) and len(hero["title"]) > 0

    def test_features_section_has_required_fields(self):
        """Features section has 3 feature titles and texts"""
        response = requests.get(f"{BASE_URL}/api/content")
        features = response.json().get("features", {})
        
        for i in [1, 2, 3]:
            assert f"feature_{i}_title" in features, f"Features missing 'feature_{i}_title'"
            assert f"feature_{i}_text" in features, f"Features missing 'feature_{i}_text'"

    def test_footer_section_has_contact_info(self):
        """Footer section has email, phone_1, location, whatsapp"""
        response = requests.get(f"{BASE_URL}/api/content")
        footer = response.json().get("footer", {})
        
        assert "email" in footer, "Footer missing 'email'"
        assert "phone_1" in footer, "Footer missing 'phone_1'"
        assert "location" in footer, "Footer missing 'location'"
        assert "whatsapp" in footer, "Footer missing 'whatsapp'"

    def test_about_section_has_required_fields(self):
        """About section has title, story, mission, vision, why_choose_us"""
        response = requests.get(f"{BASE_URL}/api/content")
        about = response.json().get("about", {})
        
        required_fields = ["title", "story", "mission", "vision", "why_choose_us"]
        for field in required_fields:
            assert field in about, f"About missing '{field}'"

    def test_booking_policy_section_has_required_fields(self):
        """Booking policy has non_refundable_text, full_payment_text, min_installment"""
        response = requests.get(f"{BASE_URL}/api/content")
        policy = response.json().get("booking_policy", {})
        
        required_fields = ["non_refundable_text", "full_payment_text", "min_installment"]
        for field in required_fields:
            assert field in policy, f"Booking policy missing '{field}'"


class TestCMSGetSection:
    """Tests for GET /api/content/{section} - returns individual sections"""

    @pytest.mark.parametrize("section", ["hero", "features", "footer", "about", "booking_policy"])
    def test_get_individual_section_returns_200(self, section):
        """GET /api/content/{section} returns 200 for all valid sections"""
        response = requests.get(f"{BASE_URL}/api/content/{section}")
        assert response.status_code == 200, f"GET /api/content/{section} failed with {response.status_code}"

    def test_get_invalid_section_returns_404(self):
        """GET /api/content/invalid_section returns 404"""
        response = requests.get(f"{BASE_URL}/api/content/invalid_section_xyz")
        assert response.status_code == 404, f"Expected 404 for invalid section, got {response.status_code}"

    def test_get_hero_section_data(self):
        """GET /api/content/hero returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/content/hero")
        data = response.json()
        
        assert "title" in data
        assert "subtitle" in data
        assert isinstance(data["title"], str)

    def test_get_about_section_data(self):
        """GET /api/content/about returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/content/about")
        data = response.json()
        
        assert "title" in data
        assert "mission" in data
        assert "vision" in data


class TestCMSUpdateAuth:
    """Tests for PUT /api/content/{section} - authentication and authorization"""

    def test_update_without_auth_returns_401(self):
        """PUT without auth token returns 401"""
        response = requests.put(
            f"{BASE_URL}/api/content/hero",
            json={"title": "Test"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"

    def test_update_with_client_token_returns_403(self, client_token):
        """PUT with non-admin token returns 403"""
        response = requests.put(
            f"{BASE_URL}/api/content/hero",
            json={"title": "Test"},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {client_token}"
            }
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        assert "Admin" in response.json().get("detail", ""), "Should mention admin access required"


class TestCMSUpdateSuccess:
    """Tests for PUT /api/content/{section} - successful updates with admin auth"""

    def test_update_hero_section(self, admin_token):
        """Admin can update hero section and changes persist"""
        test_title = f"TEST_CMS_Hero_{int(time.time())}"
        
        # Update hero
        update_response = requests.put(
            f"{BASE_URL}/api/content/hero",
            json={
                "title": test_title,
                "subtitle": "Test subtitle for CMS",
                "search_placeholder": "Search..."
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}"
            }
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        assert "updated" in update_response.json().get("message", "").lower()
        
        # Verify GET returns updated data
        get_response = requests.get(f"{BASE_URL}/api/content/hero")
        hero_data = get_response.json()
        assert hero_data["title"] == test_title, "Hero title not persisted"

    def test_update_footer_section(self, admin_token):
        """Admin can update footer section (email, phone)"""
        test_email = f"test_{int(time.time())}@seekeradventure.com"
        
        # Update footer
        update_response = requests.put(
            f"{BASE_URL}/api/content/footer",
            json={
                "company_description": "Test company description",
                "email": test_email,
                "phone_1": "+60 11-7000 9999",
                "location": "Test Location",
                "whatsapp": "601170009999",
                "facebook_url": "#",
                "instagram_url": "#",
                "tiktok_url": "#"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}"
            }
        )
        assert update_response.status_code == 200, f"Footer update failed: {update_response.text}"
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/content/footer")
        footer_data = get_response.json()
        assert footer_data["email"] == test_email, "Footer email not persisted"

    def test_update_about_section(self, admin_token):
        """Admin can update about page content"""
        test_title = f"TEST_About_Title_{int(time.time())}"
        
        update_response = requests.put(
            f"{BASE_URL}/api/content/about",
            json={
                "title": test_title,
                "story": "Test story content",
                "mission": "Test mission",
                "vision": "Test vision",
                "why_choose_us": "Test why choose us"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}"
            }
        )
        assert update_response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/content/about")
        assert get_response.json()["title"] == test_title

    def test_update_features_section(self, admin_token):
        """Admin can update features section"""
        test_title = f"TEST_Feature_1_{int(time.time())}"
        
        update_response = requests.put(
            f"{BASE_URL}/api/content/features",
            json={
                "feature_1_title": test_title,
                "feature_1_text": "Test feature 1 text",
                "feature_2_title": "Test Feature 2",
                "feature_2_text": "Test feature 2 text",
                "feature_3_title": "Test Feature 3",
                "feature_3_text": "Test feature 3 text"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}"
            }
        )
        assert update_response.status_code == 200
        
        # Verify
        get_response = requests.get(f"{BASE_URL}/api/content/features")
        assert get_response.json()["feature_1_title"] == test_title

    def test_update_booking_policy_section(self, admin_token):
        """Admin can update booking policy"""
        test_text = f"TEST_Refund_Policy_{int(time.time())}"
        
        update_response = requests.put(
            f"{BASE_URL}/api/content/booking_policy",
            json={
                "non_refundable_text": test_text,
                "full_payment_text": "Test full payment text",
                "min_installment": "Test min installment"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}"
            }
        )
        assert update_response.status_code == 200
        
        # Verify
        get_response = requests.get(f"{BASE_URL}/api/content/booking_policy")
        assert get_response.json()["non_refundable_text"] == test_text

    def test_update_invalid_section_returns_400(self, admin_token):
        """PUT to invalid section returns 400"""
        response = requests.put(
            f"{BASE_URL}/api/content/invalid_section_abc",
            json={"test": "data"},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}"
            }
        )
        assert response.status_code == 400, f"Expected 400 for invalid section, got {response.status_code}"


class TestCMSCleanup:
    """Restore default content after tests"""

    def test_restore_default_content(self, admin_token):
        """Restore default content for hero, footer, about, features, booking_policy"""
        # Restore hero
        requests.put(
            f"{BASE_URL}/api/content/hero",
            json={
                "title": "Discover Your Next Adventure",
                "subtitle": "Explore breathtaking destinations with expert guides.",
                "search_placeholder": "Search adventures..."
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}
        )
        
        # Restore footer
        requests.put(
            f"{BASE_URL}/api/content/footer",
            json={
                "company_description": "Your trusted partner for adventure travel.",
                "phone_1": "+60 11-7000 1232",
                "email": "sales@seekeradventure.com",
                "location": "Indonesia",
                "whatsapp": "601170001232",
                "facebook_url": "https://facebook.com/seekeradventure",
                "instagram_url": "https://instagram.com/seekeradventure_",
                "tiktok_url": "#"
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}
        )
        
        # Restore about
        requests.put(
            f"{BASE_URL}/api/content/about",
            json={
                "title": "About Seeker Adventure",
                "story": "Born from a passion for exploring.",
                "mission": "Connect seekers with nature.",
                "vision": "Leading adventure platform.",
                "why_choose_us": "Years of experience."
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}
        )
        
        # Restore features
        requests.put(
            f"{BASE_URL}/api/content/features",
            json={
                "feature_1_title": "Expert Guides",
                "feature_1_text": "Certified adventure guides with years of experience in the field.",
                "feature_2_title": "Licensed & Professional",
                "feature_2_text": "Professional guides, permits, and certified adventure operators for your safety.",
                "feature_3_title": "Small Groups",
                "feature_3_text": "Intimate group sizes for a more personal and immersive experience."
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}
        )
        
        # Restore booking policy
        requests.put(
            f"{BASE_URL}/api/content/booking_policy",
            json={
                "non_refundable_text": "All bookings are non-refundable as per our Terms & Conditions.",
                "full_payment_text": "Full payment is required 1 month before the trip date.",
                "min_installment": "Minimum installment payment is RM100/month."
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}
        )
        
        # Verify restoration
        response = requests.get(f"{BASE_URL}/api/content/hero")
        assert response.json()["title"] == "Discover Your Next Adventure", "Hero not restored"
        
        print("All default content restored successfully")
