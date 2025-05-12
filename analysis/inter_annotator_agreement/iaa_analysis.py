from nltk.metrics import agreement
import nltk
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("../../iac/service-account-key.json")
    firebase_admin.initialize_app(cred, {
        'projectId': 'simple-manip-survey-250416',
    })

db = firestore.client()


def get_conversations_from_firestore():
    """Fetches conversation data from Firestore."""
    conversations_ref = db.collection('survey_responses')
    docs = conversations_ref.stream()
    conversations = []
    for doc in docs:
        conversations.append(doc.to_dict())
    return conversations


def perform_iaa_analysis(conversations):
    """
    Performs Inter-Annotator Agreement (IAA) analysis on the provided conversations
    using Krippendorff's Alpha.
    """
    print("Performing IAA analysis using Krippendorff's Alpha...")

    # Extract annotation data
    data = []
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

    # Assuming each conversation in the list is an annotation from a different annotator
    # for the same set of conversations (identified by conversation_uuid).
    # We need to restructure the data to be a list of (annotator, item, category) tuples.
    # For simplicity, let's assume the input 'conversations' list contains records
    # from multiple annotators for potentially multiple conversations.
    # We need to group by conversation_uuid and then by annotator (username).

    # A more robust approach would require knowing which records belong to which annotator
    # for each conversation_uuid. For this implementation, let's assume the input
    # 'conversations' is a flat list of annotations from potentially multiple annotators
    # across multiple conversations, and we'll process it to fit the required format.

    # Let's refine the data extraction assuming 'conversations' is a list of annotation
    # records, each with 'username', 'conversation_uuid', and the manipulative_* fields.

    annotations = []
    for record in conversations:
        annotator = record.get('username', 'unknown_annotator')
        conversation_id = record.get(
            'conversation_uuid', 'unknown_conversation')
        for manip_type in manipulative_types:
            rating = record.get(manip_type)
            if rating is not None:  # Only include if annotated
                # Item is conversation_id + manipulative type, category is the rating
                annotations.append(
                    (annotator, f"{conversation_id}_{manip_type}", str(rating)))
    import pdb
    pdb.set_trace()
    if not annotations:
        print("No annotation data found to perform analysis.")
        return

    # Calculate Krippendorff's Alpha for each manipulative type (Original Scores)
    print("\nKrippendorff's Alpha per manipulative type (Original Scores):")
    for manip_type in manipulative_types:
        # Filter annotations for the current manipulative type
        manip_annotations = [(a, item, category)
                             for a, item, category in annotations if manip_type in item]

        if not manip_annotations:
            print(f"  {manip_type}: No data")
            continue

        # Create an AnnotationTask
        task = agreement.AnnotationTask(data=manip_annotations)

        # Calculate and print Alpha
        try:
            alpha = task.alpha()
            print(f"  {manip_type}: {alpha:.4f}")
        except ValueError as e:
            print(f"  {manip_type}: Could not calculate Alpha - {e}")

    # Calculate overall Krippendorff's Alpha (Original Scores)
    print("\nOverall Krippendorff's Alpha (Original Scores):")
    if annotations:
        overall_task = agreement.AnnotationTask(data=annotations)
        try:
            overall_alpha = overall_task.alpha()
            print(f"  Overall: {overall_alpha:.4f}")
        except ValueError as e:
            print(f"  Overall: Could not calculate Alpha - {e}")
    else:
        print("  Overall: No data")

    # --- Binary Analysis ---
    print("\n--- Binary Analysis (Scores < 4 are 0, else 1) ---")

    binary_annotations = []
    for annotator, item, category in annotations:
        try:
            score = int(category)
            binary_score = '1' if score > 4 else '0'
            binary_annotations.append((annotator, item, binary_score))
        except ValueError:
            # Handle cases where category is not a valid integer
            print(
                f"Warning: Could not convert category '{category}' to integer for binary analysis.")
            pass  # Skip this annotation for binary analysis

    if not binary_annotations:
        print("No valid annotation data found for binary analysis.")
        return

    # Calculate Krippendorff's Alpha for each manipulative type (Binary Scores)
    print("\nKrippendorff's Alpha per manipulative type (Binary Scores):")
    for manip_type in manipulative_types:
        # Filter binary annotations for the current manipulative type
        binary_manip_annotations = [(a, item, category)
                                    for a, item, category in binary_annotations if manip_type in item]

        if not binary_manip_annotations:
            print(f"  {manip_type}: No data")
            continue

        # Create an AnnotationTask for binary scores
        binary_task = agreement.AnnotationTask(data=binary_manip_annotations)

        # Calculate and print Alpha for binary scores
        try:
            binary_alpha = binary_task.alpha()
            print(f"  {manip_type}: {binary_alpha:.4f}")
        except ValueError as e:
            print(f"  {manip_type}: Could not calculate Binary Alpha - {e}")

    # Calculate overall Krippendorff's Alpha (Binary Scores)
    print("\nOverall Krippendorff's Alpha (Binary Scores):")
    if binary_annotations:
        overall_binary_task = agreement.AnnotationTask(data=binary_annotations)
        try:
            overall_binary_alpha = overall_binary_task.alpha()
            print(f"  Overall: {overall_binary_alpha:.4f}")
        except ValueError as e:
            print(f"  Overall: Could not calculate Overall Binary Alpha - {e}")
    else:
        print("  Overall: No data for binary analysis")


if __name__ == "__main__":
    # TODO: Ensure Firebase Admin SDK is initialized before calling get_conversations_from_firestore
    # For local development, you might need to set the GOOGLE_APPLICATION_CREDENTIALS environment variable
    # or initialize with a service account key.
    # Example:
    # if not firebase_admin._apps:
    #     cred = credentials.ApplicationDefault()
    #     firebase_admin.initialize_app(cred)

    conversations_data = get_conversations_from_firestore()
    perform_iaa_analysis(conversations_data)
