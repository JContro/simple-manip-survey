from nltk.metrics import agreement
import nltk
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import numpy as np
from collections import defaultdict

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("../../iac/service-account-key.json")
    firebase_admin.initialize_app(cred, {
        'projectId': 'simple-manip-survey-250416',
    })

db = firestore.client()


def get_conversations_from_firestore():
    """Fetches survey response data from Firestore."""
    conversations_ref = db.collection('survey_responses')
    docs = conversations_ref.stream()
    conversations = []
    for doc in docs:
        conversations.append(doc.to_dict())
    return conversations


def get_conversations_collection():
    """Fetches conversation data from Firestore."""
    conversations_ref = db.collection('conversations')
    docs = conversations_ref.stream()
    conversations = {}
    for doc in docs:
        data = doc.to_dict()
        # Use conversation UUID as key for easy lookup
        if 'uuid' in data:
            conversations[data['uuid']] = data
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


def calculate_masi_distance(set1, set2):
    """
    Calculate MASI distance between two sets.
    MASI = Jaccard * M, where M is a monotonicity factor.

    Args:
        set1: First set of annotations
        set2: Second set of annotations

    Returns:
        MASI similarity score (1 - MASI distance)
    """
    # Handle empty sets
    if not set1 and not set2:
        return 1.0  # Perfect agreement on empty sets
    if not set1 or not set2:
        return 0.0  # No agreement when one set is empty

    # Calculate Jaccard similarity
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    jaccard = intersection / union if union > 0 else 0

    # Calculate monotonicity factor M
    if set1 == set2:  # Perfect match
        m = 1.0
    elif set1.issubset(set2) or set2.issubset(set1):  # One is subset of the other
        m = 0.67
    elif intersection > 0:  # Non-empty intersection
        m = 0.33
    else:  # Disjoint sets
        m = 0.0

    # MASI similarity = Jaccard * M
    return jaccard * m


def perform_masi_analysis(conversations):
    """
    Performs Inter-Annotator Agreement (IAA) analysis using MASI (Measuring Agreement on Set-valued Items).

    Args:
        conversations: List of conversation annotations
    """
    print("\n\n=== Performing IAA analysis using MASI ===")

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

    # Group annotations by conversation_uuid and annotator
    conversation_annotations = defaultdict(lambda: defaultdict(dict))

    for record in conversations:
        annotator = record.get('username', 'unknown_annotator')
        conversation_id = record.get(
            'conversation_uuid', 'unknown_conversation')

        for manip_type in manipulative_types:
            rating = record.get(manip_type)
            if rating is not None:
                # Convert to binary for set representation (1 if score > 4, else 0)
                try:
                    score = int(rating)
                    binary_score = 1 if score > 4 else 0
                    conversation_annotations[conversation_id][annotator][manip_type] = binary_score
                except ValueError:
                    print(
                        f"Warning: Could not convert rating '{rating}' to integer for MASI analysis.")

    # Calculate MASI for each manipulative type
    print("\nMASI scores per manipulative type:")

    for manip_type in manipulative_types:
        masi_scores = []

        # For each conversation, compare all pairs of annotators
        for conversation_id, annotators in conversation_annotations.items():
            annotator_list = list(annotators.keys())

            # Skip if less than 2 annotators for this conversation
            if len(annotator_list) < 2:
                continue

            # Compare all pairs of annotators
            for i in range(len(annotator_list)):
                for j in range(i+1, len(annotator_list)):
                    annotator1 = annotator_list[i]
                    annotator2 = annotator_list[j]

                    # Create sets of manipulative types marked as 1 by each annotator
                    set1 = {mt for mt in manipulative_types if
                            mt in annotators[annotator1] and
                            annotators[annotator1][mt] == 1 and
                            mt == manip_type}

                    set2 = {mt for mt in manipulative_types if
                            mt in annotators[annotator2] and
                            annotators[annotator2][mt] == 1 and
                            mt == manip_type}

                    # Calculate MASI for this pair and manipulative type
                    masi = calculate_masi_distance(set1, set2)
                    masi_scores.append(masi)

        # Calculate average MASI for this manipulative type
        if masi_scores:
            avg_masi = np.mean(masi_scores)
            print(f"  {manip_type}: {avg_masi:.4f}")
        else:
            print(f"  {manip_type}: No data for MASI calculation")

    # Calculate overall MASI across all manipulative types
    print("\nOverall MASI score:")
    overall_masi_scores = []

    # For each conversation, compare all pairs of annotators
    for conversation_id, annotators in conversation_annotations.items():
        annotator_list = list(annotators.keys())

        # Skip if less than 2 annotators for this conversation
        if len(annotator_list) < 2:
            continue

        # Compare all pairs of annotators
        for i in range(len(annotator_list)):
            for j in range(i+1, len(annotator_list)):
                annotator1 = annotator_list[i]
                annotator2 = annotator_list[j]

                # Create sets of manipulative types marked as 1 by each annotator
                set1 = {mt for mt in manipulative_types if
                        mt in annotators[annotator1] and
                        annotators[annotator1][mt] == 1}

                set2 = {mt for mt in manipulative_types if
                        mt in annotators[annotator2] and
                        annotators[annotator2][mt] == 1}

                # Calculate MASI for this pair across all manipulative types
                masi = calculate_masi_distance(set1, set2)
                overall_masi_scores.append(masi)

    # Calculate average overall MASI
    if overall_masi_scores:
        avg_overall_masi = np.mean(overall_masi_scores)
        print(f"  Overall: {avg_overall_masi:.4f}")
    else:
        print("  Overall: No data for MASI calculation")


