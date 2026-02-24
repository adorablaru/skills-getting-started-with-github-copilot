"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Reset to initial state
    activities.clear()
    activities.update({
        "Soccer": {
            "description": "Team sport focusing on soccer skills and competitive play",
            "schedule": "Mondays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 22,
            "participants": ["alex@mergington.edu"]
        },
        "Tennis Club": {
            "description": "Individual and doubles tennis training",
            "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
            "max_participants": 16,
            "participants": ["james@mergington.edu"]
        },
        "Drama Club": {
            "description": "Theater production and performing arts",
            "schedule": "Tuesdays and Fridays, 4:00 PM - 5:30 PM",
            "max_participants": 25,
            "participants": ["isabella@mergington.edu", "noah@mergington.edu"]
        },
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        assert "Soccer" in data
        assert "Tennis Club" in data
        assert "Drama Club" in data
        
    def test_get_activities_has_correct_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        soccer = data["Soccer"]
        assert "description" in soccer
        assert "schedule" in soccer
        assert "max_participants" in soccer
        assert "participants" in soccer
        assert isinstance(soccer["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_student_success(self, client):
        """Test successful signup for a new student"""
        response = client.post(
            "/activities/Soccer/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Soccer"]["participants"]
    
    def test_signup_duplicate_student_fails(self, client):
        """Test that signing up the same student twice fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Soccer/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Soccer/signup?email={email}")
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a non-existent activity fails"""
        response = client.post(
            "/activities/NonExistentActivity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_multiple_students(self, client):
        """Test signing up multiple students for the same activity"""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(f"/activities/Tennis Club/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all students were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        participants = activities_data["Tennis Club"]["participants"]
        
        for email in emails:
            assert email in participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_student_success(self, client):
        """Test successful unregistering of an existing student"""
        # First, add a student
        email = "student@mergington.edu"
        client.post(f"/activities/Soccer/signup?email={email}")
        
        # Now unregister them
        response = client.delete(f"/activities/Soccer/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert email in data["message"]
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Soccer"]["participants"]
    
    def test_unregister_non_registered_student_fails(self, client):
        """Test that unregistering a non-registered student fails"""
        response = client.delete(
            "/activities/Soccer/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 404
        assert "not registered" in response.json()["detail"].lower()
    
    def test_unregister_from_nonexistent_activity_fails(self, client):
        """Test that unregistering from a non-existent activity fails"""
        response = client.delete(
            "/activities/NonExistentActivity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_initial_student(self, client):
        """Test unregistering a student that was initially in the activity"""
        # Drama Club has isabella@mergington.edu and noah@mergington.edu initially
        response = client.delete(
            "/activities/Drama Club/unregister?email=isabella@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        participants = activities_data["Drama Club"]["participants"]
        assert "isabella@mergington.edu" not in participants
        assert "noah@mergington.edu" in participants  # Other student should remain


class TestIntegrationScenarios:
    """Integration tests for common use case scenarios"""
    
    def test_complete_signup_and_unregister_flow(self, client):
        """Test complete flow of signing up and then unregistering"""
        email = "testflow@mergington.edu"
        activity = "Tennis Club"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities")
        assert len(after_signup.json()[activity]["participants"]) == initial_count + 1
        assert email in after_signup.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregister
        after_unregister = client.get("/activities")
        assert len(after_unregister.json()[activity]["participants"]) == initial_count
        assert email not in after_unregister.json()[activity]["participants"]
    
    def test_activity_names_with_spaces(self, client):
        """Test that activity names with spaces are handled correctly"""
        activities_with_spaces = ["Tennis Club", "Drama Club"]
        
        for activity in activities_with_spaces:
            # Test signup
            response = client.post(f"/activities/{activity}/signup?email=test@mergington.edu")
            assert response.status_code == 200
            
            # Test unregister
            response = client.delete(f"/activities/{activity}/unregister?email=test@mergington.edu")
            assert response.status_code == 200
