import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json
from collections import defaultdict
import pprint

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("../../iac/service-account-key.json")
        firebase_admin.initialize_app(cred, {
            'projectId': 'simple-manip-survey-250416',
        })
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        print("Please ensure 'iac/service-account-key.json' exists and is valid.")
        exit()

db = firestore.client()


def get_annotations_from_firestore():
    """Fetches annotation data from Firestore."""
    print("Fetching annotation data from Firestore...")
    conversations_ref = db.collection('survey_responses')
    docs = conversations_ref.stream()
    annotations = []
    for doc in docs:
        annotations.append(doc.to_dict())
    print(f"Fetched {len(annotations)} annotation records.")
    return annotations


def load_conversations(file_path="../../data/conversations.json"):
    """Loads original conversation data from a JSON file."""
    print(f"Loading conversations from {file_path}...")
    try:
        with open(file_path, 'r') as f:
            conversations = json.load(f)
        print(f"Loaded {len(conversations)} conversations.")
        return conversations
    except FileNotFoundError:
        print(f"Error: Conversation file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return []


def analyze_disagreements(annotations, conversations):
    """Analyzes disagreements among annotators for a chosen manipulation category."""

    manipulative_types = [
        "manipulative_emotional_blackmail",
        "manipulative_fear_enhancement",
        "manipulative_gaslighting",
        "manipulative_general",
        "manipulative_guilt_tripping",
        "manipulative_negging",
        "manipulative_peer_pressure",
        "manipulative_reciprocity",
    ]

    print("\nAvailable manipulation categories:")
    for i, manip_type in enumerate(manipulative_types):
        print(f"{i + 1}. {manip_type}")

    while True:
        try:
            choice = int(
                input(f"Choose a category (1-{len(manipulative_types)}): "))
            if 1 <= choice <= len(manipulative_types):
                selected_category = manipulative_types[choice - 1]
                break
            else:
                print("Invalid choice. Please enter a number within the range.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    print(f"\nAnalyzing disagreements for category: {selected_category}")

    # Group annotations by conversation_uuid and then by annotator
    annotations_by_conversation = defaultdict(lambda: defaultdict(dict))
    for annotation in annotations:
        uuid = annotation.get('conversation_uuid')
        annotator = annotation.get('username', 'unknown_annotator')
        if uuid:
            annotations_by_conversation[uuid][annotator] = annotation

    # Create a dictionary for quick lookup of conversations by UUID
    conversations_dict = {conv.get('uuid'): conv for conv in conversations}

    disagreement_count = 0
    for uuid, annotator_annotations in annotations_by_conversation.items():
        if len(annotator_annotations) > 1:  # Check if multiple annotators
            binary_ratings = []
            for annotator, data in annotator_annotations.items():
                rating = data.get(selected_category)
                if rating is not None:
                    try:
                        score = int(rating)
                        binary_score = '1' if score > 4 else '0'
                        binary_ratings.append((annotator, binary_score))
                    except ValueError:
                        print(
                            f"Warning: Could not convert rating '{rating}' to integer for binary analysis for annotator {annotator} on conversation {uuid}.")
                        pass  # Skip this rating if not a valid integer

            if len(binary_ratings) > 1:  # Check if multiple annotators rated this category
                # Check for binary disagreement
                first_binary_rating = binary_ratings[0][1]
                if any(binary_rating[1] != first_binary_rating for binary_rating in binary_ratings[1:]):
                    disagreement_count += 1
                    print("-" * 50)
                    print(
                        f"Binary Disagreement found for Conversation UUID: {uuid}")

                    # Print the conversation
                    conversation = conversations_dict.get(uuid)
                    if conversation:
                        print("\nConversation:")
                        for message in conversation.get('conversation', []):
                            sender = message.get('sender', 'Unknown')
                            text = message.get('text', 'No text')
                            print(f"  {sender}: {text}")
                    else:
                        print(f"\nConversation with UUID {uuid} not found.")

                    # Print all annotator details for this conversation
                    print("\nAll Annotator Ratings for this Conversation:")
                    for annotator, data in annotator_annotations.items():
                        print(f"  Annotator: {annotator}")
                        for manip_type in manipulative_types:
                            rating = data.get(manip_type)
                            if rating is not None:
                                print(f"    {manip_type}: {rating}")
                        print("-" * 20)  # Separator for clarity

                    # Pause for user and check for pprint request
                    user_input = input(
                        "\nPress Enter to see the next disagreement, or 'p' to pprint the conversation data: ")
                    if user_input.lower() == 'p':
                        print("\nConversation Data (pprint):")
                        pprint.pprint(conversation.get('chat_completion'))
                        # Pause again after pprint
                        input("\nPress Enter to continue...")

    if disagreement_count == 0:
        print("\nNo disagreements found for the selected category.")
    else:
        print(
            f"\nFinished analyzing. Found {disagreement_count} conversations with disagreements in '{selected_category}'.")


if __name__ == "__main__":
    annotation_data = get_annotations_from_firestore()
    conversation_data = load_conversations()

    if annotation_data and conversation_data:
        analyze_disagreements(annotation_data, conversation_data)
    elif not annotation_data:
        print("Could not retrieve annotation data. Exiting.")
    elif not conversation_data:
        print("Could not load conversation data. Exiting.")
