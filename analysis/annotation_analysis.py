import os
from collections import defaultdict
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    # Path to the service account key relative to the workspace root
    cred_path = "iac/service-account-key.json"
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'projectId': 'simple-manip-survey-250416',
    })

db = firestore.client()


def analyze_annotations():
    """
    Analyzes the survey responses to count total annotated conversations
    and the number of conversations annotated by each annotator.
    """
    print("Fetching survey responses...")
    survey_responses_ref = db.collection("survey_responses")
    docs = survey_responses_ref.stream()

    unique_conversation_uuids = set()
    annotator_counts = defaultdict(int)

    for i, doc in enumerate(docs):
        response_data = doc.to_dict()

        # Log response data for the first few documents to inspect structure
        if i < 5:
            print(f"Document {i} data: {response_data}")

        # Assuming 'conversation_uuid' is the field name
        conversation_uuid = response_data.get("conversation_uuid")
        if conversation_uuid:
            unique_conversation_uuids.add(conversation_uuid)

        annotator_username = response_data.get("username")
        if annotator_username:
            annotator_counts[annotator_username] += 1

    print("\n--- Annotation Analysis Results ---")
    print(
        f"Total unique conversations annotated: {len(unique_conversation_uuids)}")
    print("\nConversations annotated per annotator:")
    if annotator_counts:
        for annotator, count in annotator_counts.items():
            print(f"- {annotator}: {count}")
    else:
        print("No annotator data found.")
    print("-----------------------------------")

    print("\nFetching total conversations...")
    conversations_ref = db.collection("conversations")
    total_conversations_docs = conversations_ref.stream()
    total_conversations_count = sum(1 for _ in total_conversations_docs)
    print(
        f"Total conversations in 'conversations' collection: {total_conversations_count}")


if __name__ == "__main__":
    analyze_annotations()
