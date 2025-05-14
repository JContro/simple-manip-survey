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

    Only includes conversations with at least 2 annotators in the analysis.
    """
    print("Performing IAA analysis using Krippendorff's Alpha...")

    # Extract annotation data
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

    # Group annotations by conversation_id and manipulative type
    annotations_by_conv_type = defaultdict(lambda: defaultdict(list))

    # First, collect all annotations grouped by conversation and manipulation type
    for record in conversations:
        annotator = record.get('username', 'unknown_annotator')
        conversation_id = record.get(
            'conversation_uuid', 'unknown_conversation')

        for manip_type in manipulative_types:
            rating = record.get(manip_type)
            if rating is not None:  # Only include if annotated
                annotations_by_conv_type[conversation_id][manip_type].append(
                    (annotator, f"{conversation_id}_{manip_type}", str(rating)))

    # Filter to include only conversations with at least 2 annotators for each type
    filtered_annotations = []
    valid_conversations = 0
    skipped_conversations = 0

    for conversation_id, manip_types in annotations_by_conv_type.items():
        conversation_included = False

        for manip_type, annotations in manip_types.items():
            # Count unique annotators for this conversation and manipulation type
            unique_annotators = set(
                annotator for annotator, _, _ in annotations)

            if len(unique_annotators) >= 2:
                # Include this conversation's annotations for this manipulation type
                filtered_annotations.extend(annotations)
                conversation_included = True
            else:
                # Skip this manipulation type for this conversation
                pass

        if conversation_included:
            valid_conversations += 1
        else:
            skipped_conversations += 1

    print(
        f"Found {valid_conversations} conversations with at least 2 annotators")
    print(
        f"Skipped {skipped_conversations} conversations with fewer than 2 annotators")

    if not filtered_annotations:
        print("No annotation data with multiple annotators found to perform analysis.")
        return

    # Calculate Krippendorff's Alpha for each manipulative type (Original Scores)
    print("\nKrippendorff's Alpha per manipulative type (Original Scores):")
    for manip_type in manipulative_types:
        # Filter annotations for the current manipulative type
        manip_annotations = [(a, item, category)
                             for a, item, category in filtered_annotations if manip_type in item]

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
    if filtered_annotations:
        overall_task = agreement.AnnotationTask(data=filtered_annotations)
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
    for annotator, item, category in filtered_annotations:
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

    # # Calculate MASI for each manipulative type
    # print("\nMASI scores per manipulative type:")
    #
    # for manip_type in manipulative_types:
    #     masi_scores = []
    #
    #     # For each conversation, compare all pairs of annotators
    #     for conversation_id, annotators in conversation_annotations.items():
    #         annotator_list = list(annotators.keys())
    #
    #         # Skip if less than 2 annotators for this conversation
    #         if len(annotator_list) < 2:
    #             continue
    #
    #         # Compare all pairs of annotators
    #         for i in range(len(annotator_list)):
    #             for j in range(i+1, len(annotator_list)):
    #                 annotator1 = annotator_list[i]
    #                 annotator2 = annotator_list[j]
    #
    #                 # Create sets of manipulative types marked as 1 by each annotator
    #                 set1 = {mt for mt in manipulative_types if
    #                         mt in annotators[annotator1] and
    #                         annotators[annotator1][mt] == 1 and
    #                         mt == manip_type}
    #
    #                 set2 = {mt for mt in manipulative_types if
    #                         mt in annotators[annotator2] and
    #                         annotators[annotator2][mt] == 1 and
    #                         mt == manip_type}
    #
    #                 # Calculate MASI for this pair and manipulative type
    #                 masi = calculate_masi_distance(set1, set2)
    #                 masi_scores.append(masi)
    #
    #     # Calculate average MASI for this manipulative type
    #     if masi_scores:
    #         avg_masi = np.mean(masi_scores)
    #         print(f"  {manip_type}: {avg_masi:.4f}")
    #     else:
    #         print(f"  {manip_type}: No data for MASI calculation")

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
    Performs IAA analysis for binary overall, general manipulation, and per prompted type.

    Args:
        survey_responses: List of survey response annotations
        conversations: Dictionary of conversations with uuid as key
    """
    print("\n=== Performing targeted IAA analysis ===")

    # Join survey responses with conversations
    joined_data = []
    for response in survey_responses:
        conversation_uuid = response.get('conversation_uuid')
        if conversation_uuid and conversation_uuid in conversations:
            response_with_prompt = response.copy()
            response_with_prompt['prompted_as'] = conversations[conversation_uuid].get(
                'prompted_as', 'unknown')
            joined_data.append(response_with_prompt)

    # Group responses by prompted_as
    prompted_groups = defaultdict(list)
    for response in joined_data:
        prompted_as = response.get('prompted_as', 'unknown')
        prompted_groups[prompted_as].append(response)

    # Mapping of prompted categories to their manipulation type keys
    prompt_to_category = {
        "emotional_blackmail": "manipulative_emotional_blackmail",
        "Emotional Blackmail": "manipulative_emotional_blackmail",
        "manipulative_emotional_blackmail": "manipulative_emotional_blackmail",
        "fear_enhancement": "manipulative_fear_enhancement",
        "Fear Enhancement": "manipulative_fear_enhancement",
        "manipulative_fear_enhancement": "manipulative_fear_enhancement",
        "gaslighting": "manipulative_gaslighting",
        "Gaslighting": "manipulative_gaslighting",
        "manipulative_gaslighting": "manipulative_gaslighting",
        "guilt_tripping": "manipulative_guilt_tripping",
        "Guilt-Tripping": "manipulative_guilt_tripping",
        "manipulative_guilt_tripping": "manipulative_guilt_tripping",
        "negging": "manipulative_negging",
        "Negging": "manipulative_negging",
        "manipulative_negging": "manipulative_negging",
        "peer_pressure": "manipulative_peer_pressure",
        "Peer Pressure": "manipulative_peer_pressure",
        "manipulative_peer_pressure": "manipulative_peer_pressure",
        "reciprocity": "manipulative_reciprocity",
        "Reciprocity Pressure": "manipulative_reciprocity",
        "manipulative_reciprocity": "manipulative_reciprocity"
    }

    # Calculate overall binary IAA and general IAA
    print("\n--- Overall Binary IAA and General Manipulation IAA ---")
    all_binary_annotations = []
    general_annotations = []

    for response in joined_data:
        annotator = response.get('username', 'unknown_annotator')
        conversation_id = response.get(
            'conversation_uuid', 'unknown_conversation')

        # Add general manipulation annotation
        general_rating = response.get("manipulative_general")
        if general_rating is not None:
            general_annotations.append(
                (annotator, f"{conversation_id}_manipulative_general", str(general_rating)))

        # Add binary annotation for any manipulation type
        # For binary overall, count as '1' if any manipulation type scores > 4
        any_high_manipulation = False
        for manip_key in [k for k in response.keys() if k.startswith('manipulative_')]:
            rating = response.get(manip_key)
            if rating is not None and int(rating) > 4:
                any_high_manipulation = True
                break

        if any_high_manipulation:
            all_binary_annotations.append(
                (annotator, f"{conversation_id}_any_manipulation", '1'))
        else:
            all_binary_annotations.append(
                (annotator, f"{conversation_id}_any_manipulation", '0'))

    # Calculate overall binary IAA
    if all_binary_annotations:
        binary_task = agreement.AnnotationTask(data=all_binary_annotations)
        try:
            binary_alpha = binary_task.alpha()
            print(f"Overall Binary IAA: {binary_alpha:.4f}")
        except ValueError as e:
            print(f"Overall Binary IAA: Could not calculate Alpha - {e}")

    # Calculate IAA for general manipulation
    if general_annotations:
        general_task = agreement.AnnotationTask(data=general_annotations)
        try:
            general_alpha = general_task.alpha()
            print(f"General Manipulation IAA: {general_alpha:.4f}")
        except ValueError as e:
            print(f"General Manipulation IAA: Could not calculate Alpha - {e}")

    # Calculate IAA per prompted manipulation type
    print("\n--- IAA for Prompted Manipulation Types ---")

    for prompted_as, responses in prompted_groups.items():
        if prompted_as == 'unknown':
            continue

        target_category = prompt_to_category.get(prompted_as)
        if not target_category:
            continue

        print(f"\nPrompted as: {prompted_as} (analyzing {target_category})")

        # Extract annotations for this manipulation type
        prompted_annotations = []

        for response in responses:
            annotator = response.get('username', 'unknown_annotator')
            conversation_id = response.get(
                'conversation_uuid', 'unknown_conversation')
            rating = response.get(target_category)

            if rating is not None:
                prompted_annotations.append(
                    (annotator, f"{conversation_id}_{target_category}", str(rating)))

        if prompted_annotations:
            # Calculate IAA for this prompted type
            prompted_task = agreement.AnnotationTask(data=prompted_annotations)
            try:
                prompted_alpha = prompted_task.alpha()
                print(f"{target_category} IAA: {prompted_alpha:.4f}")
            except ValueError as e:
                print(f"{target_category} IAA: Could not calculate Alpha - {e}")

            # Calculate binary IAA for this prompted type
            binary_prompted = []
            for annotator, item, rating in prompted_annotations:
                try:
                    score = int(rating)
                    binary_score = '1' if score > 4 else '0'
                    binary_prompted.append((annotator, item, binary_score))
                except ValueError:
                    pass

            if binary_prompted:
                binary_prompted_task = agreement.AnnotationTask(
                    data=binary_prompted)
                try:
                    binary_prompted_alpha = binary_prompted_task.alpha()
                    print(
                        f"{target_category} Binary IAA: {binary_prompted_alpha:.4f}")
                except ValueError as e:
                    print(
                        f"{target_category} Binary IAA: Could not calculate Alpha - {e}")


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

    # Perform analysis for "is the requested manipulation type present"
    perform_requested_type_presence_analysis(survey_responses, conversations)
