import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.services.firestore import firestore_service
from app.services.auth import auth_service

client = TestClient(app)

# Mock user data
mock_user = {
    "id": "test-user-id",
    "name": "Test User",
    "email": "test@example.com",
    "hashed_password": "hashed_password",
    "created_at": "2023-01-01T00:00:00",
    "updated_at": "2023-01-01T00:00:00"
}

# Mock token
mock_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItaWQiLCJleHAiOjE2MTY0MzQ1Njd9.test_signature"

@pytest.fixture
def mock_auth():
    """Mock authentication service."""
    with patch.object(auth_service, "get_current_user", return_value=mock_user):
        yield

@pytest.fixture
def mock_db():
    """Mock database service."""
    with patch.object(firestore_service, "get_users", return_value=[mock_user]), \
         patch.object(firestore_service, "get_user_by_id", return_value=mock_user), \
         patch.object(firestore_service, "get_user_by_email", return_value=mock_user), \
         patch.object(firestore_service, "create_user", return_value=mock_user), \
         patch.object(firestore_service, "update_user", return_value=mock_user), \
         patch.object(firestore_service, "delete_user", return_value=True):
        yield

def test_get_users(mock_auth, mock_db):
    """Test get users endpoint."""
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == mock_user["id"]

def test_get_user(mock_auth, mock_db):
    """Test get user endpoint."""
    response = client.get(
        f"/api/v1/users/{mock_user['id']}",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == mock_user["id"]

def test_create_user(mock_db):
    """Test create user endpoint."""
    user_data = {
        "name": "New User",
        "email": "new@example.com",
        "password": "password123"
    }
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201
    assert response.json()["name"] == mock_user["name"]
    assert response.json()["email"] == mock_user["email"]

def test_update_user(mock_auth, mock_db):
    """Test update user endpoint."""
    update_data = {
        "name": "Updated User"
    }
    response = client.put(
        f"/api/v1/users/{mock_user['id']}",
        json=update_data,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == mock_user["id"]

def test_delete_user(mock_auth, mock_db):
    """Test delete user endpoint."""
    response = client.delete(
        f"/api/v1/users/{mock_user['id']}",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    assert response.status_code == 204