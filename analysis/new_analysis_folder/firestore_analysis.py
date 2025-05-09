from data_loader import load_users_data, load_survey_responses_data, load_conversations_data
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json
import os
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from typing import Dict, List, Union, Tuple
from sklearn.metrics import accuracy_score, recall_score, confusion_matrix
import scipy.stats as stats

db = firestore.client()


def setup_logging() -> logging.Logger:
    """Configure and return logger with consistent formatting."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data_processing.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def calculate_statistics(row: pd.Series, manipulation_cols: List[str]) -> Tuple[float, float]:
    """Calculate variance and mean score for a row of manipulation scores."""
    scores = []
    for col in manipulation_cols:
        if isinstance(row[col], list) and row[col]:
            scores.extend(row[col])

    if not scores:
        return np.nan, np.nan

    return np.var(scores), np.mean(scores)


def analyze_correlations(series1, series2, series1_name="Series 1", series2_name="Series 2"):
    """
    Calculate different types of correlations between two pandas Series.

    Parameters:
    series1 (pd.Series): First series of data
    series2 (pd.Series): Second series of data
    series1_name (str): Name of first series for output
    series2_name (str): Name of second series for output

    Returns:
    dict: Dictionary containing different correlation metrics
    """
    # Remove any rows where either series has NaN values
    clean_data = pd.DataFrame({
        series1_name: series1,
        series2_name: series2
    }).dropna()

    series1_clean = clean_data[series1_name]
    series2_clean = clean_data[series2_name]

    # Calculate different correlation coefficients
    correlations = {
        'pearson': {
            'coefficient': series1_clean.corr(series2_clean, method='pearson'),
            'pvalue': stats.pearsonr(series1_clean, series2_clean)[1]
        },
        'spearman': {
            'coefficient': series1_clean.corr(series2_clean, method='spearman'),
            'pvalue': stats.spearmanr(series1_clean, series2_clean)[1]
        },
        'kendall': {
            'coefficient': series1_clean.corr(series1_clean, series2_clean, method='kendall'),
            'pvalue': stats.kendalltau(series1_clean, series2_clean)[1]
        }
    }

    # Calculate additional relationship metrics
    correlations['additional_metrics'] = {
        'covariance': series1_clean.cov(series2_clean),
        'r_squared': correlations['pearson']['coefficient'] ** 2,
        'sample_size': len(clean_data),
        'removed_rows': len(series1) - len(clean_data)
    }

    return correlations


def analyze_all_correlations(analytics_df: pd.DataFrame, mean_manipulation_columns: List[str], logger: logging.Logger) -> None:
    """
    Analyze correlations between all combinations of manipulation columns and save results to PDF.
    """
    from itertools import combinations
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    # Create PDF
    with PdfPages('manipulation_correlations.pdf') as pdf:
        # Add title page
        plt.figure(figsize=(11, 8.5))
        plt.axis('off')
        plt.text(0.5, 0.5, 'Manipulation Correlation Analysis Report',
                 horizontalalignment='center',
                 verticalalignment='center',
                 fontsize=24)
        plt.text(0.5, 0.4, f'Generated on {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}',
                 horizontalalignment='center',
                 verticalalignment='center',
                 fontsize=12)
        pdf.savefig()
        plt.close()

        # Initialize correlation and p-value matrices with zeros
        correlation_matrix = pd.DataFrame(0.0,
                                          index=mean_manipulation_columns,
                                          columns=mean_manipulation_columns,
                                          dtype=float)
        pvalue_matrix = pd.DataFrame(1.0,  # Initialize with 1.0 for non-significant
                                     index=mean_manipulation_columns,
                                     columns=mean_manipulation_columns,
                                     dtype=float)

        # Store detailed correlation results
        detailed_results = []

        # Analyze all combinations
        for (col1, col2) in combinations(mean_manipulation_columns, 2):
            # Get readable names
            name1 = col1.replace('_mean', '').title()
            name2 = col2.replace('_mean', '').title()

            # Calculate correlations
            correlations = analyze_correlations(
                analytics_df[col1],
                analytics_df[col2],
                series1_name=name1,
                series2_name=name2
            )

            # Store in matrices - ensure float type
            coef = float(correlations['pearson']['coefficient'])
            pval = float(correlations['pearson']['pvalue'])

            correlation_matrix.loc[col1, col2] = coef
            correlation_matrix.loc[col2, col1] = coef
            pvalue_matrix.loc[col1, col2] = pval
            pvalue_matrix.loc[col2, col1] = pval

            # Create scatter plot
            plt.figure(figsize=(10, 6))
            plt.scatter(analytics_df[col1], analytics_df[col2], alpha=0.5)
            plt.xlabel(name1)
            plt.ylabel(name2)

            # Add correlation information
            info_text = (
                f"Pearson: {coef:.3f} (p={pval:.3e})\n"
                f"Spearman: {correlations['spearman']['coefficient']:.3f} (p={correlations['spearman']['pvalue']:.3e})\n"
                f"Kendall: {correlations['kendall']['coefficient']:.3f} (p={correlations['kendall']['pvalue']:.3e})\n"
                f"R²: {correlations['additional_metrics']['r_squared']:.3f}\n"
                f"Sample size: {correlations['additional_metrics']['sample_size']}"
            )
            plt.title(f"Correlation between {name1} and {name2}")
            plt.text(0.05, 0.95, info_text,
                     transform=plt.gca().transAxes,
                     verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            # Add to PDF
            pdf.savefig()
            plt.close()

            # Store detailed results
            detailed_results.append({
                'pair': f"{name1} vs {name2}",
                'correlations': correlations
            })

            logger.info(f"Processed correlation between {name1} and {name2}")

        # Fill diagonal of correlation matrix
        np.fill_diagonal(correlation_matrix.values, 1.0)
        np.fill_diagonal(pvalue_matrix.values, 0.0)

        # Ensure matrices are float type
        correlation_matrix = correlation_matrix.astype(float)
        pvalue_matrix = pvalue_matrix.astype(float)

        def format_correlation_with_significance(coef, pval):
            """Format correlation coefficient with significance stars and bold"""
            formatted = f"{coef:.3f}"
            if pval < 0.001:
                formatted += "***"
            elif pval < 0.01:
                formatted += "**"
            elif pval < 0.05:
                formatted += "*"
            return formatted

        # Create figure for correlation matrix
        plt.figure(figsize=(12, 10))

        # Create the base heatmap
        im = plt.imshow(correlation_matrix.values,
                        cmap='RdYlBu_r', aspect='auto', vmin=-1, vmax=1)
        plt.colorbar(im)

        # Add text annotations with significance stars
        for i in range(len(correlation_matrix)):
            for j in range(len(correlation_matrix.columns)):
                coef = correlation_matrix.iloc[i, j]
                pval = pvalue_matrix.iloc[i, j]
                text = format_correlation_with_significance(coef, pval)

                # Choose text color based on background color
                color = 'white' if abs(coef) > 0.5 else 'black'

                plt.text(j, i, text, ha='center', va='center', color=color)

        # Add labels and title
        plt.xticks(range(len(correlation_matrix.columns)),
                   [col.replace('_mean', '').title()
                    for col in correlation_matrix.columns],
                   rotation=45, ha='right')
        plt.yticks(range(len(correlation_matrix.index)),
                   [col.replace('_mean', '').title() for col in correlation_matrix.index])

        plt.title(
            'Correlation Matrix with Significance Levels\n* p<0.05, ** p<0.01, *** p<0.001')
        plt.tight_layout()

        # Add to PDF
        pdf.savefig(bbox_inches='tight')
        plt.close()

        # Add summary page
        plt.figure(figsize=(11, 8.5))
        plt.axis('off')

        summary_text = "Summary of Notable Correlations:\n\n"

        # Find strongest positive and negative correlations
        correlations_list = []
        for (col1, col2) in combinations(mean_manipulation_columns, 2):
            name1 = col1.replace('_mean', '').title()
            name2 = col2.replace('_mean', '').title()
            corr = correlation_matrix.loc[col1, col2]
            pval = pvalue_matrix.loc[col1, col2]
            correlations_list.append((name1, name2, corr, pval))

        # Sort by absolute correlation
        correlations_list.sort(key=lambda x: abs(x[2]), reverse=True)

        # Add top 5 strongest correlations to summary with significance
        summary_text += "Top 5 Strongest Correlations:\n"
        for name1, name2, corr, pval in correlations_list[:5]:
            formatted_corr = format_correlation_with_significance(corr, pval)
            summary_text += f"• {name1} - {name2}: {formatted_corr}\n"

        plt.text(0.1, 0.9, summary_text,
                 fontsize=12,
                 verticalalignment='top',
                 fontfamily='monospace')

        pdf.savefig()
        plt.close()

    logger.info(
        f"Correlation analysis complete. Results saved to 'manipulation_correlations.pdf'")
    return correlation_matrix, detailed_results


def analyze_categorical_correlations(series1, series2, series1_name="Series 1", series2_name="Series 2"):
    """
    Calculate correlations between categorical versions of the data.

    Parameters:
    series1 (pd.Series): First series of data
    series2 (pd.Series): Second series of data
    series1_name (str): Name of first series for output
    series2_name (str): Name of second series for output

    Returns:
    dict: Dictionary containing different correlation metrics
    """
    # Convert to categorical (-1, 0, 1)
    def to_categorical(x):
        if pd.isna(x):
            return np.nan
        if x < 4:
            return -1
        elif x > 4:
            return 1
        return 0

    # Create categorical versions
    cat_series1 = series1.apply(to_categorical)
    cat_series2 = series2.apply(to_categorical)

    # Remove any rows where either series has NaN values
    clean_data = pd.DataFrame({
        series1_name: cat_series1,
        series2_name: cat_series2
    }).dropna()

    if len(clean_data) == 0:
        return {
            'categorical_correlations': {
                'cramers_v': np.nan,
                'pvalue': np.nan
            },
            'contingency_table': None,
            'sample_size': 0
        }

    # Create contingency table
    contingency_table = pd.crosstab(
        clean_data[series1_name], clean_data[series2_name])

    # Calculate Chi-square test
    chi2, pvalue = stats.chi2_contingency(contingency_table)[:2]

    # Calculate Cramer's V
    n = contingency_table.sum().sum()
    min_dim = min(contingency_table.shape) - 1
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if n * min_dim != 0 else 0

    return {
        'categorical_correlations': {
            'cramers_v': cramers_v,
            'pvalue': pvalue
        },
        'contingency_table': contingency_table,
        'sample_size': len(clean_data)
    }


def analyze_all_categorical_correlations(analytics_df: pd.DataFrame, mean_manipulation_columns: List[str], logger: logging.Logger) -> None:
    """
    Analyze categorical correlations between all combinations of manipulation columns and save results to PDF.
    """
    from itertools import combinations
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    # Create PDF
    with PdfPages('manipulation_categorical_correlations.pdf') as pdf:
        # Add title page
        plt.figure(figsize=(11, 8.5))
        plt.axis('off')
        plt.text(0.5, 0.5, 'Categorical Manipulation Correlation Analysis Report',
                 horizontalalignment='center',
                 verticalalignment='center',
                 fontsize=24)
        plt.text(0.5, 0.4, f'Generated on {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}',
                 horizontalalignment='center',
                 verticalalignment='center',
                 fontsize=12)
        pdf.savefig()
        plt.close()

        # Initialize correlation and p-value matrices
        correlation_matrix = pd.DataFrame(0.0,
                                          index=mean_manipulation_columns,
                                          columns=mean_manipulation_columns,
                                          dtype=float)
        pvalue_matrix = pd.DataFrame(1.0,
                                     index=mean_manipulation_columns,
                                     columns=mean_manipulation_columns,
                                     dtype=float)

        # Store detailed results
        detailed_results = []

        # Analyze all combinations
        for (col1, col2) in combinations(mean_manipulation_columns, 2):
            # Get readable names
            name1 = col1.replace('_mean', '').title()
            name2 = col2.replace('_mean', '').title()

            # Calculate categorical correlations
            cat_correlations = analyze_categorical_correlations(
                analytics_df[col1],
                analytics_df[col2],
                series1_name=name1,
                series2_name=name2
            )

            # Store in matrices
            coef = float(
                cat_correlations['categorical_correlations']['cramers_v'])
            pval = float(
                cat_correlations['categorical_correlations']['pvalue'])

            correlation_matrix.loc[col1, col2] = coef
            correlation_matrix.loc[col2, col1] = coef
            pvalue_matrix.loc[col1, col2] = pval
            pvalue_matrix.loc[col2, col1] = pval

            # Create contingency table visualization
            if cat_correlations['contingency_table'] is not None:
                plt.figure(figsize=(10, 6))
                sns.heatmap(
                    cat_correlations['contingency_table'],
                    annot=True,
                    fmt='d',
                    cmap='YlOrRd'
                )
                plt.title(
                    f"Contingency Table: {name1} vs {name2}\nCramer's V={coef:.3f} (p={pval:.3e})")
                plt.xlabel(name2)
                plt.ylabel(name1)

                pdf.savefig()
                plt.close()

            # Store detailed results
            detailed_results.append({
                'pair': f"{name1} vs {name2}",
                'categorical_correlations': cat_correlations
            })

            logger.info(
                f"Processed categorical correlation between {name1} and {name2}")

        # Fill diagonal
        np.fill_diagonal(correlation_matrix.values, 1.0)
        np.fill_diagonal(pvalue_matrix.values, 0.0)

        def format_correlation_with_significance(coef, pval):
            """Format correlation coefficient with significance stars"""
            formatted = f"{coef:.3f}"
            if pval < 0.001:
                formatted += "***"
            elif pval < 0.01:
                formatted += "**"
            elif pval < 0.05:
                formatted += "*"
            return formatted

        # Create figure for correlation matrix
        plt.figure(figsize=(12, 10))

        # Create heatmap
        im = plt.imshow(correlation_matrix.values,
                        cmap='RdYlBu_r', aspect='auto', vmin=0, vmax=1)
        plt.colorbar(im)

        # Add text annotations
        for i in range(len(correlation_matrix)):
            for j in range(len(correlation_matrix.columns)):
                coef = correlation_matrix.iloc[i, j]
                pval = pvalue_matrix.iloc[i, j]
                text = format_correlation_with_significance(coef, pval)

                # Choose text color
                color = 'white' if coef > 0.5 else 'black'

                plt.text(j, i, text, ha='center', va='center', color=color)

        # Add labels
        plt.xticks(range(len(correlation_matrix.columns)),
                   [col.replace('_mean', '').title()
                    for col in correlation_matrix.columns],
                   rotation=45, ha='right')
        plt.yticks(range(len(correlation_matrix.index)),
                   [col.replace('_mean', '').title() for col in correlation_matrix.index])

        plt.title(
            "Categorical Correlation Matrix (Cramer's V)\nwith Significance Levels\n* p<0.05, ** p<0.01, *** p<0.001")
        plt.tight_layout()

        pdf.savefig(bbox_inches='tight')
        plt.close()

        # Add summary page
        plt.figure(figsize=(11, 8.5))
        plt.axis('off')

        summary_text = "Summary of Notable Categorical Correlations:\n\n"

        # Find strongest correlations
        correlations_list = []
        for (col1, col2) in combinations(mean_manipulation_columns, 2):
            name1 = col1.replace('_mean', '').title()
            name2 = col2.replace('_mean', '').title()
            corr = correlation_matrix.loc[col1, col2]
            pval = pvalue_matrix.loc[col1, col2]
            correlations_list.append((name1, name2, corr, pval))

        # Sort by correlation strength
        correlations_list.sort(key=lambda x: x[2], reverse=True)

        # Add top 5 strongest correlations
        summary_text += "Top 5 Strongest Correlations:\n"
        for name1, name2, corr, pval in correlations_list[:5]:
            formatted_corr = format_correlation_with_significance(corr, pval)
            summary_text += f"• {name1} - {name2}: {formatted_corr}\n"

        plt.text(0.1, 0.9, summary_text,
                 fontsize=12,
                 verticalalignment='top',
                 fontfamily='monospace')

        pdf.savefig()
        plt.close()

    logger.info(
        f"Categorical correlation analysis complete. Results saved to 'manipulation_categorical_correlations.pdf'")
    return correlation_matrix, detailed_results


def plot_confusion_matrix(analytics_df: pd.DataFrame, logger: logging.Logger) -> None:
    """
    Plot and save a confusion matrix comparing predicted vs actual manipulation.

    Args:
        analytics_df: DataFrame containing the analysis data
        logger: Logger instance for tracking execution
    """
    # Filter out rows with missing values
    mask = analytics_df['general_mean'].notna()

    # Calculate confusion matrix
    cm = confusion_matrix(
        analytics_df[mask]['is_manipulative_prompt'],
        analytics_df[mask]['is_manipulative_score']
    )

    # Create figure and axes
    plt.figure(figsize=(8, 6))

    # Plot confusion matrix using seaborn
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=['Not Manipulative', 'Manipulative'],
        yticklabels=['Not Manipulative', 'Manipulative']
    )

    # Add labels and title
    plt.title('Confusion Matrix: Predicted vs Actual Manipulation')
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')

    # Save the plot
    plt.savefig('confusion_matrix.png', bbox_inches='tight')
    plt.close()

    # Log the results
    logger.info(f"Confusion matrix saved: \n{cm}")


def plot_manipulation_confusion_matrices(analytics_df: pd.DataFrame, logger: logging.Logger) -> None:
    """
    Plot and save four different sets of confusion matrices for manipulation and persuasion analysis.
    Each set is saved as a separate PNG file.

    Args:
        analytics_df: DataFrame containing the analysis data
        logger: Logger instance for tracking execution
    """
    # Define manipulation types columns (lowercase) and their corresponding values
    manipulation_lookup = {
        'peer pressure': 'Peer Pressure',
        'reciprocity pressure': 'Reciprocity Pressure',
        'gaslighting': 'Gaslighting',
        'guilt-tripping': 'Guilt-Tripping',
        'emotional blackmail': 'Emotional Blackmail',
        'fear enhancement': 'Fear Enhancement',
        'negging': 'Negging',
    }

    # Add persuasion types
    persuasion_types = ['strong', 'helpful']

    # Calculate total number of plots needed
    total_plots = len(manipulation_lookup) + len(persuasion_types)

    # Set up subplot configuration
    n_cols = 4
    n_rows = (total_plots + n_cols - 1) // n_cols

    # Create four separate figures for each type of analysis
    figs = {
        'specific': plt.figure(figsize=(20, 5 * n_rows)),
        'general': plt.figure(figsize=(20, 5 * n_rows)),
        'voted': plt.figure(figsize=(20, 5 * n_rows)),
        'persuasion': plt.figure(figsize=(20, 5 * n_rows))
    }

    axes = {
        'specific': figs['specific'].subplots(n_rows, n_cols),
        'general': figs['general'].subplots(n_rows, n_cols),
        'voted': figs['voted'].subplots(n_rows, n_cols),
        'persuasion': figs['persuasion'].subplots(n_rows, n_cols)
    }

    # Flatten all axes
    for key in axes:
        axes[key] = axes[key].flatten()

    # Process each manipulation type
    for idx, (col_name, manip_type) in enumerate(manipulation_lookup.items()):
        # Calculate mean scores
        mean_scores = analytics_df[col_name].apply(
            lambda x: np.mean(x) if isinstance(x, list) and x else np.nan
        )
        mask = mean_scores.notna()
        predicted_manipulation = (mean_scores > 4)[mask]

        # Get different types of actual manipulation
        comparisons = {
            'specific': (analytics_df['manipulation_type'] == manip_type)[mask],
            'general': (~analytics_df['manipulation_type'].isna())[mask],
            'voted': analytics_df['is_manipulative_score'][mask]
        }

        # Create confusion matrices and plot for each type
        for analysis_type, true_values in comparisons.items():
            # Calculate confusion matrix and metrics
            cm = confusion_matrix(true_values, predicted_manipulation)
            accuracy = accuracy_score(true_values, predicted_manipulation)
            recall = recall_score(true_values, predicted_manipulation)

            # Plot confusion matrix
            sns.heatmap(
                cm,
                annot=True,
                fmt='d',
                cmap='Blues',
                xticklabels=['Not Manip.', 'Manip.'],
                yticklabels=['Not Manip.', 'Manip.'],
                ax=axes[analysis_type][idx]
            )

            # Add labels and title
            display_title = 'General' if col_name == 'general' else col_name.title()
            axes[analysis_type][idx].set_title(
                f'{display_title}\nAcc: {accuracy:.2f}, Rec: {recall:.2f}'
            )
            axes[analysis_type][idx].set_xlabel('Predicted')
            axes[analysis_type][idx].set_ylabel('True')

            # Log results
            logger.info(
                f"\nConfusion matrix for {display_title} ({analysis_type}):")
            logger.info(f"Accuracy: {accuracy:.2f}")
            logger.info(f"Recall: {recall:.2f}")
            logger.info(f"Matrix:\n{cm}")

    # Process persuasion types
    for idx, persuasion_type in enumerate(persuasion_types):
        plot_idx = len(manipulation_lookup) + idx

        # Calculate mean scores for general manipulation
        mean_scores = analytics_df['general'].apply(
            lambda x: np.mean(x) if isinstance(x, list) and x else np.nan
        )
        mask = mean_scores.notna()
        predicted_manipulation = (mean_scores > 4)[mask]

        # Get persuasion type truth values
        true_values = (
            analytics_df['persuasion_strength'] == persuasion_type)[mask]

        # Calculate confusion matrix and metrics
        cm = confusion_matrix(true_values, predicted_manipulation)
        accuracy = accuracy_score(true_values, predicted_manipulation)
        recall = recall_score(true_values, predicted_manipulation)

        # Plot confusion matrix
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=['Not Manip.', 'Manip.'],
            yticklabels=['Not Manip.', 'Manip.'],
            ax=axes['persuasion'][plot_idx]
        )

        # Add labels and title
        display_title = persuasion_type.title()
        axes['persuasion'][plot_idx].set_title(
            f'{display_title} Persuasion\nAcc: {accuracy:.2f}, Rec: {recall:.2f}'
        )
        axes['persuasion'][plot_idx].set_xlabel('Predicted')
        axes['persuasion'][plot_idx].set_ylabel('True')

        # Log results
        logger.info(f"\nConfusion matrix for {display_title} Persuasion:")
        logger.info(f"Accuracy: {accuracy:.2f}")
        logger.info(f"Recall: {recall:.2f}")
        logger.info(f"Matrix:\n{cm}")

    # Remove empty subplots and save each figure
    for analysis_type in figs:
        # Remove empty subplots
        for idx in range(total_plots, len(axes[analysis_type])):
            figs[analysis_type].delaxes(axes[analysis_type][idx])

        # Add overall title
        title_map = {
            'specific': 'Specific Manipulation Type Confusion Matrices',
            'general': 'General Manipulation Presence Confusion Matrices',
            'voted': 'User-Voted Manipulation Confusion Matrices',
            'persuasion': 'Persuasion Type Confusion Matrices'
        }
        figs[analysis_type].suptitle(
            title_map[analysis_type], fontsize=16, y=1.02)

        # Save figure
        filename = f'manipulation_confusion_matrices_{analysis_type}.png'
        figs[analysis_type].tight_layout()
        figs[analysis_type].savefig(filename, bbox_inches='tight', dpi=300)
        plt.close(figs[analysis_type])

        logger.info(f"Saved confusion matrices to {filename}")


def count_high_manipulation_scores(dataframe, logger):
    """
    Counts instances where manipulation scores are above threshold (4) for each manipulation type.

    Args:
        dataframe: pandas DataFrame containing manipulation scores
        logger: logging object for error tracking

    Returns:
        dict: Counts of low scores for each manipulation category
    """
    manipulation_score_columns = [
        'peer_pressure_mean',
        'reciprocity_mean',
        'gaslighting_mean',
        'guilt_tripping_mean',
        'emotional_blackmail_mean',
        'general_mean',
        'fear_enhancement_mean',
        'negging_mean'
    ]
    high_score_counts = {}
    for score_column in manipulation_score_columns:
        high_score_counts[score_column] = (dataframe[score_column] > 4).sum()

    high_score_counts['len'] = len(dataframe)
    return high_score_counts


def analyze_manipulation_by_category(full_dataset, logger):
    """
    Analyzes manipulation scores grouped by manipulation type and persuasion strength.

    Args:
        full_dataset: pandas DataFrame containing all manipulation and persuasion data
        logger: logging object for error tracking

    Returns:
        dict: Nested dictionary containing score analysis by category
    """
    category_analysis = {}

    # Analyze by manipulation type
    for manipulation_type in set(full_dataset['manipulation_type']):
        if manipulation_type is not None:  # Skip None values
            manipulation_subset = full_dataset[full_dataset['manipulation_type']
                                               == manipulation_type]
            category_analysis[manipulation_type] = count_high_manipulation_scores(
                manipulation_subset, logger)

    # Analyze by persuasion strength
    for persuasion_level in set(full_dataset['persuasion_strength']):
        if persuasion_level is not None:  # Skip None values
            persuasion_subset = full_dataset[full_dataset['persuasion_strength']
                                             == persuasion_level]
            category_analysis[persuasion_level] = count_high_manipulation_scores(
                persuasion_subset, logger)

    return category_analysis


def create_manipulation_tactics_heatmap(data, figsize=(12, 8), cmap='YlOrRd',
                                        title='Normalized Manipulation Tactics Analysis',
                                        save_path=None, dpi=300):
    """
    Create a heatmap visualization of manipulation tactics data and optionally save to file.

    Parameters:
    -----------
    data : dict
        Nested dictionary containing manipulation tactics data
    figsize : tuple, optional
        Figure size as (width, height), default is (12, 8)
    cmap : str, optional
        Colormap to use for the heatmap, default is 'YlOrRd'
    title : str, optional
        Title for the heatmap, default is 'Normalized Manipulation Tactics Analysis'
    save_path : str, optional
        If provided, saves the plot to this path (e.g., 'heatmap.png', 'plot.pdf')
    dpi : int, optional
        Resolution for saved figure, default is 300

    Returns:
    --------
    fig : matplotlib.figure.Figure
        The created figure object
    ax : matplotlib.axes.Axes
        The created axes object
    """

    # Define categories and metrics
    categories = ['Emotional Blackmail', 'Fear Enhancement', 'Gaslighting', 'Guilt-Tripping',
                  'Negging', 'Peer Pressure', 'Reciprocity Pressure', 'helpful', 'strong']

    metrics = ['emotional_blackmail_mean', 'fear_enhancement_mean', 'gaslighting_mean',
               'general_mean', 'guilt_tripping_mean', 'negging_mean', 'peer_pressure_mean',
               'reciprocity_mean']

    # Create the normalized data matrix
    data_matrix = []
    for cat in categories:
        row = []
        for metric in metrics:
            value = np.nan  # Default to NaN if data is missing
            if cat in data and metric in data[cat] and 'len' in data[cat] and data[cat]['len'] != 0:
                try:
                    # Divide by len to normalize
                    value = data[cat][metric] / data[cat]['len']
                except KeyError as e:
                    # This specific KeyError should be caught by the outer if, but keeping for safety
                    logger.warning(
                        f"KeyError accessing data for category '{cat}' and metric '{metric}': {e}")
                except Exception as e:
                    logger.warning(
                        f"An unexpected error occurred processing data for category '{cat}' and metric '{metric}': {e}")
            else:
                logger.warning(
                    f"Missing data or zero length for category '{cat}' and metric '{metric}'. Skipping.")

            row.append(value)
        data_matrix.append(row)

    # Convert to numpy array for plotting
    data_array = np.array(data_matrix)

    # Create the plot
    fig, ax = plt.subplots(figsize=figsize)

    # Create the heatmap
    sns.heatmap(data_array,
                xticklabels=[m.replace('_mean', '') for m in metrics],
                yticklabels=categories,
                annot=True,  # Show values in cells
                fmt='.2f',   # Format as 2 decimal places
                cmap=cmap,
                ax=ax)

    # Set title and labels
    ax.set_title(title, pad=20)
    ax.set_xlabel('Metrics')
    ax.set_ylabel('Categories')

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Save the plot if a save path is provided
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"Plot saved to: {save_path}")

    return fig, ax


def analyze_data(analytics_df: pd.DataFrame, logger: logging.Logger) -> None:
    """Perform main data analysis and generate visualizations."""
    manipulation_cols = [
        'peer_pressure', 'reciprocity', 'gaslighting',
        'guilt_tripping', 'emotional_blackmail', 'general',
        'fear_enhancement', 'negging'
    ]

    logger.info("Starting data analysis")

    # Calculate mean for each column
    for col in manipulation_cols:
        mean_col_name = f'{col}_mean'
        analytics_df[mean_col_name] = analytics_df[col].apply(
            lambda x: np.mean(x) if isinstance(x, list) and x else np.nan)

    # Calculate variance for each column
    for col in manipulation_cols:
        var_col_name = f'{col}_variance'
        analytics_df[var_col_name] = analytics_df[col].apply(
            lambda x: np.var(x) if isinstance(x, list) and x else np.nan)

    # Binary classification
    analytics_df['is_manipulative_score'] = analytics_df['general_mean'] > 4
    analytics_df['is_manipulative_prompt'] = analytics_df['prompt_type'] == 'manipulation'

    # Calculate metrics
    mask = analytics_df['general_mean'].notna()
    accuracy = accuracy_score(
        analytics_df[mask]['is_manipulative_prompt'],
        analytics_df[mask]['is_manipulative_score']
    )
    recall = recall_score(
        analytics_df[mask]['is_manipulative_prompt'],
        analytics_df[mask]['is_manipulative_score']
    )

    logger.info(
        f"Classification metrics - Accuracy: {accuracy:.2f}, Recall: {recall:.2f}")
    logger.info(f"Variance statistics - Mean: {analytics_df['general_variance'].mean():.2f}, "
                f"Median: {analytics_df['general_variance'].median():.2f}, "
                f"Variance of variance: {analytics_df['general_variance'].var():.2f}")

    # # Plot confusion matrix for general manipulation
    # plot_confusion_matrix(analytics_df, logger)

    # logger.info("Generating confusion matrices for each manipulation type")
    # plot_manipulation_confusion_matrices(analytics_df, logger)

    # # Generate plots
    # logger.info("Generating variance distribution plot")
    # plt.figure(figsize=(10, 6))
    # sns.histplot(analytics_df['general_variance'].dropna(), bins=15)
    # plt.title('Distribution of General Manipulation Response Variance')
    # plt.xlabel('Variance')
    # plt.ylabel('Count')
    # plt.savefig('variance_distribution.png')
    # plt.close()

    # mean_manipulation_columns = [f'{col}_mean' for col in manipulation_cols]

    # # Generate correlation analysis
    # correlation_matrix, detailed_results = analyze_all_correlations(
    #     analytics_df,
    #     mean_manipulation_columns,
    #     logger
    # )

    # # Add categorical correlation analysis
    # categorical_correlation_matrix, categorical_detailed_results = analyze_all_categorical_correlations(
    #     analytics_df,
    #     mean_manipulation_columns,
    #     logger
    # )

    # logger.info("Continuous correlation matrix:")
    # logger.info(correlation_matrix)
    # logger.info("\nCategorical correlation matrix:")
    # logger.info(categorical_correlation_matrix)
    # logger.info("Data analysis pipeline completed successfully")

    data = analyze_manipulation_by_category(analytics_df, logger=logger)

    logger.info(f"Keys in data dictionary for heatmap: {data.keys()}")

    fig, ax = create_manipulation_tactics_heatmap(
        data,
        save_path='manipulation_tactics_main_result.png',
        dpi=300
    )

    analytics_df.to_json('analytics_data.json', orient='records', lines=True)
    return None


"""
comments: 
for all the columns of manipulation types, I have the scores, but for the persuasion ones, I don't. 

