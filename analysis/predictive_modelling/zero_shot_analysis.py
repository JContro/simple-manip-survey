"""Zero-shot analysis script for manipulation detection.

This script gets data from Firestore and calculates metrics for zero-shot manipulation detection.
It processes survey responses and conversations, prepares ground truth data, and evaluates model predictions.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Any
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import glob
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define manipulation types
MANIPULATION_TYPES = [
    'peer pressure', 'reciprocity pressure', 'gaslighting',
    'guilt-tripping', 'emotional blackmail', 'fear enhancement',
    'negging', 'general'
]


def parse_zs_output(classification):
    """
    Parse the zero-shot model output, handling different JSON formats.

    Args:
        classification: The raw classification output from the model

    Returns:
        dict: Parsed JSON data or None if parsing fails
    """
    logger.debug(f"Parsing classification: {classification[:100]}...")

    # Handle None or empty strings
    if not classification or not isinstance(classification, str):
        return None

    classification = classification.strip()

    # Handle markdown code blocks
    if classification.startswith('```json\n'):
        classification = classification[len('```json\n'):]
        if classification.endswith('```'):
            classification = classification[:-3]
    elif classification.startswith('```\n'):
        classification = classification[len('```\n'):]
        if classification.endswith('```'):
            classification = classification[:-3]
    elif classification.startswith('```'):
        classification = classification[len('```'):]
        if classification.endswith('```'):
            classification = classification[:-3]

    # Try to clean up common JSON issues
    try:
        # Replace single quotes with double quotes for JSON compatibility
        if "'" in classification and '"' not in classification:
            classification = classification.replace("'", '"')

        # Try to parse the JSON
        data = json.loads(classification)
        return data
    except json.JSONDecodeError as e:
        logger.debug(f"Error decoding JSON: {e}")
        logger.debug(f"Problematic JSON: {classification}")

        # Try a more lenient approach for malformed JSON
        try:
            # Sometimes there's extra text before or after the JSON
            # Try to find the JSON object by looking for { and }
            start = classification.find('{')
            end = classification.rfind('}') + 1
            if start >= 0 and end > start:
                potential_json = classification[start:end]
                return json.loads(potential_json)
        except json.JSONDecodeError:
            pass

        return None


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculate accuracy, precision, recall, and F1 score for multi-label classification.

    Args:
        y_true: Ground truth binary labels
        y_pred: Predicted binary labels

    Returns:
        dict: Dictionary containing various metrics
    """
    logger.debug(f"Calculating metrics for arrays of shape {y_true.shape}")
    y_true = y_true.astype(bool)
    y_pred = y_pred.astype(bool)

    hamming_accuracy = np.mean(y_true == y_pred)
    subset_accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average='macro',
        zero_division=0
    )

    return {
        'hamming_accuracy': hamming_accuracy,
        'subset_accuracy': subset_accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }


def calculate_statistics(values: List[float]) -> Dict:
    """
    Calculate statistical measures for a list of values.

    Args:
        values: List of numeric values

    Returns:
        dict: Dictionary containing statistical measures
    """
    values = np.array(values)
    mean = np.mean(values)
    std = np.std(values)
    confidence_level = 0.95
    degrees_of_freedom = len(values) - 1
    t_value = stats.t.ppf((1 + confidence_level) / 2, degrees_of_freedom)
    margin_of_error = t_value * (std / np.sqrt(len(values)))

    return {
        'mean': mean,
        'std': std,
        'var': np.var(values),
        'confidence_interval_95': (mean - margin_of_error, mean + margin_of_error)
    }


