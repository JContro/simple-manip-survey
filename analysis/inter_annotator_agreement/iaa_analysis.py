"""
IAA Analysis - Krippendorff's Alpha Calculator for Binary Conversations

This script calculates Krippendorff's alpha for binary annotations in conversations.
It loads conversation data from Firestore and performs inter-annotator agreement analysis.
"""

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


def extract_binary_annotations(survey_responses, field_name):
    """
    Extract binary annotations from survey responses based on a specific field.

    Args:
        survey_responses: List of survey response dictionaries
        field_name: Field name to extract binary values from

    Returns:
        Dictionary mapping conversation IDs to lists of binary annotations
    """
    binary_annotations = []

    for response in survey_responses:
        for key in response.keys():
            if 'manipulative' in key:
                if response[key] is None:
                    continue
                value = int(response[key])
                binary_value = 1 if value >= 4 else 0
                binary_annotations.append({response['username'],
                                           f"{response['conversation_uuid']}-{key}",
                                           binary_value})

    return binary_annotations


def overall_alpha(binary_annotations):
    """
    Analyze binary annotations and calculate Krippendorff's alpha.

    Args:
        binary_annotations: Dictionary mapping conversation IDs to lists of binary annotations

    Returns:
        Dictionary with analysis results
    """
    # TODO: Get the overall krippendorff alpha


def print_results(results, field_name):
    """
    Print analysis results.

    Args:
        results: Dictionary with analysis results
        field_name: Field name that was analyzed
    """
    print(f"\n=== Krippendorff's Alpha Analysis for {field_name} ===")
    print(f"Total conversations: {results['total_conversations']}")
    print(
        f"Conversations with multiple annotations: {results['conversations_with_multiple_annotations']}")

    if results['alpha_values']:
        print("\nAlpha values per conversation:")
        for conv_id, alpha in results['alpha_values']:
            print(f"  {conv_id}: {alpha:.4f}")

        # Calculate average alpha
        avg_alpha = np.mean([alpha for _, alpha in results['alpha_values']])
        print(f"\nAverage alpha: {avg_alpha:.4f}")

    if results['overall_alpha'] is not None:
        print(
            f"\nOverall Krippendorff's alpha: {results['overall_alpha']:.4f}")

        # Interpret the result
        alpha = results['overall_alpha']
        if alpha == 1.0:
            print("Perfect agreement (alpha = 1.0)")
        elif alpha >= 0.8:
            print("Good agreement (alpha >= 0.8)")
        elif alpha >= 0.67:
            print("Tentative agreement (0.67 <= alpha < 0.8)")
        elif alpha >= 0:
            print("Poor agreement (0 <= alpha < 0.67)")
        else:
            print("Agreement worse than chance (alpha < 0)")


def analyze_all_binary_fields(survey_responses):
    """
    Analyze all relevant binary fields in the survey responses.

    Args:
        survey_responses: List of survey response dictionaries
    """
    # Fields to analyze
    binary_fields = [
        "manipulative_emotional_blackmail",
        "manipulative_fear_enhancement",
        "manipulative_gaslighting",
        "manipulative_general",
        "manipulative_guilt_tripping",
        "manipulative_negging",
        "manipulative_peer_pressure",
        "manipulative_reciprocity"
    ]

    for field in binary_fields:
        binary_annotations = extract_binary_annotations(
            survey_responses, field)
        import pdb
        pdb.set_trace()
        results = analyze_binary_annotations(binary_annotations)
        print_results(results, field)


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
    analyze_all_binary_fields(survey_responses)


if __name__ == "__main__":
    main()
