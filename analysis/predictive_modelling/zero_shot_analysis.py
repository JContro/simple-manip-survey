from firebase_admin import firestore
from firebase_admin import credentials
import firebase_admin
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os
import json

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    # Path to the service account key relative to the workspace root
    cred_path = "../../iac/service-account-key.json"
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'projectId': 'simple-manip-survey-250416',
    })

db = firestore.client()

# Define the directories containing the prediction files
ZERO_SHOT_DIR = 'data/zero_shot'
FEW_SHOT_DIR = 'data/few_shot'

# Define the ordered list of manipulation tactics
# This order will be used consistently for both predicted labels and actual labels
MANIPULATION_TACTICS = [
    "Guilt-Tripping",
    "Peer Pressure",
    "Reciprocity Pressure",
    "Gaslighting",
    "Emotional Blackmail",
    "Fear Enhancement",
    "Negging"
]


def load_predictions(filepath):
    """
    Loads predictions from a JSON file and processes them into binary format.

    Returns:
        dict: {conversation_id: [binary_values_for_each_tactic]}
    """
    with open(filepath, 'r') as f:
        predictions_data = json.load(f)

    processed_predictions = {}
    for item in predictions_data:
        conversation_id = item.get("conversation_id")
        classification_str = item.get("classification", "{}")

        # Handle various formats (some have markdown code blocks, etc.)
        classification_str = classification_str.strip()
        if classification_str.startswith("```"):
            classification_str = classification_str.strip("```").strip()

        try:
            # Parse the classification JSON string
            classification = json.loads(classification_str)
            tactics = classification.get("manipulation_tactics", {})

            # Create binary list in the defined order
            binary_values = [1 if tactics.get(
                tactic, False) else 0 for tactic in MANIPULATION_TACTICS]
            processed_predictions[conversation_id] = binary_values
        except json.JSONDecodeError:
            # Skip entries with invalid JSON
            print(f"There was an error in: {classification_str}")
            continue

    return processed_predictions


def get_actual_labels():
    """
    Fetches actual labels from Firestore and converts them to binary format.

    Returns:
        dict: {conversation_uuid: [binary_values_for_each_tactic]}
    """
    try:
        conversations_ref = db.collection("survey_responses")
        docs = conversations_ref.stream()

        actual_labels = {}
        for doc in docs:
            data = doc.to_dict()
            conversation_uuid = data.get("conversation_uuid")
            if conversation_uuid:
                # Map from manipulation tactic to corresponding field name in Firestore
                tactic_to_field = {
                    "Guilt-Tripping": "manipulative_guilt",
                    "Peer Pressure": "manipulative_peer",
                    "Reciprocity Pressure": "manipulative_reciprocity",
                    "Gaslighting": "manipulative_gaslighting",
                    "Emotional Blackmail": "manipulative_emotional",
                    "Fear Enhancement": "manipulative_fear",
                    "Negging": "manipulative_negging"
                }

                # Create binary list in the defined order
                binary_labels = []
                for tactic in MANIPULATION_TACTICS:
                    field_name = tactic_to_field.get(tactic)
                    if field_name and field_name in data and data[field_name] is not None:
                        binary_labels.append(1 if data[field_name] > 4 else 0)
                    else:
                        binary_labels.append(0)  # Default if data not present

                actual_labels[conversation_uuid] = binary_labels

        return actual_labels

    except Exception as e:
        return None


def evaluate_predictions(predictions, actual_labels):
    """
    Evaluates predictions against actual labels using various metrics.

    Args:
        predictions: Dict of {conversation_id: [binary_values]}
        actual_labels: Dict of {conversation_uuid: [binary_values]}

    Returns:
        dict: Dictionary with accuracy, precision, recall, and F1 scores
    """
    # Find common conversation IDs between predictions and actual labels
    common_ids = set(predictions.keys()) & set(actual_labels.keys())

    if not common_ids:
        return None

    # Prepare lists for evaluation
    y_true = []
    y_pred = []

    for conv_id in common_ids:
        y_true.extend(actual_labels[conv_id])
        y_pred.extend(predictions[conv_id])

    # Calculate metrics
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0)
    }

    return metrics


def main():
    """Main function to perform zero-shot analysis."""
    actual_labels = get_actual_labels()

    if actual_labels is None:
        return

    analysis_dirs = [ZERO_SHOT_DIR, FEW_SHOT_DIR]

    for data_dir in analysis_dirs:
        if not os.path.exists(data_dir):
            continue

        for filename in os.listdir(data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(data_dir, filename)
                # Use filename as model name
                model_name = os.path.splitext(filename)[0]

                predictions = load_predictions(filepath)

                if not predictions:
                    continue

                metrics = evaluate_predictions(predictions, actual_labels)

                if metrics:
                    print(f"Model: {model_name}")
                    for metric, value in metrics.items():
                        print(f"{metric}: {value:.4f}")
                    print()


if __name__ == "__main__":
    main()
