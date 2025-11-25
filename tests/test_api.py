"""
Tests for the High School Management System API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_get_activities_structure(self, client):
        """Test that activity structure is correct"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup"""
        response = client.post(
            "/activities/Chess Club/signup?email=new_student@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "new_student@mergington.edu" in data["message"]

        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "new_student@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_duplicate_student(self, client):
        """Test that duplicate signup is prevented"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_nonexistent_activity(self, client):
        """Test signup for nonexistent activity"""
        response = client.post(
            "/activities/NonExistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        # Add activity with spaces
        response = client.post(
            "/activities/Programming%20Class/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200

    def test_signup_multiple_students(self, client):
        """Test multiple students can sign up"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(f"/activities/Chess Club/signup?email={email}")
            assert response.status_code == 200

        # Verify all were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        for email in emails:
            assert email in activities_data["Chess Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client):
        """Test successful unregistration"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.delete(f"/activities/Chess Club/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert email in data["message"]

        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Chess Club"]["participants"]

    def test_unregister_student_not_registered(self, client):
        """Test unregistering a student who is not registered"""
        email = "notregistered@mergington.edu"
        response = client.delete(f"/activities/Chess Club/unregister?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from nonexistent activity"""
        response = client.delete(
            "/activities/NonExistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_then_unregister(self, client):
        """Test complete workflow: signup and then unregister"""
        email = "workflow@mergington.edu"
        
        # Signup
        signup_response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify registered
        activities_response = client.get("/activities")
        assert email in activities_response.json()["Chess Club"]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/Chess Club/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregistered
        activities_response = client.get("/activities")
        assert email not in activities_response.json()["Chess Club"]["participants"]


class TestActivityBusinessLogic:
    """Tests for activity business logic and edge cases"""

    def test_activity_participant_count(self, client):
        """Test that participant counts are tracked correctly"""
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club should have 2 participants initially
        assert len(data["Chess Club"]["participants"]) == 2
        
        # Add one more
        client.post("/activities/Chess Club/signup?email=new@mergington.edu")
        
        response = client.get("/activities")
        data = response.json()
        assert len(data["Chess Club"]["participants"]) == 3

    def test_different_activities_independent(self, client):
        """Test that different activities maintain separate participant lists"""
        email = "multi@mergington.edu"
        
        # Sign up for multiple activities
        client.post(f"/activities/Chess Club/signup?email={email}")
        client.post(f"/activities/Programming Class/signup?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        
        assert email in data["Chess Club"]["participants"]
        assert email in data["Programming Class"]["participants"]
        
        # Unregister from one
        client.delete(f"/activities/Chess Club/unregister?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        
        assert email not in data["Chess Club"]["participants"]
        assert email in data["Programming Class"]["participants"]
