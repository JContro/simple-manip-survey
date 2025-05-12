import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("../../iac/service-account-key.json")
    firebase_admin.initialize_app(cred, {
        'projectId': 'simple-manip-survey-250416',
    })

db = firestore.client()


def load_users_data():
    """Loads data from the 'users' collection."""
    print("Loading data from 'users' collection...")
    docs = db.collection('users').stream()
    data = []
    for doc in docs:
        data.append(doc.to_dict())
    print(f"Loaded {len(data)} documents from 'users'.")
    return data


def load_survey_responses_data():
    """Loads data from the 'survey_responses' collection."""
    print("Loading data from 'survey_responses' collection...")
    docs = db.collection('survey_responses').stream()
    data = []
    for doc in docs:
        data.append(doc.to_dict())
    print(f"Loaded {len(data)} documents from 'survey_responses'.")
    return data


def load_conversations_data():
    """Loads data from the 'conversations' collection."""
    print("Loading data from 'conversations' collection...")
    docs = db.collection('conversations').stream()
    data = []
    for doc in docs:
        data.append(doc.to_dict())
    print(f"Loaded {len(data)} documents from 'conversations'.")
    return data


if __name__ == "__main__":
    # Example usage:
    print("Running data loader example...")
    users_data = load_users_data()
    if users_data:
        print("First user document:", users_data[0])
    survey_responses_data = load_survey_responses_data()
    if survey_responses_data:
        print("First survey response document:", survey_responses_data[0])
    conversations_data = load_conversations_data()
    if conversations_data:
        print("First conversation document:", conversations_data[0])
    print("Data loading complete.")
