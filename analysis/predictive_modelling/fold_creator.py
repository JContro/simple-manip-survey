"""
Fold Creator Module

This script reads survey_responses and conversations collections from Firestore,
and creates stratified k-fold splits for machine learning experiments.
The splits are saved as a JSON file in the format {'fold_0': ['uuids',...]}
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import StratifiedKFold
import os
import json
import logging
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_firestore():
    """Initialize Firebase Admin SDK if not already initialized."""
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


def get_data_from_firestore(db):
    """
    Fetches survey responses and conversation data from Firestore.

    Returns:
        tuple: (survey_responses, conversations)
    """
    logger.info("Fetching data from Firestore...")

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


def prepare_dataframe(survey_responses, conversations):
    """
    Prepares a DataFrame from survey responses and conversations for k-fold splitting.

    Args:
        survey_responses: List of survey response dictionaries
        conversations: List of conversation dictionaries

    Returns:
        pandas.DataFrame: Combined DataFrame with relevant features
    """
    logger.info("Preparing DataFrame for k-fold splitting...")

    # Create DataFrame from survey responses
    survey_df = pd.DataFrame(survey_responses)

    # Create DataFrame from conversations
    conv_df = pd.DataFrame(conversations)

    # Check if we have data
    if survey_df.empty:
        logger.error("No survey responses found")
        raise ValueError("No survey responses found")

    if conv_df.empty:
        logger.error("No conversations found")
        raise ValueError("No conversations found")

    # Ensure we have the conversation_uuid column in both DataFrames
    if 'conversation_uuid' not in survey_df.columns:
        logger.error("conversation_uuid column missing from survey responses")
        raise ValueError(
            "conversation_uuid column missing from survey responses")

    if 'uuid' not in conv_df.columns:
        logger.error("uuid column missing from conversations")
        raise ValueError("uuid column missing from conversations")

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

    return merged_df


def plot_kfold_distributions(fold_splits, stratify_columns, target_columns=None, output_dir=None):
    """
    Plot and save the distribution of classes across k folds.

    Parameters:
    -----------
    fold_splits : dict
        Dictionary containing k-fold splits
    stratify_columns : list
        List of columns used for stratification
    target_columns : list, optional
        Additional target columns to plot distributions for
    output_dir : str, optional
        Directory to save plots to. If None, plots will be displayed instead
    """
    all_columns = stratify_columns.copy()
    if target_columns:
        all_columns.extend(
            [col for col in target_columns if col not in stratify_columns])

    n_folds = len(fold_splits)
    n_targets = len(all_columns)

    # Distribution plots
    fig, axes = plt.subplots(n_targets, 2, figsize=(15, 6 * n_targets))
    if n_targets == 1:
        axes = axes.reshape(1, -1)

    for idx, col in enumerate(all_columns):
        # Calculate distributions for each fold
        fold_distributions = []
        for fold_idx, split in fold_splits.items():
            y_train, y_test = split['y_train'], split['y_test']
            train_dist = y_train[col].value_counts(normalize=True)
            test_dist = y_test[col].value_counts(normalize=True)
            fold_distributions.append((train_dist, test_dist))

        # Calculate average distribution across folds
        avg_train_dist = pd.concat(
            [d[0] for d in fold_distributions]).groupby(level=0).mean()
        avg_test_dist = pd.concat(
            [d[1] for d in fold_distributions]).groupby(level=0).mean()

        # Bar plot
        x = np.arange(len(avg_train_dist))
        width = 0.35
        axes[idx, 0].bar(x - width/2, avg_train_dist, width,
                         label='Train (avg)', alpha=0.8)
        axes[idx, 0].bar(x + width/2, avg_test_dist, width,
                         label='Test (avg)', alpha=0.5)
        axes[idx, 0].set_title(
            f'{col} Average Distribution Across {n_folds} Folds')
        axes[idx, 0].set_xticks(x)
        axes[idx, 0].set_xticklabels(avg_train_dist.index)
        axes[idx, 0].legend()

        # Add percentage labels on bars
        for i, v in enumerate(avg_train_dist):
            axes[idx, 0].text(
                i - width/2, v, f'{v:.1%}', ha='center', va='bottom')
        for i, v in enumerate(avg_test_dist):
            axes[idx, 0].text(
                i + width/2, v, f'{v:.1%}', ha='center', va='bottom')

        # Box plot showing distribution variance across folds
        fold_data = []
        for fold_idx in range(n_folds):
            for class_label in avg_train_dist.index:
                fold_data.extend([
                    {
                        'Fold': fold_idx,
                        'Class': class_label,
                        'Proportion': fold_distributions[fold_idx][0].get(class_label, 0),
                        'Set': 'Train'
                    },
                    {
                        'Fold': fold_idx,
                        'Class': class_label,
                        'Proportion': fold_distributions[fold_idx][1].get(class_label, 0),
                        'Set': 'Test'
                    }
                ])

        fold_df = pd.DataFrame(fold_data)
        sns.boxplot(data=fold_df, x='Class', y='Proportion',
                    hue='Set', ax=axes[idx, 1])
        axes[idx, 1].set_title(f'{col} Distribution Variance Across Folds')
        axes[idx, 1].tick_params(axis='x', rotation=45)

    plt.tight_layout()
    if output_dir:
        try:
            plt.savefig(os.path.join(output_dir, 'distribution_plots.png'))
        except Exception as e:
            logging.error(f"Failed to save distribution plots: {e}")
        plt.close()
    else:
        plt.show()

    # Box plots for distribution variance
    plt.figure(figsize=(15, 5 * n_targets))
    for idx, col in enumerate(all_columns):
        plt.subplot(n_targets, 1, idx + 1)

        fold_data = []
        for fold_idx, split in fold_splits.items():
            train_dist = split['y_train'][col].value_counts(normalize=True)
            test_dist = split['y_test'][col].value_counts(normalize=True)

            for class_label in train_dist.index:
                fold_data.extend([
                    {
                        'Fold': fold_idx,
                        'Class': class_label,
                        'Proportion': train_dist[class_label],
                        'Set': 'Train'
                    },
                    {
                        'Fold': fold_idx,
                        'Class': class_label,
                        'Proportion': test_dist.get(class_label, 0),
                        'Set': 'Test'
                    }
                ])

        fold_df = pd.DataFrame(fold_data)
        sns.boxplot(data=fold_df, x='Class', y='Proportion', hue='Set')
        plt.title(f'{col} Distribution Variance Across Folds')
        plt.xticks(rotation=45)

    plt.tight_layout()
    if output_dir:
        try:
            plt.savefig(os.path.join(output_dir, 'distribution_variance.png'))
        except Exception as e:
            logging.error(f"Failed to save distribution variance plots: {e}")
        plt.close()
    else:
        plt.show()

    # Save distribution statistics if output directory is provided
    if output_dir:
        stats = []
        for fold_idx, split in fold_splits.items():
            for col in all_columns:
                train_dist = split['y_train'][col].value_counts(normalize=True)
                test_dist = split['y_test'][col].value_counts(normalize=True)
                stats.append({
                    'fold': fold_idx,
                    'column': col,
                    'set': 'train',
                    'distribution': train_dist.to_dict()
                })
                stats.append({
                    'fold': fold_idx,
                    'column': col,
                    'set': 'test',
                    'distribution': test_dist.to_dict()
                })

        try:
            with open(os.path.join(output_dir, 'distribution_stats.json'), 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save distribution statistics: {e}")


def perform_kfold_stratified_split(df, stratify_columns, target_columns=None, n_splits=5,
                                   random_state=42, plot=True, plot_output_dir=None):
    """
    Performs k-fold stratified split on a pandas DataFrame, stratifying by specified columns
    while preserving additional target columns.

    Parameters:
    -----------
    df : pandas.DataFrame
        The input DataFrame
    stratify_columns : list
        Columns to use for stratification
    target_columns : list, optional
        Additional target columns to preserve (not used for stratification)
    n_splits : int, default=5
        Number of folds for k-fold cross-validation
    random_state : int, default=42
        Random seed for reproducibility
    plot : bool, default=True
        Whether to plot the distributions of the splits
    plot_output_dir : str, optional
        Directory to save plots to. If None, plots will be displayed

    Returns:
    --------
    fold_splits : dict
        Dictionary containing the splits for each fold:
        {fold_index: {'X_train': X_train, 'X_test': X_test, 
                      'y_train': y_train, 'y_test': y_test}}
    """
    # Verify all columns exist in the DataFrame
    all_target_cols = stratify_columns.copy()
    if target_columns:
        all_target_cols.extend(
            [col for col in target_columns if col not in stratify_columns])

    missing_cols = [col for col in all_target_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Columns not found in DataFrame: {missing_cols}")

    # Check for empty DataFrame
    if len(df) == 0:
        raise ValueError("Input DataFrame is empty")

    # Separate features and targets
    X = df.drop(all_target_cols, axis=1)
    y = df[all_target_cols]

    # Create a combined category for stratification
    combined_strat = y[stratify_columns].apply(
        lambda row: '_'.join(row.astype(str)), axis=1)

    # Initialize KFold cross-validator
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True,
                          random_state=random_state)

    # Store splits
    fold_splits = {}

    try:
        # Perform k-fold split
        for fold_idx, (train_idx, test_idx) in enumerate(skf.split(X, combined_strat)):

            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            fold_splits[fold_idx] = {
                'X_train': X_train,
                'X_test': X_test,
                'y_train': y_train,
                'y_test': y_test
            }

            # Print distribution for current fold
            logger.info(f"\nFold {fold_idx + 1}/{n_splits}")
            for col in stratify_columns:
                logger.info(f"\nColumn: {col}")
                logger.info("Training set distribution:")
                logger.info(y_train[col].value_counts(normalize=True))
                logger.info("\nTest set distribution:")
                logger.info(y_test[col].value_counts(normalize=True))

    except ValueError as e:
        if "The least populated class in y has only 1 member" in str(e):
            logger.warning(
                "\nWarning: Some classes have too few samples for stratification.")
            raise e
        else:
            raise e

    # Plot distributions if requested
    if plot:
        plot_kfold_distributions(
            fold_splits,
            stratify_columns,
            target_columns,
            output_dir=plot_output_dir
        )

    return fold_splits


def create_fold_uuid_mapping(fold_splits):
    """
    Creates a mapping of fold indices to conversation UUIDs.

    Args:
        fold_splits: Dictionary containing k-fold splits

    Returns:
        dict: Dictionary mapping fold indices to lists of conversation UUIDs
    """
    fold_uuid_mapping = {}

    for fold_idx, split in fold_splits.items():
        # Get test set UUIDs for this fold
        if 'conversation_uuid' in split['X_test'].columns:
            test_uuids = split['X_test']['conversation_uuid'].tolist()
        else:
            # If conversation_uuid is in y_test
            test_uuids = split['y_test']['conversation_uuid'].tolist()

        fold_uuid_mapping[f'fold_{fold_idx}'] = test_uuids

    return fold_uuid_mapping


def save_fold_mapping(fold_uuid_mapping, output_path):
    """
    Saves the fold-to-UUID mapping to a JSON file.

    Args:
        fold_uuid_mapping: Dictionary mapping fold indices to lists of conversation UUIDs
        output_path: Path to save the JSON file
    """
    try:
        with open(output_path, 'w') as f:
            json.dump(fold_uuid_mapping, f, indent=2)
        logger.info(f"Saved fold mapping to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save fold mapping: {e}")
        raise


def main():
    """Main function to create and save k-fold splits."""
    parser = argparse.ArgumentParser(
        description='Create stratified k-fold splits for survey data')
    parser.add_argument('--n-splits', type=int,
                        default=5, help='Number of folds')
    parser.add_argument('--random-state', type=int,
                        default=42, help='Random seed')
    parser.add_argument('--output-dir', type=str,
                        default='./data', help='Output directory')
    parser.add_argument('--stratify-columns', type=str, nargs='+',
                        default=['model', 'manipulative_general'],
                        help='Columns to stratify on')
    parser.add_argument('--target-columns', type=str, nargs='+',
                        default=['manipulative_emotional_blackmail', 'manipulative_fear_enhancement',
                                 'manipulative_gaslighting', 'manipulative_guilt_tripping',
                                 'manipulative_negging', 'manipulative_peer_pressure',
                                 'manipulative_reciprocity'],
                        help='Additional target columns to preserve')
    parser.add_argument('--no-plot', action='store_true',
                        help='Disable plotting')

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Firestore
    db = initialize_firestore()

    # Get data from Firestore
    survey_responses, conversations = get_data_from_firestore(db)

    # Prepare DataFrame
    df = prepare_dataframe(survey_responses, conversations)

    # Log available columns for debugging
    logger.info(f"Available columns in DataFrame: {df.columns.tolist()}")

    # Check if model_name exists or if there's a similar column
    model_columns = [col for col in df.columns if 'model' in col.lower()]
    if model_columns:
        logger.info(f"Found model-related columns: {model_columns}")

    # Perform k-fold split
    fold_splits = perform_kfold_stratified_split(
        df,
        stratify_columns=args.stratify_columns,
        target_columns=args.target_columns,
        n_splits=args.n_splits,
        random_state=args.random_state,
        plot=not args.no_plot,
        plot_output_dir=args.output_dir if not args.no_plot else None
    )

    # Create fold-to-UUID mapping
    fold_uuid_mapping = create_fold_uuid_mapping(fold_splits)

    # Save mapping to JSON file
    output_path = output_dir / 'fold_mapping.json'
    save_fold_mapping(fold_uuid_mapping, output_path)

    logger.info(f"Successfully created {args.n_splits}-fold splits")
    logger.info(f"Fold mapping saved to {output_path}")


if __name__ == "__main__":
    main()
