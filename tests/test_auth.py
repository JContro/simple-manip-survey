import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.services.firestore import firestore_service
from app.services.auth import auth_service
from app.core.security import get_password_hash

client = TestClient(app)

# Mock user data
mock_user = {
    "id": "test-user-id",
    "name": "Test User",
    "email": "test@example.com",
    "hashed_password": get_password_hash("password123"),
    "created_at": "2023-01-01T00:00:00",
    "updated_at": "2023-01-01T00:00:00"
}

# Mock token
mock_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItaWQiLCJleHAiOjE2MTY0MzQ1Njd9.test_signature"

@pytest.fixture
def mock_auth():
    """Mock authentication service."""
    with patch.object(auth_service, "authenticate_user", return_value=mock_user), \
         patch.object(auth_service, "create_access_token", return_value=mock_token), \
         patch.object(auth_service, "get_current_user", return_value=mock_user):
        yield

@pytest.fixture
def mock_db():
    """Mock database service."""
    with patch.object(firestore_service, "get_user_by_email", return_value=None), \
         patch.object(firestore_service, "create_user", return_value=mock_user):
        yield

@pytest.fixture
def mock_db_with_user():
    """Mock database service with existing user."""
    with patch.object(firestore_service, "get_user_by_email", return_value=mock_user):
        yield

def test_register(mock_db):
    """Test user registration."""
    user_data = {
        "name": "New User",
        "email": "new@example.com",
        "password": "password123"
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201
    assert "id" in response.json()
    assert "name" in response.json()
    assert "email" in response.json()
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()

def test_register_existing_email(mock_db_with_user):
    """Test registration with existing email."""
    user_data = {
        "name": "Duplicate User",
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_login(mock_auth):
    """Test user login."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"] == mock_token
    assert response.json()["token_type"] == "bearer"

def test_get_current_user(mock_auth):
    """Test get current user endpoint."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == mock_user["id"]
    assert response.json()["name"] == mock_user["name"]
    assert response.json()["email"] == mock_user["email"]
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()