def evaluate_model(data: pd.DataFrame, model: str) -> Dict:
    """
    Evaluate the model predictions against ground truth.

    Args:
        data: DataFrame containing ground truth and model predictions
        model: Model name identifier used in column names

    Returns:
        dict: Dictionary containing evaluation results
    """
    logger.info(f"Evaluating model: {model}")

    folds = data['fold'].unique()
    results_per_fold = {}
    fold_metrics = {
        'overall': {metric: [] for metric in ['hamming_accuracy', 'subset_accuracy', 'precision', 'recall', 'f1']},
        'per_manipulation': {manip: {'precision': [], 'recall': [], 'f1': []} for manip in MANIPULATION_TYPES}
    }

    for fold in folds:
        fold_data = data[data['fold'] == fold]
        logger.info(f"Processing fold {fold} with {len(fold_data)} samples")

        # Prepare true and predicted values
        y_true = np.column_stack(
            [fold_data[f'{manip}_binary_true'] for manip in MANIPULATION_TYPES])
        y_pred = np.column_stack(
            [fold_data[f'{model}_{manip.lower()}_zs'] for manip in MANIPULATION_TYPES])

        # Calculate metrics
        overall_metrics = calculate_metrics(y_true, y_pred)
        logger.info(f"Fold {fold} overall metrics: {overall_metrics}")

        # Calculate per-manipulation metrics
        manip_metrics = {}
        y_true = y_true.astype(bool)
        y_pred = y_pred.astype(bool)
        for i, manip in enumerate(MANIPULATION_TYPES):
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_true[:, i],
                y_pred[:, i],
                average='binary',
                zero_division=0
            )
            manip_metrics[manip] = {
                'precision': precision, 'recall': recall, 'f1': f1}

        results_per_fold[f'fold_{fold}'] = {
            'overall': overall_metrics,
            'per_manipulation': manip_metrics
        }

        # Store metrics for statistical analysis
        for metric, value in overall_metrics.items():
            fold_metrics['overall'][metric].append(value)
        for manip, metrics in manip_metrics.items():
            for metric, value in metrics.items():
                fold_metrics['per_manipulation'][manip][metric].append(value)

    # Calculate statistical analysis
    statistical_analysis = {
        'overall': {metric: calculate_statistics(values)
                    for metric, values in fold_metrics['overall'].items()},
        'per_manipulation': {manip: {metric: calculate_statistics(values)
                                     for metric, values in metrics.items()}
                             for manip, metrics in fold_metrics['per_manipulation'].items()}
    }

    return {
        'per_fold': results_per_fold,
        'statistical_analysis': statistical_analysis
    }


def initialize_firestore():
    """
    Initialize Firebase Admin SDK if not already initialized.

    Returns:
        firestore.Client: Initialized Firestore client
    """
    if not firebase_admin._apps:
        try:
            # Try to use service account key file
            service_account_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "iac",
                "service-account-key.json"
            )
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': 'simple-manip-survey-250416',
                })
                logger.info("Initialized Firebase with service account key")
            else:
                # Fall back to application default credentials
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
                logger.info(
                    "Initialized Firebase with application default credentials")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise

    return firestore.client()


def get_data_from_firestore():
    """
    Fetches survey responses and conversation data from Firestore.

    Returns:
        tuple: (survey_responses, conversations)
    """
    logger.info("Fetching data from Firestore...")
    db = initialize_firestore()

    # Get survey responses
    survey_responses_ref = db.collection('survey_responses')
    survey_docs = survey_responses_ref.stream()
    survey_responses = [doc.to_dict() for doc in survey_docs]
    logger.info(f"Retrieved {len(survey_responses)} survey responses")

    # Get conversations
    conversations_ref = db.collection('conversations')
    conversation_docs = conversations_ref.stream()
    conversations = [doc.to_dict() for doc in conversation_docs]
    logger.info(f"Retrieved {len(conversations)} conversations")

    return survey_responses, conversations


