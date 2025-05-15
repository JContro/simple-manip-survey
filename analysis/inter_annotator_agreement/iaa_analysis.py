from collections import defaultdict
import numpy as np
from firebase_admin import firestore
from firebase_admin import credentials
import firebase_admin
import nltk
from nltk.metrics import agreement
from irrCAC.table import CAC
import pandas as pd
"""
IAA Analysis - Krippendorff's Alpha Calculator for Binary Conversations

This script calculates Krippendorff's alpha for binary annotations in conversations.
It loads conversation data from Firestore and performs inter-annotator agreement analysis.
"""


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
    print(f"Loaded {len(conversations)} survey responses from Firestore")
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
    print(f"Loaded {len(conversations)} conversations from Firestore")
    return conversations


def extract_binary_annotations(survey_responses):
    """
    Extract binary annotations from survey responses for all manipulative fields.

    Args:
        survey_responses: List of survey response dictionaries

    Returns:
        List of tuples (coder, item, value) where:
        - coder is the username of the annotator
        - item is the conversation UUID and field name
        - value is the binary annotation (0 or 1)
    """
    binary_annotations = []

    for response in survey_responses:
        for key in response.keys():
            if 'manipulative' in key:
                if response[key] is None:
                    continue
                value = int(response[key])
                binary_value = 1 if value >= 4 else 0
                binary_annotations.append((response['username'],
                                           f"{response['conversation_uuid']}-{key}",
                                           binary_value))

    return binary_annotations


def calculate_iaa(binary_annotations):
    """
    Calculate Krippendorff's alpha and related statistics for overall analysis.

    Args:
        binary_annotations: List of tuples (coder, item, value)

    Returns:
        Dictionary with analysis results including overall alpha
    """
    results = {
        'total_conversations': 0,
        'conversations_with_multiple_annotations': 0,
        'overall_alpha': None
    }

    if not binary_annotations:
        return results

    # Calculate overall Krippendorff's alpha
    results['overall_alpha'] = calculate_krippendorff_alpha(binary_annotations)

    # Calculate Krippendorff's alpha per conversation
    annotations_by_conversation = defaultdict(list)
    for coder, item, value in binary_annotations:
        # Extract conversation UUID from the item string
        conv_uuid = item.split('-')[0]
        annotations_by_conversation[conv_uuid].append((coder, item, value))

    results['total_conversations'] = len(annotations_by_conversation)

    for conv_uuid, annotations in annotations_by_conversation.items():
        # Only calculate alpha for conversations with multiple annotations
        coders_for_conversation = set([coder for coder, _, _ in annotations])
        if len(coders_for_conversation) > 1:
            results['conversations_with_multiple_annotations'] += 1

    return results


def calculate_overall_alpha(survey_responses):
    """
    Calculate overall Krippendorff's alpha for all survey responses.

    Args:
        survey_responses: List of survey response dictionaries

    Returns:
        Dictionary with analysis results
    """
    all_binary_annotations = extract_binary_annotations(survey_responses)
    results = calculate_iaa(all_binary_annotations)
    print(f"Total Overall Krippendorff's Alpha: {results['overall_alpha']}")
    return results


def get_field_mapping():
    """
    Returns the mapping between survey field names and prompted manipulation tactics.

    Returns:
        Dictionary mapping field names to prompted tactic names
    """
    return {
        "manipulative_emotional_blackmail": "Emotional Blackmail",
        "manipulative_fear_enhancement": "Fear Enhancement",
        "manipulative_gaslighting": "Gaslighting",
        "manipulative_general": None,  # No direct match in the second list
        "manipulative_guilt_tripping": "Guilt-Tripping",
        "manipulative_negging": "Negging",
        "manipulative_peer_pressure": "Peer Pressure",
        "manipulative_reciprocity": "Reciprocity Pressure"
    }


def filter_records_by_field(binary_responses, field, prompted_as, conversations):
    """
    Filter binary responses based on field name and prompted value.

    Args:
        binary_responses: List of tuples (coder, item, value)
        field: Field name to filter by
        prompted_as: Prompted value to filter by
        conversations: Dictionary mapping conversation UUIDs to conversation data

    Returns:
        List of filtered records
    """
    filtered_records = []

    if field == "manipulative_general":
        # For "general", include all UUIDs
        filtered_records = [r for r in binary_responses if field in r[1]]
    else:
        # For specific fields, filter by the prompted_as value
        for uuid, conv_data in conversations.items():
            if conv_data['prompted_as'] == prompted_as:
                records = [
                    r for r in binary_responses if uuid in r[1] and field in r[1]]
                filtered_records.extend(records)

    return filtered_records