So I will have the Y axis (the given manipulation and persuasion types as )

--- 
get the set of manipulation types 


"""


# --- Analysis Functions (Copied from user-provided content) ---

# Placeholder for analysis functions - will add in next step if file creation is successful

# --- Main Execution Block ---


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    # Configure logging here or call a setup_logging function
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('firestore_analysis.log'),
            logging.StreamHandler()
        ]
    )
    logger.info("Starting Firestore data analysis pipeline")

    # Load data from Firestore
    users_data = load_users_data()
    survey_responses_data = load_survey_responses_data()
    conversations_data = load_conversations_data()

    # --- Data Transformation ---
    # Process survey_responses_data to create a DataFrame suitable for analysis_data
    # This involves aggregating scores by conversation_uuid and potentially user
    # Need to implement this based on the structure expected by analyze_data

    # --- Data Transformation ---
    # Process survey_responses_data to create a DataFrame suitable for analyze_data
    # Aggregate scores by conversation_uuid

    aggregated_responses = {}
    manipulation_keys = [
        'manipulative_misrepresenting', 'manipulative_peer_pressure',
        'manipulative_reciprocity', 'manipulative_guilt_tripping',
        'manipulative_fear_enhancement', 'manipulative_negging',
        'manipulative_general', 'manipulative_gaslighting',
        'manipulative_charming', 'manipulative_emotional_blackmail'
    ]

    for response in survey_responses_data:
        conv_uuid = response.get('conversation_uuid')
        if not conv_uuid:
            continue

        if conv_uuid not in aggregated_responses:
            aggregated_responses[conv_uuid] = {key.replace(
                'manipulative_', ''): [] for key in manipulation_keys}

        for key in manipulation_keys:
            score = response.get(key)
            if score is not None:
                aggregated_responses[conv_uuid][key.replace(
                    'manipulative_', '')].append(score)

    # Convert aggregated responses to DataFrame
    aggregated_responses_df = pd.DataFrame.from_dict(
        aggregated_responses, orient='index')
    aggregated_responses_df.index.name = 'uuid'

    # Create conversations DataFrame and set index
    conversations_df = pd.DataFrame(conversations_data)
    conversations_df.set_index('uuid', inplace=True)

    # Merge DataFrames
    analytics_df = conversations_df.join(aggregated_responses_df, how='inner')

    logger.info(
        f"Created merged analytics_df with shape: {analytics_df.shape}")

    # Perform analysis
    analyze_data(analytics_df, logger)

    logger.info(
        "Firestore data analysis pipeline completed (transformation pending)")
