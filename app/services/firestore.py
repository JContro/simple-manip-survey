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
def email_exists(email: str) -> bool:
    """Checks if an email already exists in the 'emails' collection."""
    try:
        emails_collection = db.collection("emails")
        query = emails_collection.where("email", "==", email).limit(1)
        docs = query.stream()
        
        # If any document is returned, the email exists
        return any(docs)
    except Exception as e:
        print(f"Error checking for existing email in Firestore: {e}")
        # Assuming an error means we can't confirm existence,
        # treat as not existing to avoid blocking saves on error.
        # A more robust solution might handle this error differently.
        return False

def username_exists(username: str) -> bool:
    """Checks if a username already exists in the 'users' collection."""
    try:
        users_collection = db.collection("users")
        user_doc = users_collection.document(username).get()
        return user_doc.exists
    except Exception as e:
        print(f"Error checking for existing username in Firestore: {e}")
        # Assuming an error means we can't confirm existence,
        # treat as not existing to avoid blocking operations on error.
        return False

def get_emails():
    """Retrieves all emails from the 'emails' collection in Firestore."""
    try:
        emails_collection = db.collection("emails")
        docs = emails_collection.stream()
        emails_list = []
        for doc in docs:
            emails_list.append(doc.to_dict())
        print(f"Retrieved {len(emails_list)} emails from Firestore")
        return {"status": "success", "data": emails_list}
    except Exception as e:
        print(f"Error retrieving emails from Firestore: {e}")
        return {"status": "error", "message": str(e)}
def save_user_and_survey(username: str, survey_data: dict):
    """Saves user and survey data to the 'users' collection in Firestore."""
    try:
        users_collection = db.collection("users")
        user_doc_ref = users_collection.document(username) # Use username as document ID
        user_doc_ref.set({
            "username": username,
            "survey_data": survey_data,
            "timestamp": firestore.SERVER_TIMESTAMP # Use server timestamp
        })
        print(f"User '{username}' and survey data saved to Firestore")
        return {"status": "success", "message": "User and survey data saved successfully"}
    except Exception as e:
        print(f"Error saving user and survey data to Firestore: {e}")
def get_users():
    """Retrieves all users from the 'users' collection in Firestore."""
    try:
        users_collection = db.collection("users")
        docs = users_collection.stream()
        users_list = []
        for doc in docs:
            user_data = doc.to_dict()
            users_list.append(user_data)
        print(f"Retrieved {len(users_list)} users from Firestore")
        return {"status": "success", "data": users_list}
    except Exception as e:
        print(f"Error retrieving users from Firestore: {e}")
        return {"status": "error", "message": str(e)}
        return {"status": "error", "message": str(e)}

# Initialize client when the module is imported
db = get_firestore_client()