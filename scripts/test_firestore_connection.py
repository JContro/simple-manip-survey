#!/usr/bin/env python3

import os
import sys
from google.cloud import firestore
from google.auth.exceptions import DefaultCredentialsError

def test_firestore_connection():
    """
    Test connection to Firestore.
    """
    print("Testing Firestore connection...")
    
    # Check if GOOGLE_APPLICATION_CREDENTIALS is set
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your service account key file.")
        print("Example: export GOOGLE_APPLICATION_CREDENTIALS=./iac/service-account-key.json")
        return False
    
    # Check if the credentials file exists
    if not os.path.exists(credentials_path):
        print(f"ERROR: Credentials file not found at {credentials_path}")
        return False
    
    # Get project ID
    project_id = os.environ.get("GCP_PROJECT_ID", "simple-manip-survey-250416")
    
    try:
        # Initialize Firestore client
        db = firestore.Client(project=project_id)
        
        # Test collection reference
        collection_name = "users"
        collection_ref = db.collection(collection_name)
        
        # Try to get a document (this won't fail even if the collection is empty)
        docs = list(collection_ref.limit(1).stream())
        
        print(f"Successfully connected to Firestore in project {project_id}")
        print(f"Collection '{collection_name}' exists and is accessible")
        print(f"Found {len(docs)} documents in the collection")
        
        return True
    except DefaultCredentialsError as e:
        print(f"ERROR: Authentication failed: {str(e)}")
        print("Please check your service account key file and permissions.")
        return False
    except Exception as e:
        print(f"ERROR: Failed to connect to Firestore: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_firestore_connection()
    sys.exit(0 if success else 1)