def prepare_data(survey_responses, conversations, fold_mapping):
    """
    Prepare data for evaluation by combining survey responses and conversations.

    Args:
        survey_responses: List of survey response dictionaries
        conversations: List of conversation dictionaries
        fold_mapping: Dictionary mapping fold indices to conversation UUIDs

    Returns:
        pd.DataFrame: Prepared DataFrame with ground truth labels
    """
    logger.info("Preparing data for evaluation...")

    # Create DataFrames
    survey_df = pd.DataFrame(survey_responses)
    conv_df = pd.DataFrame(conversations)

    # Rename uuid to conversation_uuid in conversations DataFrame for merging
    conv_df = conv_df.rename(columns={'uuid': 'conversation_uuid'})

    # Merge DataFrames on conversation_uuid
    merged_df = pd.merge(
        survey_df,
        conv_df,
        on='conversation_uuid',
        how='inner',
        suffixes=('_survey', '_conv')
    )

    logger.info(f"Created merged DataFrame with {len(merged_df)} rows")

    # Create binary labels for each manipulation type
    for manip in MANIPULATION_TYPES:
        col_name = f"manipulative_{manip.replace(' ', '_')}"
        binary_col = f"{manip}_binary_true"

        # Handle special case for reciprocity pressure
        if manip == 'reciprocity pressure' and f"manipulative_{manip.replace(' ', '_')}" not in merged_df.columns:
            col_name = "manipulative_reciprocity"

        # Handle special case for guilt-tripping
        if manip == 'guilt-tripping' and f"manipulative_{manip.replace(' ', '_')}" not in merged_df.columns:
            col_name = "manipulative_guilt_tripping"

        if col_name in merged_df.columns:
            # Convert scores to binary (0 if score <= 4, 1 if score > 4)
            merged_df[binary_col] = (merged_df[col_name] > 4).astype(int)
        else:
            logger.warning(f"Column {col_name} not found in data")
            merged_df[binary_col] = 0

    # Assign folds based on fold_mapping
    merged_df['fold'] = None
    for fold_idx, uuids in fold_mapping.items():
        fold_num = int(fold_idx.split('_')[1])
        merged_df.loc[merged_df['conversation_uuid'].isin(
            uuids), 'fold'] = fold_num

    # Drop rows without fold assignment
    merged_df = merged_df.dropna(subset=['fold'])
    merged_df['fold'] = merged_df['fold'].astype(int)

    logger.info(
        f"Final DataFrame has {len(merged_df)} rows with fold assignments")

    return merged_df


def load_model_predictions(data_dir, model_name):
    """
    Load model predictions from JSON files.

    Args:
        data_dir: Directory containing model prediction files
        model_name: Name of the model to load predictions for

    Returns:
        dict: Dictionary mapping conversation IDs to model predictions
    """
    logger.info(f"Loading predictions for model: {model_name}")

    # Construct path to the model's prediction file
    file_path = os.path.join(data_dir, "zero_shot", f"{model_name}.json")

    if not os.path.exists(file_path):
        logger.error(f"Prediction file not found: {file_path}")
        return {}

    with open(file_path, 'r') as f:
        predictions = json.load(f)

    # Create a dictionary mapping conversation IDs to predictions
    pred_dict = {}
    for pred in predictions:
        conv_id = pred.get('conversation_id')
        classification = pred.get('classification')

        if conv_id and classification:
            parsed_data = parse_zs_output(classification)
            if parsed_data:
                pred_dict[conv_id] = parsed_data

    logger.info(f"Loaded {len(pred_dict)} predictions for {model_name}")
    return pred_dict


