#!/usr/bin/env python3

import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def test_local_firestore():
    """
    Test connection to local Firestore emulator.
    """
    try:
        # Import after loading environment variables
        from google.cloud import firestore
        
        # Log environment variables
        project_id = os.environ.get("GCP_PROJECT_ID", "simple-manip-survey-250416")
        emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        
        logger.info("Testing Firestore connection with:")
        logger.info(f"  GCP_PROJECT_ID: {project_id}")
        logger.info(f"  FIRESTORE_EMULATOR_HOST: {emulator_host}")
        logger.info(f"  GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}")
        
        if not emulator_host:
            logger.warning("FIRESTORE_EMULATOR_HOST is not set. Are you trying to connect to production?")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                logger.info("Aborting test.")
                return False
        
        # Initialize Firestore client
        logger.info("Initializing Firestore client...")
        db = firestore.Client(project=project_id)
        
        # Test collection reference
        collection_name = "users"
        logger.info(f"Accessing collection: {collection_name}")
        collection_ref = db.collection(collection_name)
        
        # Try to get a document
        logger.info("Attempting to query documents...")
        docs = list(collection_ref.limit(1).stream())
        
        logger.info(f"Successfully connected to Firestore in project {project_id}")
        logger.info(f"Collection '{collection_name}' exists and is accessible")
        logger.info(f"Found {len(docs)} documents in the collection")
        
        # Try to create a test document
        logger.info("Creating a test document...")
        test_doc_ref = db.collection("_test_collection").document("test_doc")
        test_doc_ref.set({"test": True, "timestamp": firestore.SERVER_TIMESTAMP})
        
        # Read it back
        test_doc = test_doc_ref.get()
        logger.info(f"Test document created and retrieved: {test_doc.exists}")
        
        # Clean up
        test_doc_ref.delete()
        logger.info("Test document deleted")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Firestore connection: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_local_firestore()
    sys.exit(0 if success else 1)