def calculate_krippendorff_alpha(filtered_records):
    """
    Calculate Krippendorff's alpha for a set of filtered records.

    Args:
        filtered_records: List of tuples (coder, item, value)

    Returns:
        Krippendorff's alpha value or None if calculation is not possible
    """
    if not filtered_records:
        return None

    task = agreement.AnnotationTask(data=filtered_records)
    return task.alpha()


def calculate_prompted_field_alpha(survey_responses, conversations):
    """
    Calculate Krippendorff's alpha for each field based on prompted values.

    Args:
        survey_responses: List of survey response dictionaries
        conversations: Dictionary mapping conversation UUIDs to conversation data

    Returns:
        Dictionary mapping field names to Krippendorff's alpha values
    """
    mapping = get_field_mapping()
    binary_responses = extract_binary_annotations(survey_responses)
    results_by_field = {}

    for field, prompted_as in mapping.items():
        filtered_records = filter_records_by_field(
            binary_responses, field, prompted_as, conversations
        )

        # Calculate Krippendorff's alpha for the filtered records
        results_by_field[field] = calculate_krippendorff_alpha(
            filtered_records)

    print("Krippendorff's Alpha by Field:")
    for field, alpha in results_by_field.items():
        print(f"{field}: {alpha}")

    return results_by_field


def calculate_gwet_ac1(filtered_records):
    """
    Calculate Gwet's AC1 coefficient for a set of filtered records.

    Args:
        filtered_records: List of tuples (coder, item, value)

    Returns:
        Gwet's AC1 coefficient value or None if calculation is not possible
    """
    if not filtered_records or len(filtered_records) <= 1:
        return None

    # Convert filtered records to a format suitable for irrCAC
    # Group by item and create a contingency table
    annotations_by_item = {}
    for coder, item, value in filtered_records:
        if item not in annotations_by_item:
            annotations_by_item[item] = {}
        annotations_by_item[item][coder] = value

    # Create a contingency table
    # For binary data (0 and 1), we need a 2x2 table
    contingency_table = pd.DataFrame(
        0, index=['0', '1'], columns=['0', '1'])

    # Count occurrences of each rating combination
    for item_annotations in annotations_by_item.values():
        # Skip items with only one annotation
        if len(item_annotations) <= 1:
            continue

        # Count ratings for this item
        ratings = list(item_annotations.values())
        for i in range(len(ratings)):
            for j in range(i+1, len(ratings)):
                # Convert to string keys for the DataFrame
                rating_i = str(ratings[i])
                rating_j = str(ratings[j])
                contingency_table.loc[rating_i, rating_j] += 1
                # Also increment the symmetric cell
                contingency_table.loc[rating_j, rating_i] += 1

    # Calculate Gwet's AC1 using irrCAC
    if contingency_table.sum().sum() > 0:  # Ensure we have data
        cac = CAC(contingency_table)
        gwet_result = cac.gwet()
        return gwet_result['est']['coefficient_value']
    else:
        return None


def calculate_prompted_field_gwet_ac1(survey_responses, conversations):
    """
    Calculate Gwet's AC1 coefficient for each field based on prompted values.

    Args:
        survey_responses: List of survey response dictionaries
        conversations: Dictionary mapping conversation UUIDs to conversation data

    Returns:
        Dictionary mapping field names to Gwet's AC1 coefficients
    """
    mapping = get_field_mapping()
    binary_responses = extract_binary_annotations(survey_responses)
    results_by_field = {}

    for field, prompted_as in mapping.items():
        filtered_records = filter_records_by_field(
            binary_responses, field, prompted_as, conversations
        )

        # Calculate Gwet's AC1 for the filtered records
        results_by_field[field] = calculate_gwet_ac1(filtered_records)

    print("Gwet's AC1 by Field:")
    for field, ac1 in results_by_field.items():
        print(f"{field}: {ac1}")

    return results_by_field


def main():
    """
    Main function to run the analysis.
    """
    # Load data from Firestore
    survey_responses = get_conversations_from_firestore()
    conversations = get_conversations_collection()

    if not survey_responses:
        print("No survey responses loaded. Exiting.")
        return

    # Analyze binary annotations from survey responses
    results_overall_alpha = calculate_overall_alpha(survey_responses)
    print(results_overall_alpha)

    # Calculate Krippendorff's alpha by field
    print("\n=== Calculating Krippendorff's Alpha by Field ===")
    calculate_prompted_field_alpha(survey_responses, conversations)

    # Calculate Gwet's AC1 by field
    print("\n=== Calculating Gwet's AC1 by Field ===")
    calculate_prompted_field_gwet_ac1(survey_responses, conversations)


if __name__ == "__main__":
    main()
