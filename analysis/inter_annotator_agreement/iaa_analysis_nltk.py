from nltk.metrics import agreement
from nltk.metrics.distance import masi_distance
import nltk
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import numpy as np
from collections import defaultdict
import krippendorff

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
            binary_score = '1' if score >= 4 else '0'
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


def perform_masi_analysis(conversations):
    """
    Performs Inter-Annotator Agreement (IAA) analysis using MASI (Measuring Agreement on Set-valued Items)
    using NLTK's implementation.

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

                    # Calculate MASI similarity/agreement using NLTK (1 - distance)
                    # Handle case when both sets are empty to avoid division by zero
                    if not set1 and not set2:
                        # Both sets are empty, consider them in perfect agreement
                        masi_similarity = 1.0
                    else:
                        masi_similarity = 1 - masi_distance(set1, set2)
                    masi_scores.append(masi_similarity)

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

                # Calculate MASI similarity/agreement using NLTK (1 - distance)
                # Handle case when both sets are empty to avoid division by zero
                if not set1 and not set2:
                    # Both sets are empty, consider them in perfect agreement
                    masi_similarity = 1.0
                else:
                    masi_similarity = 1 - masi_distance(set1, set2)
                overall_masi_scores.append(masi_similarity)
                # Remove debugging breakpoint
                # import pdb
                # pdb.set_trace()

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
        if prompted_as in ["emotional_blackmail", "manipulative_emotional_blackmail", "Emotional Blackmail"]:
            target_category = "manipulative_emotional_blackmail"
        elif prompted_as in ["fear_enhancement", "manipulative_fear_enhancement", "Fear Enhancement"]:
            target_category = "manipulative_fear_enhancement"
        elif prompted_as in ["gaslighting", "manipulative_gaslighting", "Gaslighting"]:
            target_category = "manipulative_gaslighting"
        elif prompted_as in ["guilt_tripping", "manipulative_guilt_tripping", "Guilt-Tripping"]:
            target_category = "manipulative_guilt_tripping"
        elif prompted_as in ["negging", "manipulative_negging", "Negging"]:
            target_category = "manipulative_negging"
        elif prompted_as in ["peer_pressure", "manipulative_peer_pressure", "Peer Pressure"]:
            target_category = "manipulative_peer_pressure"
        elif prompted_as in ["reciprocity", "manipulative_reciprocity", "Reciprocity Pressure"]:
            target_category = "manipulative_reciprocity"

        print(
            f"  Mapped prompted_as '{prompted_as}' to target category: {target_category}")

        # Always include general category
        categories_to_analyze = ["manipulative_general"]
        if target_category:
            categories_to_analyze.append(target_category)

        # Extract annotations for the target categories
        for category in categories_to_analyze:
            # First collect all annotations
            all_annotations_by_conversation = defaultdict(list)
            for response in responses:
                annotator = response.get('username', 'unknown_annotator')
                conversation_id = response.get(
                    'conversation_uuid', 'unknown_conversation')
                rating = response.get(category)
                if rating is not None:
                    all_annotations_by_conversation[conversation_id].append(
                        (annotator, f"{conversation_id}_{category}", str(rating)))

            # Filter to include only conversations with at least 2 annotators
            annotations = []
            valid_conversations = 0
            for conversation_id, conv_annotations in all_annotations_by_conversation.items():
                # Count unique annotators for this conversation
                unique_annotators = set(
                    annotator for annotator, _, _ in conv_annotations)
                if len(unique_annotators) >= 2:
                    annotations.extend(conv_annotations)
                    valid_conversations += 1

            print(
                f"  {category}: Found {valid_conversations} conversations with at least 2 annotators")

            if not annotations:
                print(f"  {category}: No data with multiple annotators")
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
                    binary_score = '1' if score >= 4 else '0'
                    binary_annotations.append((annotator, item, binary_score))
                except ValueError:
                    pass

            if binary_annotations:
                # Debug information about binary annotations
                ones_count = sum(
                    1 for _, _, score in binary_annotations if score == '1')
                zeros_count = sum(
                    1 for _, _, score in binary_annotations if score == '0')
                print(
                    f"  {category} Binary annotations: {len(binary_annotations)} total, {ones_count} ones, {zeros_count} zeros")

                # Count unique annotators and items
                unique_annotators = set(
                    annotator for annotator, _, _ in binary_annotations)
                unique_items = set(item for _, item, _ in binary_annotations)
                print(
                    f"  {category} Unique annotators: {len(unique_annotators)}, Unique items: {len(unique_items)}")

                binary_task = agreement.AnnotationTask(data=binary_annotations)
                try:
                    binary_alpha = binary_task.alpha()
                    print(f"  {category} (Binary Scores): {binary_alpha:.4f}")
                except ValueError as e:
                    print(
                        f"  {category} (Binary Scores): Could not calculate Alpha - {e}")

    # Calculate overall IAA across all prompted categories
    print("\n--- Overall IAA across all prompted categories ---")

    # First collect all annotations by conversation and category
    annotations_by_conv_category = defaultdict(lambda: defaultdict(list))

    # Debug counters
    processed_responses = 0
    matched_categories = 0

    for prompted_as, responses in prompted_groups.items():
        print(
            f"Processing {len(responses)} responses for prompted_as: {prompted_as}")

        target_category = None
        if prompted_as in ["emotional_blackmail", "manipulative_emotional_blackmail", "Emotional Blackmail"]:
            target_category = "manipulative_emotional_blackmail"
        elif prompted_as in ["fear_enhancement", "manipulative_fear_enhancement", "Fear Enhancement"]:
            target_category = "manipulative_fear_enhancement"
        elif prompted_as in ["gaslighting", "manipulative_gaslighting", "Gaslighting"]:
            target_category = "manipulative_gaslighting"
        elif prompted_as in ["guilt_tripping", "manipulative_guilt_tripping", "Guilt-Tripping"]:
            target_category = "manipulative_guilt_tripping"
        elif prompted_as in ["negging", "manipulative_negging", "Negging"]:
            target_category = "manipulative_negging"
        elif prompted_as in ["peer_pressure", "manipulative_peer_pressure", "Peer Pressure"]:
            target_category = "manipulative_peer_pressure"
        elif prompted_as in ["reciprocity", "manipulative_reciprocity", "Reciprocity Pressure"]:
            target_category = "manipulative_reciprocity"

        print(f"  Mapped to target category: {target_category}")

        for response in responses:
            processed_responses += 1
            annotator = response.get('username', 'unknown_annotator')
            conversation_id = response.get(
                'conversation_uuid', 'unknown_conversation')

            if target_category:
                # Add annotations for the prompted category
                rating = response.get(target_category)
                if rating is not None:
                    matched_categories += 1
                    annotations_by_conv_category[conversation_id][target_category].append(
                        (annotator, f"{conversation_id}_{target_category}", str(rating)))

            # Add annotations for the general category
            general_rating = response.get("manipulative_general")
            if general_rating is not None:
                annotations_by_conv_category[conversation_id]["manipulative_general"].append(
                    (annotator, f"{conversation_id}_manipulative_general", str(general_rating)))

    print(f"\nProcessed {processed_responses} total responses")
    print(f"Found {matched_categories} matching target categories")

    # Now filter to include only conversations with at least 2 annotators per category
    all_annotations = []
    all_binary_annotations = []
    valid_conversations = 0

    for conversation_id, categories in annotations_by_conv_category.items():
        for category, annotations in categories.items():
            # Count unique annotators for this conversation and category
            unique_annotators = set(
                annotator for annotator, _, _ in annotations)

            if len(unique_annotators) >= 2:
                valid_conversations += 1
                # Add to all_annotations
                all_annotations.extend(annotations)

                # Create binary annotations
                for annotator, item, category_val in annotations:
                    try:
                        score = int(category_val)
                        binary_score = '1' if score >= 4 else '0'
                        all_binary_annotations.append(
                            (annotator, item, binary_score))
                    except ValueError:
                        pass

    print(
        f"Found {valid_conversations} valid conversation-category pairs with at least 2 annotators")

    # Debug information about all annotations
    print(
        f"\nTotal annotations collected for overall IAA: {len(all_annotations)}")
    print(
        f"Total binary annotations collected for overall IAA: {len(all_binary_annotations)}")

    # Calculate overall Krippendorff's Alpha
    if all_annotations:
        # Count unique annotators, items, and conversations
        unique_annotators = set(annotator for annotator,
                                _, _ in all_annotations)
        unique_items = set(item for _, item, _ in all_annotations)
        unique_conversations = set(item.split(
            '_')[0] for _, item, _ in all_annotations)

        print(f"Unique annotators: {len(unique_annotators)}")
        print(f"Unique items: {len(unique_items)}")
        print(f"Unique conversations: {len(unique_conversations)}")

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
        # Debug information about binary annotations
        ones_count = sum(
            1 for _, _, score in all_binary_annotations if score == '1')
        zeros_count = sum(
            1 for _, _, score in all_binary_annotations if score == '0')
        print(
            f"Binary annotations: {len(all_binary_annotations)} total, {ones_count} ones, {zeros_count} zeros")

        # Count unique annotators and items for binary annotations
        unique_binary_annotators = set(
            annotator for annotator, _, _ in all_binary_annotations)
        unique_binary_items = set(
            item for _, item, _ in all_binary_annotations)
        print(f"Unique binary annotators: {len(unique_binary_annotators)}")
        print(f"Unique binary items: {len(unique_binary_items)}")

        overall_binary_task = agreement.AnnotationTask(
            data=all_binary_annotations)
        try:
            overall_binary_alpha = overall_binary_task.alpha()
            print(f"Overall (Binary Scores): {overall_binary_alpha:.4f}")
        except ValueError as e:
            print(f"Overall (Binary Scores): Could not calculate Alpha - {e}")
    else:
        print("Overall (Binary Scores): No data")


def custom_masi_distance(v1, v2):
    """
    Implement MASI distance between two sets v1 and v2
    MASI = 1 - (|v1 ∩ v2| / |v1 ∪ v2|) * m
    where m reflects the relationship between sets

    Args:
        v1: First set (or list/tuple that will be converted to set)
        v2: Second set (or list/tuple that will be converted to set)

    Returns:
        float: MASI distance between the two sets
    """
    # Convert to sets if they aren't already
    v1_set = set(v1) if not isinstance(v1, set) else v1
    v2_set = set(v2) if not isinstance(v2, set) else v2

    if not v1_set and not v2_set:  # Both empty
        return 0

    intersection = len(v1_set & v2_set)
    union = len(v1_set | v2_set)

    # Calculate monotonicity factor
    if v1_set == v2_set:  # Identity
        m = 1
    elif v1_set.issubset(v2_set) or v2_set.issubset(v1_set):  # Containment
        m = 2/3
    elif intersection > 0:  # Overlap
        m = 1/3
    else:  # Disjoint
        m = 0

    jaccard = intersection / union if union > 0 else 0
    return 1 - (jaccard * m)


def perform_krippendorff_masi_analysis(conversations):
    """
    Performs Inter-Annotator Agreement (IAA) analysis using Krippendorff's alpha
    with a custom MASI distance function.

    This implementation uses the krippendorff package rather than NLTK's implementation,
    allowing for a custom distance metric.

    Args:
        conversations: List of conversation annotations
    """
    print("\n\n=== Performing IAA analysis using Krippendorff's alpha with custom MASI distance ===")

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
                try:
                    # Convert to integer for analysis
                    score = int(rating)
                    annotations_by_conv_type[conversation_id][manip_type].append(
                        (annotator, score))
                except ValueError:
                    print(
                        f"Warning: Could not convert rating '{rating}' to integer for Krippendorff analysis.")

    print("\n--- Original Scores Analysis ---")

    # For each manipulation type, calculate Krippendorff's alpha
    for manip_type in manipulative_types:
        # Prepare reliability data for Krippendorff's alpha
        reliability_data = []

        # Get all conversations with this manipulation type
        conversations_with_type = {conv_id: annotations for conv_id, annotations
                                   in annotations_by_conv_type.items()
                                   if manip_type in annotations}

        # Skip if no conversations have this type
        if not conversations_with_type:
            print(f"  {manip_type}: No data")
            continue

        # Get all unique annotators across all conversations
        all_annotators = set()
        for conv_annotations in conversations_with_type.values():
            for manip_annotations in conv_annotations.values():
                for annotator, _ in manip_annotations:
                    all_annotators.add(annotator)

        # Convert to list for consistent ordering
        all_annotators = sorted(list(all_annotators))

        # For each conversation, create a row in the reliability data
        for conv_id, conv_annotations in conversations_with_type.items():
            if manip_type not in conv_annotations:
                continue

            # Skip conversations with only one annotator
            if len(set(annotator for annotator, _ in conv_annotations[manip_type])) < 2:
                continue

            # Create a row for each annotator (with missing values for annotators who didn't rate this item)
            annotator_scores = {annotator: score for annotator,
                                score in conv_annotations[manip_type]}

            # Add a row to reliability_data with each annotator's score (or None if missing)
            row = [annotator_scores.get(annotator)
                   for annotator in all_annotators]
            reliability_data.append(row)

        # Skip if no valid data
        if not reliability_data:
            print(f"  {manip_type}: No valid data with multiple annotators")
            continue

        # Calculate Krippendorff's alpha with the custom MASI distance function
        try:
            # For original scores, we use the default interval metric
            alpha = krippendorff.alpha(reliability_data=reliability_data)
            print(f"  {manip_type}: {alpha:.4f}")
        except Exception as e:
            print(f"  {manip_type}: Could not calculate Alpha - {e}")

    # Calculate overall Krippendorff's alpha across all manipulation types
    print("\nOverall Krippendorff's alpha (Original Scores):")

    # Prepare overall reliability data
    overall_reliability_data = []
    all_annotators = set()

    # Get all unique annotators across all conversations and types
    for conv_annotations in annotations_by_conv_type.values():
        for manip_annotations in conv_annotations.values():
            for annotator, _ in manip_annotations:
                all_annotators.add(annotator)

    # Convert to list for consistent ordering
    all_annotators = sorted(list(all_annotators))

    # For each conversation and manipulation type, create a row in the reliability data
    for conv_id, conv_annotations in annotations_by_conv_type.items():
        for manip_type, manip_annotations in conv_annotations.items():
            # Skip items with only one annotator
            if len(set(annotator for annotator, _ in manip_annotations)) < 2:
                continue

            # Create a row for each annotator
            annotator_scores = {
                annotator: score for annotator, score in manip_annotations}

            # Add a row to reliability_data with each annotator's score (or None if missing)
            row = [annotator_scores.get(annotator)
                   for annotator in all_annotators]
            overall_reliability_data.append(row)

    # Calculate overall Krippendorff's alpha
    if overall_reliability_data:
        try:
            overall_alpha = krippendorff.alpha(
                reliability_data=overall_reliability_data)
            print(f"  Overall: {overall_alpha:.4f}")
        except Exception as e:
            print(f"  Overall: Could not calculate Alpha - {e}")
    else:
        print("  Overall: No valid data")

    # --- Binary Analysis ---
    print("\n--- Binary Analysis (Scores >= 4 are 1, else 0) ---")

    # For each manipulation type, calculate Krippendorff's alpha with binary scores
    for manip_type in manipulative_types:
        # Prepare reliability data for Krippendorff's alpha
        binary_reliability_data = []

        # Get all conversations with this manipulation type
        conversations_with_type = {conv_id: annotations for conv_id, annotations
                                   in annotations_by_conv_type.items()
                                   if manip_type in annotations}

        # Skip if no conversations have this type
        if not conversations_with_type:
            print(f"  {manip_type}: No data")
            continue

        # Get all unique annotators across all conversations
        all_annotators = set()
        for conv_annotations in conversations_with_type.values():
            for manip_annotations in conv_annotations.values():
                for annotator, _ in manip_annotations:
                    all_annotators.add(annotator)

        # Convert to list for consistent ordering
        all_annotators = sorted(list(all_annotators))

        # For each conversation, create a row in the reliability data
        for conv_id, conv_annotations in conversations_with_type.items():
            if manip_type not in conv_annotations:
                continue

            # Skip conversations with only one annotator
            if len(set(annotator for annotator, _ in conv_annotations[manip_type])) < 2:
                continue

            # Create a row for each annotator with binary scores
            annotator_scores = {annotator: 1 if score >= 4 else 0
                                for annotator, score in conv_annotations[manip_type]}

            # Add a row to reliability_data with each annotator's binary score
            row = [annotator_scores.get(annotator)
                   for annotator in all_annotators]
            binary_reliability_data.append(row)

        # Skip if no valid data
        if not binary_reliability_data:
            print(f"  {manip_type}: No valid binary data with multiple annotators")
            continue

        # Calculate Krippendorff's alpha with the custom MASI distance function for binary data
        try:
            # For binary data, we use the custom MASI distance function
            alpha = krippendorff.alpha(
                reliability_data=binary_reliability_data, value_domain=custom_masi_distance)
            print(f"  {manip_type}: {alpha:.4f}")
        except Exception as e:
            print(f"  {manip_type}: Could not calculate Binary Alpha - {e}")

    # Calculate overall Krippendorff's alpha for binary scores
    print("\nOverall Krippendorff's alpha (Binary Scores):")

    # Prepare overall binary reliability data
    overall_binary_reliability_data = []

    # For each conversation and manipulation type, create a row in the reliability data
    for conv_id, conv_annotations in annotations_by_conv_type.items():
        for manip_type, manip_annotations in conv_annotations.items():
            # Skip items with only one annotator
            if len(set(annotator for annotator, _ in manip_annotations)) < 2:
                continue

            # Create a row for each annotator with binary scores
            annotator_scores = {annotator: 1 if score >= 4 else 0
                                for annotator, score in manip_annotations}

            # Add a row to reliability_data with each annotator's binary score
            row = [annotator_scores.get(annotator)
                   for annotator in all_annotators]
            overall_binary_reliability_data.append(row)

    # Calculate overall Krippendorff's alpha for binary scores
    if overall_binary_reliability_data:
        try:
            overall_binary_alpha = krippendorff.alpha(
                reliability_data=overall_binary_reliability_data,
                value_domain=custom_masi_distance
            )
            print(f"  Overall: {overall_binary_alpha:.4f}")
        except Exception as e:
            print(f"  Overall: Could not calculate Overall Binary Alpha - {e}")
    else:
        print("  Overall: No valid binary data")


if __name__ == "__main__":
    # Ensure nltk has the required data
    try:
        nltk.data.find('metrics/masi_distance.py')
    except LookupError:
        print("Downloading required NLTK data...")
        # Disable SSL verification to work around certificate issues
        import ssl
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context
        nltk.download('masi_distance')

    # Get survey responses and conversations
    survey_responses = get_conversations_from_firestore()
    conversations = get_conversations_collection()

    # Perform standard IAA analysis
    perform_iaa_analysis(survey_responses)
    perform_masi_analysis(survey_responses)

    # Perform IAA analysis based on prompted category
    perform_prompted_iaa_analysis(survey_responses, conversations)

    # Perform Krippendorff's alpha analysis with custom MASI distance
    perform_krippendorff_masi_analysis(survey_responses)
