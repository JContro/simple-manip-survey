import pytest
import os
from unittest.mock import patch, MagicMock

# Set test environment variables
os.environ["SECRET_KEY"] = "test_secret_key"
os.environ["GCP_PROJECT_ID"] = "test-project-id"

# Mock Firestore client
@pytest.fixture(autouse=True)
def mock_firestore_client():
    """Mock Firestore client for all tests."""
    with patch("google.cloud.firestore.Client") as mock_client:
        # Mock collection and document references
        mock_collection = MagicMock()
        mock_document = MagicMock()
        
        # Set up the mock chain
        mock_client.return_value.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        
        # Mock query methods
        mock_collection.where.return_value = mock_collection
        mock_collection.limit.return_value = mock_collection
        mock_collection.offset.return_value = mock_collection
        mock_collection.stream.return_value = []
        
        yield mock_client