import os
from google.cloud import firestore

def get_firestore_client():
    """Initializes and returns a Firestore client."""
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        # Connect to the emulator
        client = firestore.Client(
            project=os.environ.get("GCP_PROJECT_ID", "simple-manip-survey-250416"),
            database="(default)" # Use the default database for the emulator
        )
        print(f"Connecting to Firestore emulator at {os.environ['FIRESTORE_EMULATOR_HOST']}")
    else:
        # Use production credentials
        client = firestore.Client()
        print("Connecting to production Firestore")
    return client

# Initialize client when the module is imported
db = get_firestore_client()