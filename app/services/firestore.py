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

def save_email(email: str):
    """Saves an email to the 'emails' collection in Firestore."""
    try:
        emails_collection = db.collection("emails")
        email_doc_ref = emails_collection.document() # Auto-generate document ID
        email_doc_ref.set({
            "email": email,
            "timestamp": firestore.SERVER_TIMESTAMP # Use server timestamp
        })
        print(f"Email '{email}' saved to Firestore")
        return {"status": "success", "message": "Email saved successfully"}
    except Exception as e:
        print(f"Error saving email to Firestore: {e}")
        return {"status": "error", "message": str(e)}

# Initialize client when the module is imported
db = get_firestore_client()