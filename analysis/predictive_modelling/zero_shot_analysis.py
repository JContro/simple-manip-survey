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
print(f"Firestore client initialized: {db is not None}")

# Define the directories containing the prediction files
ZERO_SHOT_DIR = 'data/zero_shot'
FEW_SHOT_DIR = 'data/few_shot'


def load_predictions(filepath):
    """Loads predictions from a JSON file."""
    with open(filepath, 'r') as f:
        predictions_data = json.load(f)
    return predictions_data


def get_actual_labels():
    """Fetches actual labels from Firestore."""
    try:
        conversations_ref = db.collection("survey_responses")
        docs = conversations_ref.stream()

        actual_labels = {}
        for doc in docs:
            data = doc.to_dict()
            conversation_uuid = data.get("conversation_uuid")
            if conversation_uuid:
                # Extract labels where the value is not null and key starts with 'manipulative_'
                # Extract labels and their values where the value is not null and key starts with 'manipulative_'
                labels_with_values = {
                    key: value for key, value in data.items()
                    if key.startswith("manipulative_") and value is not None
                }
                actual_labels[conversation_uuid] = labels_with_values

        return actual_labels

    except Exception as e:
        print(f"Error fetching actual labels from Firestore: {e}")
        return None


def evaluate_predictions(predictions, actual_labels):
    """Evaluates predictions against actual labels and returns metrics."""
    y_true = []
    y_pred = []

    # Assuming predictions is a list of dicts, each with 'uuid' and 'predicted_labels'
    # And actual_labels is a dict mapping uuid to actual labels list

    for pred_item in predictions:
        uuid = pred_item.get('conversation_id')
        # Assuming 'predicted_labels' key
        predicted_labels = pred_item.get('predicted_labels', [])

        if uuid in actual_labels:
            true_labels = actual_labels[uuid]

            # For multi-label classification, we need to flatten or use appropriate metrics
            # Let's assume labels are a list of strings (e.g., tactics)
            # We need to create a binary matrix for metrics calculation

            # Get all unique labels from both true and predicted sets for this conversation
            all_labels = sorted(list(set(true_labels + predicted_labels)))

            # Create binary vectors
            true_vector = [
                1 if label in true_labels else 0 for label in all_labels]
            pred_vector = [
                1 if label in predicted_labels else 0 for label in all_labels]

            y_true.append(true_vector)
            y_pred.append(pred_vector)

        else:
            print(
                f"Warning: Conversation UUID {uuid} not found in actual labels.")

    if not y_true:
        print("No matching conversations found for evaluation.")
        return None

    # Calculate metrics. For multi-label, use appropriate averaging.
    # 'micro' average is suitable for overall performance across all labels.
    # 'samples' average is suitable if each sample (conversation) is a separate prediction.
    # Let's use 'micro' for overall label performance.

    # Flatten the lists of lists for metric calculation
    y_true_flat = [item for sublist in y_true for item in sublist]
    y_pred_flat = [item for sublist in y_pred for item in sublist]

    # Hamming Score (Accuracy) - proportion of correctly predicted labels over total labels
    # This is equivalent to accuracy_score when using flattened binary indicators
    accuracy = accuracy_score(y_true_flat, y_pred_flat)

    # Precision, Recall, F1 Score - using micro average
    precision = precision_score(
        y_true_flat, y_pred_flat, average='micro', zero_division=0)
    recall = recall_score(y_true_flat, y_pred_flat,
                          average='micro', zero_division=0)
    f1 = f1_score(y_true_flat, y_pred_flat, average='micro', zero_division=0)

    return {
        "Accuracy (Hamming Score)": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1 Score": f1
    }


def main():
    """Main function to perform zero-shot analysis."""
    print("Fetching actual labels from Firestore...")
    actual_labels = get_actual_labels()

    if actual_labels is None:
        print("Could not fetch actual labels. Exiting.")
        return

    print(f"Fetched {len(actual_labels)} actual labels.")
    print(f"Type of actual_labels keys: {type(next(iter(actual_labels)))}")
    analysis_dirs = [ZERO_SHOT_DIR, FEW_SHOT_DIR]

    for data_dir in analysis_dirs:
        if not os.path.exists(data_dir):
            print(f"Directory {data_dir} not found. Skipping.")
            continue

        print(f"\nAnalyzing predictions in {data_dir}...")

        for filename in os.listdir(data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(data_dir, filename)
                # Use filename as model name
                model_name = os.path.splitext(filename)[0]

                print(f"\n--- Evaluating {model_name} ---")
                predictions = load_predictions(filepath)

                if not predictions:
                    print("No predictions loaded.")
                    continue

                metrics = evaluate_predictions(predictions, actual_labels)

                if metrics:
                    for metric, value in metrics.items():
                        print(f"{metric}: {value:.4f}")
            break


if __name__ == "__main__":
    main()