def process_model_predictions(data_df, model_name, predictions):
    """
    Process model predictions and add them to the DataFrame.

    Args:
        data_df: DataFrame containing ground truth data
        model_name: Name of the model
        predictions: Dictionary mapping conversation IDs to model predictions

    Returns:
        pd.DataFrame: DataFrame with added model prediction columns
    """
    logger.info(f"Processing predictions for model: {model_name}")

    # Create a copy of the DataFrame to avoid modifying the original
    df = data_df.copy()

    # Initialize prediction columns
    for manip in MANIPULATION_TYPES:
        df[f'{model_name}_{manip.lower()}_zs'] = 0

    # Fill in predictions
    for idx, row in df.iterrows():
        conv_id = row['conversation_uuid']
        if conv_id in predictions:
            pred = predictions[conv_id]

            # Extract manipulation tactics predictions
            if 'manipulation_tactics' in pred:
                tactics = pred['manipulation_tactics']

                # Handle peer pressure
                if 'Peer Pressure' in tactics:
                    value = tactics['Peer Pressure']
                    df.at[idx, f'{model_name}_peer pressure_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))
                elif 'Peer-Pressure' in tactics:
                    value = tactics['Peer-Pressure']
                    df.at[idx, f'{model_name}_peer pressure_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))

                # Handle reciprocity pressure
                if 'Reciprocity Pressure' in tactics:
                    value = tactics['Reciprocity Pressure']
                    df.at[idx, f'{model_name}_reciprocity pressure_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))
                elif 'Reciprocity-Pressure' in tactics:
                    value = tactics['Reciprocity-Pressure']
                    df.at[idx, f'{model_name}_reciprocity pressure_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))

                # Handle gaslighting
                if 'Gaslighting' in tactics:
                    value = tactics['Gaslighting']
                    df.at[idx, f'{model_name}_gaslighting_zs'] = int(value) if isinstance(
                        value, (bool, int, str)) else int(bool(value))

                # Handle guilt-tripping
                if 'Guilt-Tripping' in tactics:
                    value = tactics['Guilt-Tripping']
                    df.at[idx, f'{model_name}_guilt-tripping_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))

                # Handle emotional blackmail
                if 'Emotional Blackmail' in tactics:
                    value = tactics['Emotional Blackmail']
                    df.at[idx, f'{model_name}_emotional blackmail_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))
                elif 'Emotional-Blackmail' in tactics:
                    value = tactics['Emotional-Blackmail']
                    df.at[idx, f'{model_name}_emotional blackmail_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))

                # Handle fear enhancement
                if 'Fear Enhancement' in tactics:
                    value = tactics['Fear Enhancement']
                    df.at[idx, f'{model_name}_fear enhancement_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))
                elif 'Fear-Enhancement' in tactics:
                    value = tactics['Fear-Enhancement']
                    df.at[idx, f'{model_name}_fear enhancement_zs'] = int(
                        value) if isinstance(value, (bool, int, str)) else int(bool(value))

                # Handle negging
                if 'Negging' in tactics:
                    value = tactics['Negging']
                    df.at[idx, f'{model_name}_negging_zs'] = int(value) if isinstance(
                        value, (bool, int, str)) else int(bool(value))

            # Extract general manipulation prediction
            if 'general' in pred:
                value = pred['general']
                df.at[idx, f'{model_name}_general_zs'] = int(value) if isinstance(
                    value, (bool, int, str)) else int(bool(value))

    logger.info(f"Processed predictions for {model_name}")
    return df


def save_results(results, output_dir, model_name):
    """
    Save evaluation results to a JSON file.

    Args:
        results: Dictionary containing evaluation results
        output_dir: Directory to save results to
        model_name: Name of the model
    """
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{model_name}_evaluation.json")

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Saved evaluation results to {output_file}")


def main():
    """
    Main function to run the zero-shot analysis.
    """
    logger.info("Starting zero-shot analysis")

    # Set paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    output_dir = os.path.join(script_dir, "results")
    fold_mapping_path = os.path.join(data_dir, "fold_mapping.json")

    # Load fold mapping
    with open(fold_mapping_path, 'r') as f:
        fold_mapping = json.load(f)

    # Get data from Firestore
    survey_responses, conversations = get_data_from_firestore()

    # Prepare data
    data_df = prepare_data(survey_responses, conversations, fold_mapping)

    # Get list of model files
    model_files = glob.glob(os.path.join(data_dir, "zero_shot", "*.json"))
    model_names = [os.path.splitext(os.path.basename(f))[0]
                   for f in model_files]

    # Process each model
    for model_name in model_names:
        logger.info(f"Processing model: {model_name}")

        # Load model predictions
        predictions = load_model_predictions(data_dir, model_name)

        # Process predictions
        processed_df = process_model_predictions(
            data_df, model_name, predictions)

        # Evaluate model
        results = evaluate_model(processed_df, model_name)

        # Save results
        save_results(results, output_dir, model_name)

    logger.info("Zero-shot analysis completed")


if __name__ == "__main__":
    main()
