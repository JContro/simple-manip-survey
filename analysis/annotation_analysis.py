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

    total_annotated_conversations = 0
    annotator_counts = defaultdict(int)

    for doc in docs:
        total_annotated_conversations += 1
        response_data = doc.to_dict()
        annotator_username = response_data.get("username")
        if annotator_username:
            annotator_counts[annotator_username] += 1

    print("\n--- Annotation Analysis Results ---")
    print(f"Total conversations annotated: {total_annotated_conversations}")
    print("\nConversations annotated per annotator:")
    if annotator_counts:
        for annotator, count in annotator_counts.items():
            print(f"- {annotator}: {count}")
    else:
        print("No annotator data found.")
    print("-----------------------------------")


if __name__ == "__main__":
    analyze_annotations()