def perform_prompted_iaa_analysis(survey_responses, conversations):
    """
    Performs IAA analysis based on the prompted manipulation category.

    Args:
        survey_responses: List of survey response annotations
        conversations: Dictionary of conversations with uuid as key
    """
    print("\n\n=== Performing IAA analysis based on prompted manipulation category ===")

    # Join survey responses with conversations
    joined_data = []
    for response in survey_responses:
        conversation_uuid = response.get('conversation_uuid')
        if conversation_uuid and conversation_uuid in conversations:
            # Add the prompted_as field to the response
            response_with_prompt = response.copy()
            response_with_prompt['prompted_as'] = conversations[conversation_uuid].get(
                'prompted_as', 'unknown')
            joined_data.append(response_with_prompt)

    print(f"Joined {len(joined_data)} survey responses with conversations")

    # Group responses by prompted_as
    prompted_groups = defaultdict(list)
    for response in joined_data:
        prompted_as = response.get('prompted_as', 'unknown')
        prompted_groups[prompted_as].append(response)

    # List of manipulation types
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

    # For each prompted_as group, calculate IAA for the prompted category and general
    print("\n--- IAA for prompted manipulation categories ---")
    for prompted_as, responses in prompted_groups.items():
        print(f"\nPrompted as: {prompted_as}")

        # Determine which manipulation category to analyze based on prompted_as
        target_category = None
        if prompted_as in ["emotional_blackmail", "manipulative_emotional_blackmail"]:
            target_category = "manipulative_emotional_blackmail"
        elif prompted_as in ["fear_enhancement", "manipulative_fear_enhancement"]:
            target_category = "manipulative_fear_enhancement"
        elif prompted_as in ["gaslighting", "manipulative_gaslighting"]:
            target_category = "manipulative_gaslighting"
        elif prompted_as in ["guilt_tripping", "manipulative_guilt_tripping"]:
            target_category = "manipulative_guilt_tripping"
        elif prompted_as in ["negging", "manipulative_negging"]:
            target_category = "manipulative_negging"
        elif prompted_as in ["peer_pressure", "manipulative_peer_pressure"]:
            target_category = "manipulative_peer_pressure"
        elif prompted_as in ["reciprocity", "manipulative_reciprocity"]:
            target_category = "manipulative_reciprocity"

        # Always include general category
        categories_to_analyze = ["manipulative_general"]
        if target_category:
            categories_to_analyze.append(target_category)

        # Extract annotations for the target categories
        for category in categories_to_analyze:
            annotations = []
            for response in responses:
                annotator = response.get('username', 'unknown_annotator')
                conversation_id = response.get(
                    'conversation_uuid', 'unknown_conversation')
                rating = response.get(category)
                if rating is not None:
                    annotations.append(
                        (annotator, f"{conversation_id}_{category}", str(rating)))

            if not annotations:
                print(f"  {category}: No data")
                continue

            # Calculate Krippendorff's Alpha for original scores
            task = agreement.AnnotationTask(data=annotations)
            try:
                alpha = task.alpha()
                print(f"  {category} (Original Scores): {alpha:.4f}")
            except ValueError as e:
                print(
                    f"  {category} (Original Scores): Could not calculate Alpha - {e}")

            # Calculate Krippendorff's Alpha for binary scores
            binary_annotations = []
            for annotator, item, category_val in annotations:
                try:
                    score = int(category_val)
                    binary_score = '1' if score > 4 else '0'
                    binary_annotations.append((annotator, item, binary_score))
                except ValueError:
                    pass

            if binary_annotations:
                binary_task = agreement.AnnotationTask(data=binary_annotations)
                try:
                    binary_alpha = binary_task.alpha()
                    print(f"  {category} (Binary Scores): {binary_alpha:.4f}")
                except ValueError as e:
                    print(
                        f"  {category} (Binary Scores): Could not calculate Alpha - {e}")

    # Calculate overall IAA across all prompted categories
    print("\n--- Overall IAA across all prompted categories ---")
    all_annotations = []
    all_binary_annotations = []

    for prompted_as, responses in prompted_groups.items():
        target_category = None
        if prompted_as in ["emotional_blackmail", "manipulative_emotional_blackmail"]:
            target_category = "manipulative_emotional_blackmail"
        elif prompted_as in ["fear_enhancement", "manipulative_fear_enhancement"]:
            target_category = "manipulative_fear_enhancement"
        elif prompted_as in ["gaslighting", "manipulative_gaslighting"]:
            target_category = "manipulative_gaslighting"
        elif prompted_as in ["guilt_tripping", "manipulative_guilt_tripping"]:
            target_category = "manipulative_guilt_tripping"
        elif prompted_as in ["negging", "manipulative_negging"]:
            target_category = "manipulative_negging"
        elif prompted_as in ["peer_pressure", "manipulative_peer_pressure"]:
            target_category = "manipulative_peer_pressure"
        elif prompted_as in ["reciprocity", "manipulative_reciprocity"]:
            target_category = "manipulative_reciprocity"

        if target_category:
            for response in responses:
                annotator = response.get('username', 'unknown_annotator')
                conversation_id = response.get(
                    'conversation_uuid', 'unknown_conversation')

                # Add annotations for the prompted category
                rating = response.get(target_category)
                if rating is not None:
                    all_annotations.append(
                        (annotator, f"{conversation_id}_{target_category}", str(rating)))
                    try:
                        score = int(rating)
                        binary_score = '1' if score > 4 else '0'
                        all_binary_annotations.append(
                            (annotator, f"{conversation_id}_{target_category}", binary_score))
                    except ValueError:
                        pass

                # Add annotations for the general category
                general_rating = response.get("manipulative_general")
                if general_rating is not None:
                    all_annotations.append(
                        (annotator, f"{conversation_id}_manipulative_general", str(general_rating)))
                    try:
                        score = int(general_rating)
                        binary_score = '1' if score > 4 else '0'
                        all_binary_annotations.append(
                            (annotator, f"{conversation_id}_manipulative_general", binary_score))
                    except ValueError:
                        pass

    # Calculate overall Krippendorff's Alpha
    if all_annotations:
        overall_task = agreement.AnnotationTask(data=all_annotations)
        try:
            overall_alpha = overall_task.alpha()
            print(f"Overall (Original Scores): {overall_alpha:.4f}")
        except ValueError as e:
            print(
                f"Overall (Original Scores): Could not calculate Alpha - {e}")
    else:
        print("Overall (Original Scores): No data")

    if all_binary_annotations:
        overall_binary_task = agreement.AnnotationTask(
            data=all_binary_annotations)
        try:
            overall_binary_alpha = overall_binary_task.alpha()
            print(f"Overall (Binary Scores): {overall_binary_alpha:.4f}")
        except ValueError as e:
            print(f"Overall (Binary Scores): Could not calculate Alpha - {e}")
    else:
        print("Overall (Binary Scores): No data")


if __name__ == "__main__":
    # TODO: Ensure Firebase Admin SDK is initialized before calling get_conversations_from_firestore
    # For local development, you might need to set the GOOGLE_APPLICATION_CREDENTIALS environment variable
    # or initialize with a service account key.
    # Example:
    # if not firebase_admin._apps:
    #     cred = credentials.ApplicationDefault()
    #     firebase_admin.initialize_app(cred)

    # Get survey responses and conversations
    survey_responses = get_conversations_from_firestore()
    conversations = get_conversations_collection()

    # Perform standard IAA analysis
    perform_iaa_analysis(survey_responses)
    perform_masi_analysis(survey_responses)

    # Perform IAA analysis based on prompted category
    perform_prompted_iaa_analysis(survey_responses, conversations)
