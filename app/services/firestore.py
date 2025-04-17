import uuid
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.config import settings
from app.core.exceptions import NotFoundError, DatabaseError
from app.models.user import UserCreate, UserUpdate, UserInDB

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class FirestoreService:
    """
    Service for interacting with Firestore database.
    """
    def __init__(self):
        """
        Initialize Firestore client.
        """
        self.db = None #initialize as none, so we can check if it is initialized later
        self.collection = None

    async def initialize_firestore(self): #make this async
        """
        Initialize the Firestore client asynchronously.
        """
        # Check if we're running with the emulator
        emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")

        logger.info(f"Initializing Firestore client with project ID: {settings.GCP_PROJECT_ID}")
        logger.info(f"FIRESTORE_EMULATOR_HOST: {emulator_host}")
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

        if emulator_host:
            logger.info(f"Using Firestore emulator at {emulator_host}")
            if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                logger.info("Unsetting GOOGLE_APPLICATION_CREDENTIALS for emulator use")
            self.db = firestore.Client(project=settings.GCP_PROJECT_ID)
        else:
            logger.info("Using production Firestore")
            self.db = firestore.Client(project=settings.GCP_PROJECT_ID)

        logger.info("Firestore client initialized successfully")

        try:
            test_ref = self.db.collection("_connection_test")
            docs = list(test_ref.limit(1).stream())
            if docs:
                logger.info("Successfully verified Firestore connection and collection exists.")
            else:
                logger.info("Successfully verified Firestore connection, but collection is empty.")

        except Exception as e:
            logger.warning(f"Could not verify Firestore connection: {str(e)}")

        self.collection = self.db.collection(settings.FIRESTORE_COLLECTION)
        logger.info(f"Using collection: {settings.FIRESTORE_COLLECTION}")

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            User data or None if not found
        """
        try:
            doc_ref = self.collection.document(user_id)
            doc = doc_ref.get()
            if doc.exists:
                return {**doc.to_dict(), "id": doc.id}
            return None
        except Exception as e:
            raise DatabaseError(f"Error getting user: {str(e)}")

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by email.
        
        Args:
            email: The user email
            
        Returns:
            User data or None if not found
        """
        try:
            query = self.collection.where(filter=FieldFilter("email", "==", email))
            docs = query.stream()
            for doc in docs:
                return {**doc.to_dict(), "id": doc.id}
            return None
        except Exception as e:
            raise DatabaseError(f"Error getting user by email: {str(e)}")

    async def get_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of users.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of user data
        """
        try:
            query = self.collection.limit(limit).offset(offset)
            docs = query.stream()
            return [{**doc.to_dict(), "id": doc.id} for doc in docs]
        except Exception as e:
            raise DatabaseError(f"Error getting users: {str(e)}")

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            user_data: User data
            
        Returns:
            Created user data
        """
        try:
            # Check if email already exists
            existing_user = await self.get_user_by_email(user_data["email"])
            if existing_user:
                raise DatabaseError("User with this email already exists")
            
            # Generate ID and timestamps
            user_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Prepare user document
            user_doc = {
                **user_data,
                "created_at": now,
                "updated_at": now
            }
            
            # Save to Firestore
            doc_ref = self.collection.document(user_id)
            doc_ref.set(user_doc)
            
            return {**user_doc, "id": user_id}
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Error creating user: {str(e)}")

    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user.
        
        Args:
            user_id: The user ID
            user_data: User data to update
            
        Returns:
            Updated user data
        """
        try:
            # Check if user exists
            doc_ref = self.collection.document(user_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            # Check if email is being updated and already exists
            if "email" in user_data:
                existing_user = await self.get_user_by_email(user_data["email"])
                if existing_user and existing_user["id"] != user_id:
                    raise DatabaseError("User with this email already exists")
            
            # Update timestamp
            user_data["updated_at"] = datetime.utcnow()
            
            # Update in Firestore
            doc_ref.update(user_data)
            
            # Get updated user
            updated_doc = doc_ref.get()
            return {**updated_doc.to_dict(), "id": user_id}
        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            raise DatabaseError(f"Error updating user: {str(e)}")

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Check if user exists
            doc_ref = self.collection.document(user_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            # Delete from Firestore
            doc_ref.delete()
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Error deleting user: {str(e)}")


# Create a singleton instance
firestore_service = FirestoreService()

async def initialize_firestore_service():
    if os.environ.get('FIRESTORE_EMULATOR_HOST'):
        logger.info("Delaying Firestore initialization for 30 seconds (local development).")
        await asyncio.sleep(30)
        logger.info("Resuming Firestore initialization.")
    await firestore_service.initialize_firestore()
    return firestore_service