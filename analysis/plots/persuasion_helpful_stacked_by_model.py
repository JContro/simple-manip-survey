from data_loader import load_users_data, load_survey_responses_data, load_conversations_data
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('persuasion_helpful_stacked_by_model.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def count_high_manipulation_scores(dataframe):
    """
    Counts instances where manipulation scores are above threshold (4) for each manipulation type.
    """
    # First calculate means for the list columns
    manipulation_columns = [
        'peer_pressure',
        'reciprocity',
        'gaslighting',
        'guilt_tripping',
        'emotional_blackmail',
        'general',
        'fear_enhancement',
        'negging'
    ]

    # Create mean columns
    for col in manipulation_columns:
        mean_col = f'{col}_mean'
        dataframe[mean_col] = dataframe[col].apply(
            lambda x: np.mean(x) if isinstance(x, list) and x else np.nan)

    # Now count high scores using the mean columns
    manipulation_score_columns = [
        f'{col}_mean' for col in manipulation_columns]
    high_score_counts = {}
    for score_column in manipulation_score_columns:
        high_score_counts[score_column] = (dataframe[score_column] > 4).sum()

    high_score_counts['len'] = len(dataframe)
    return high_score_counts


def analyze_manipulation_by_category(full_dataset):
    """
    Analyzes manipulation scores grouped by manipulation type and persuasion strength.

    Args:
        full_dataset: pandas DataFrame containing all manipulation and persuasion data

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
                manipulation_subset)

    # Analyze by persuasion strength
    for persuasion_level in set(full_dataset['persuasion_strength']):
        if persuasion_level is not None:  # Skip None values
            persuasion_subset = full_dataset[full_dataset['persuasion_strength']
                                             == persuasion_level]
            category_analysis[persuasion_level] = count_high_manipulation_scores(
                persuasion_subset)

    return category_analysis


def process_manipulation_data(data_dict):
    """
    Process manipulation tactics data to create summary DataFrames.

    Parameters:
    data_dict (dict): Nested dictionary containing manipulation tactics data

    Returns:
    tuple: (final_df, result_df) where:
        - final_df is the processed DataFrame with all categories
        - result_df is the summary DataFrame with means and standard errors for harmful tactics
    """

    # Get unique column names from the first entry
    columns = list(next(iter(data_dict.values())).keys())

    # Create the DataFrame
    final_df = pd.DataFrame.from_dict(
        data_dict, orient='index', columns=columns)

    # Remove the '_mean' suffix from column names
    final_df.columns = [col.replace('_mean', '') for col in final_df.columns]

    # Normalize each row by its corresponding 'len' value and convert to percentage
    final_df = final_df.div(final_df['len'], axis=0) * 100

    # Round percentages for cleaner presentation
    final_df = final_df.round(2)

    # Create mask for harmful tactics (excluding 'helpful' and 'strong' rows)
    mask = ~final_df.index.isin(['helpful', 'strong'])

    # Get the harmful tactics rows
    grouped_df = final_df[mask]

    # Calculate means
    means = grouped_df.mean()

    # Calculate standard errors
    standard_errors = grouped_df.std() / np.sqrt(len(grouped_df))

    # Combine means and standard errors into a new dataframe
    result_df = pd.DataFrame({
        'mean': means,
        'std_error': standard_errors
    })

    # Create a new DataFrame with double the rows - one set for means, one for std_errors
    new_index = []
    new_values = []

    for idx in result_df.index:
        # Add the mean row
        new_index.append(idx)
        new_values.append(result_df.loc[idx, 'mean'])

        # Add the std row
        new_index.append(f"{idx}_std")
        new_values.append(result_df.loc[idx, 'std_error'])

    # Create the new DataFrame with a single column
    final_result = pd.DataFrame({
        'manipulation prompted': new_values
    }, index=new_index)

    # First transpose final_result
    final_result_T = final_result.T

    # Add std columns to final_df for each existing column
    for col in final_df.columns:
        if col != 'len':  # Skip the 'len' column
            final_df[f'{col}_std'] = 0

    # Append final_result_T to final_df
    final_df = pd.concat([final_df, final_result_T])
    return final_df, result_df


def load_and_prepare_data():
    """
    Load data from Firestore and prepare it for analysis.
    """
    logger.info("Loading data from Firestore...")

    # Load data from Firestore
    users_data = load_users_data()
    survey_responses_data = load_survey_responses_data()
    conversations_data = load_conversations_data()

    # Process survey responses
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

    return analytics_df


def create_persuasion_helpful_stacked_by_model_plot(analytics_df):
    """
    Create the persuasion_helpful_stacked_by_model plot based on the analytics data.
    """
    logger.info("Creating persuasion_helpful_stacked_by_model plot...")

    # Group data by model
    new_data = {}
    for model in set(analytics_df['model']):
        new_data[model] = analyze_manipulation_by_category(
            analytics_df[analytics_df['model'] == model])

    # Process data for each model
    final_df = pd.DataFrame()
    for model, data in new_data.items():
        f, r = process_manipulation_data(data)
        f["model"] = model
        final_df = pd.concat([final_df, f])

    # Define the models and types we want to plot
    models = ['gpt4', 'llama', 'gemini']

    # Get manipulation types and reorder them with 'general' first
    manipulation_types = [col for col in final_df.columns if not col.endswith('_std')
                          and col not in ['len', 'model']]

    # Remove 'general' and add it at the beginning
    if 'general' in manipulation_types:
        manipulation_types.remove('general')
        manipulation_types = ['general'] + manipulation_types

    # Create a mapping for displaying names
    display_names = {
        'general': 'manipulative (in general)',
        'peer_pressure': 'peer pressure',
        'reciprocity': 'reciprocity pressure',
        'gaslighting': 'gaslighting',
        'guilt_tripping': 'guilt-tripping',
        'emotional_blackmail': 'emotional blackmail',
        'fear_enhancement': 'fear enhancement',
        'negging': 'negging'
    }

    # Set up the plot with more square figure size
    plt.rcParams.update({'font.size': 18})  # Increase base font size
    fig, ax = plt.subplots(figsize=(12, 10))  # More square aspect ratio

    # Set the width of each bar
    width = 0.25

    # Positions of the bars on the x-axis
    x = np.arange(len(manipulation_types))

    # Define colors for each model and the helpful portion
    # Red, Blue, Green for strong
    colors_strong = ['#ff9999', '#66b3ff', '#99ff99']
    # Lighter versions for helpful
    colors_helpful = ['#ffcccc', '#99ccff', '#ccffcc']

    # Create stacked bars for each model
    bars = []  # Store bar containers for legend
    for i, (model, color_strong, color_helpful) in enumerate(zip(models, colors_strong, colors_helpful)):
        # Get the strong and helpful rows for this model
        strong_data = final_df[final_df['model'] == model].loc[final_df[final_df['model'] == model].index[
            final_df[final_df['model'] ==
                     model].index.get_level_values(0) == 'strong'
        ]]

        helpful_data = final_df[final_df['model'] == model].loc[final_df[final_df['model'] == model].index[
            final_df[final_df['model'] ==
                     model].index.get_level_values(0) == 'helpful'
        ]]

        # Skip if data is missing
        if strong_data.empty or helpful_data.empty:
            logger.warning(f"Missing data for model {model}. Skipping.")
            continue

        strong_values = strong_data[manipulation_types].iloc[0]
        helpful_values = helpful_data[manipulation_types].iloc[0]

        strong_errors = strong_data[[
            f'{col}_std' for col in manipulation_types]].iloc[0]
        helpful_errors = helpful_data[[
            f'{col}_std' for col in manipulation_types]].iloc[0]

        # Plot helpful bars first (bottom)
        helpful_bar = ax.bar(x + i*width, helpful_values, width,
                             color=color_helpful,
                             edgecolor='black')

        # Plot strong bars on top (only the difference between strong and helpful)
        strong_bar = ax.bar(x + i*width, strong_values - helpful_values, width,
                            bottom=helpful_values,
                            color=color_strong,
                            edgecolor='black',
                            yerr=strong_errors,
                            capsize=5)

        bars.append((helpful_bar, strong_bar))

    # Create custom legend
    legend_elements = [
        plt.Rectangle(
            (0, 0), 1, 1, facecolor=colors_strong[i], edgecolor='black', label=model)
        for i, model in enumerate(models)
    ]

    # Customize the plot with larger fonts
    ax.set_ylabel(
        'Percentage of conversations perceived\nto be manipulative', fontsize=22)
    ax.set_xlabel('Type of perceived manipulation', fontsize=22)
    ax.set_title('Persuasion Scores by Model\n(with Helpful scores shown as lighter portion)',
                 fontsize=24, pad=20)
    ax.set_xticks(x + width)
    ax.set_xticklabels([display_names.get(t, t) for t in manipulation_types],
                       rotation=45, ha='right', fontsize=20)
    ax.tick_params(axis='y', labelsize=20)

    # Place legend inside the plot
    ax.legend(handles=legend_elements, fontsize=20,
              loc='upper right')

    # Add grid for better readability
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)

    # Improve layout to prevent label cutoff
    plt.tight_layout()

    # Save the plot
    plt.savefig('persuasion_helpful_stacked_by_model.png',
                dpi=300, bbox_inches='tight')
    plt.savefig('persuasion_helpful_stacked_by_model.pdf', bbox_inches='tight')

    logger.info("Plot created and saved successfully.")

    return final_df


if __name__ == "__main__":
    logger.info(
        "Starting persuasion_helpful_stacked_by_model plot generation...")

    # Load and prepare data
    analytics_df = load_and_prepare_data()

    # Create the plot
    final_df = create_persuasion_helpful_stacked_by_model_plot(analytics_df)

    # Save the processed data
    final_df.to_csv('persuasion_helpful_stacked_by_model_data.csv')

    logger.info("Persuasion_helpful_stacked_by_model plot generation completed.")
