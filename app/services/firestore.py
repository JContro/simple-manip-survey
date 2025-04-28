from typing import Optional
import os
from google.cloud import firestore


def get_firestore_client():
    """Initializes and returns a Firestore client."""
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        # Connect to the emulator
        client = firestore.Client(
            project=os.environ.get(
                "GCP_PROJECT_ID", "simple-manip-survey-250416"),
            database="(default)"  # Use the default database for the emulator
        )
        print(
            f"Connecting to Firestore emulator at {os.environ['FIRESTORE_EMULATOR_HOST']}")
    else:
        # Use production credentials
        client = firestore.Client()
        print("Connecting to production Firestore")
    return client


def save_email(email: str):
    """Saves an email to the 'emails' collection in Firestore."""
    try:
        emails_collection = db.collection("emails")
        email_doc_ref = emails_collection.document()  # Auto-generate document ID
        email_doc_ref.set({
            "email": email,
            "timestamp": firestore.SERVER_TIMESTAMP  # Use server timestamp
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


def save_user(username: str):
    """Saves a user with only a username to the 'users' collection in Firestore."""
    try:
        users_collection = db.collection("users")
        user_doc_ref = users_collection.document(
            username)  # Use username as document ID
        user_doc_ref.set({
            "username": username,
            "timestamp": firestore.SERVER_TIMESTAMP  # Use server timestamp
        })
        print(f"User '{username}' saved to Firestore")
        return {"status": "success", "message": "User saved successfully"}
    except Exception as e:
        print(f"Error saving user to Firestore: {e}")


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


def get_user_by_username(username: str):
    """Retrieves a single user document by username from the 'users' collection."""
    try:
        users_collection = db.collection("users")
        user_doc = users_collection.document(username).get()
        if user_doc.exists:
            print(f"Retrieved user '{username}' from Firestore")
            return {"status": "success", "data": user_doc.to_dict()}
        else:
            print(f"User '{username}' not found in Firestore")
            return {"status": "not found", "message": f"User '{username}' not found"}
    except Exception as e:
        print(f"Error retrieving user '{username}' from Firestore: {e}")
        return {"status": "error", "message": str(e)}


def save_conversation(conversation_data: dict):
    """Saves a conversation to the 'conversations' collection in Firestore."""
    try:
        conversations_collection = db.collection("conversations")
        # Use the UUID from the conversation data as the document ID
        conversation_doc_ref = conversations_collection.document(
            conversation_data.get("uuid"))

        # Create a new dictionary to ensure data is properly formatted for Firestore
        data_to_save = dict(conversation_data)

        conversation_doc_ref.set(data_to_save)
        print(
            f"Conversation '{conversation_data.get('uuid')}' saved to Firestore")
        return {"status": "success", "message": "Conversation saved successfully"}
    except Exception as e:
        print(f"Error saving conversation to Firestore: {e}")
        return {"status": "error", "message": str(e)}


def get_conversations(batch: Optional[int] = None):
    """Retrieves conversations from the 'conversations' collection in Firestore, optionally filtered by batch."""
    try:
        conversations_collection = db.collection("conversations")

        query = conversations_collection.order_by(
            "uuid")  # Order by uuid for consistent results

        if batch is not None:
            query = query.where("batch", "==", batch)
            print(f"Filtering conversations by batch: {batch}")

        docs = query.stream()
        conversations_list = []
        for doc in docs:
            conversations_list.append(doc.to_dict())

        if batch is not None:
            print(
                f"Retrieved {len(conversations_list)} conversations for batch {batch} from Firestore")
        else:
            print(
                f"Retrieved {len(conversations_list)} total conversations from Firestore")

        return {"status": "success", "data": conversations_list}
    except Exception as e:
        print(f"Error retrieving conversations from Firestore: {e}")
        return {"status": "error", "message": str(e)}


def get_conversations_by_username(username: str):
    """Retrieves conversations for a user based on their assigned batches."""
    try:
        user_result = get_user_by_username(username)
        if user_result["status"] != "success":
            return user_result  # Return error or not found status from get_user_by_username

        user_data = user_result["data"]
        assigned_batches = user_data.get("batches", [])

        if not assigned_batches:
            print(f"User '{username}' has no batches assigned.")
            # Return empty list if no batches
            return {"status": "success", "data": []}

        all_conversations = []
        for batch in assigned_batches:

            conversations_result = get_conversations(batch=batch)

            if conversations_result["status"] == "success":
                all_conversations.extend(conversations_result["data"])
            else:
                print(
                    f"Warning: Could not retrieve conversations for batch {batch} for user '{username}': {conversations_result['message']}")

        print(
            f"Retrieved {len(all_conversations)} conversations for user '{username}' across batches {assigned_batches}")
        return {"status": "success", "data": all_conversations}

    except Exception as e:
        print(f"Error retrieving conversations for user '{username}': {e}")
        return {"status": "error", "message": str(e)}


def delete_all_conversations():
    """Deletes all documents in the 'conversations' collection."""
    try:
        conversations_collection = db.collection("conversations")
        docs = conversations_collection.stream()
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        print(f"Deleted {deleted_count} conversations from Firestore")
        return {"status": "success", "message": f"Deleted {deleted_count} conversations"}
    except Exception as e:
        print(f"Error deleting conversations from Firestore: {e}")
        return {"status": "error", "message": str(e)}


def get_user_batch(username: str):
    """Retrieves the assigned batch for a user from the 'users' collection."""
    try:
        users_collection = db.collection("users")
        user_doc = users_collection.document(username).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            # Assuming the user has a single assigned batch for this survey
            # You might need to adjust this if a user can have multiple active batches
            assigned_batches = user_data.get("batches", [])
            if assigned_batches:
                # For simplicity, return the first batch in the list
                return {"status": "success", "batch": assigned_batches[0]}
            else:
                return {"status": "not found", "message": f"No batch assigned to user '{username}'"}
        else:
            return {"status": "not found", "message": f"User '{username}' not found"}
    except Exception as e:
        print(f"Error retrieving batch for user '{username}': {e}")
        return {"status": "error", "message": str(e)}


def assign_batch_to_user(username: str, batch: int):
    """Assigns a batch to user - adds to the list."""
    try:
        users_collection = db.collection("users")
        user_doc_ref = users_collection.document(username)

        # Use arrayUnion to add the batch to the 'batches' array
        user_doc_ref.update({
            "batches": firestore.ArrayUnion([batch])
        })

        print(f"Batch {batch} assigned to user '{username}'")
        return {"status": "success", "message": f"Batch {batch} assigned to user '{username}'"}

    except Exception as e:
        print(f"Error assigning batch to user '{username}': {e}")
        return {"status": "error", "message": str(e)}


# Initialize client when the module is imported
db = get_firestore_client()
