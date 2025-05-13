"""
Aggregate Zero-Shot Results Script

This script aggregates the evaluation results from different models and formats them
into a table similar to the LaTeX table provided. It groups the results by model type
(zero-shot, few-shot, CoT, finetuned) and extracts the relevant metrics.
"""

import os
import json
import pandas as pd
import numpy as np
import re

# Define the results directory
RESULTS_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "results")

# Define model name mappings for better display
MODEL_NAME_MAPPING = {
    "chatgpt-4o-latest": "gpt-4o-2024-08-06",
    "claude-3.5-sonnet-few-shot": "claude-3-5-sonnet-20241022",
    "deepseek-chat": "DeepSeek-V3",
    "deepseek-chat-few-shot": "DeepSeek-V3",
    "gemini-2.0-flash-001": "gemini-2.0-flash",
    "gemini-2.0-flash-001-few-shot": "gemini-2.0-flash",
    "llama-3.1-405b-instruct": "llama-3.1-405b-instruct",
    "llama-3.1-405b-instruct-few-shot": "llama-3.1-405b-instruct",
    "llama-3.3-70b-instruct": "llama-3.3-70b-instruct",
    "perplexity-r1-1776": "Perplexity R1",
    "perplexity-r1-1776-cot-few-shot": "Perplexity R1",
    "openai-o1-mini-cot-few-shot": "openai-o1-mini"
}

# Define model types
MODEL_TYPES = {
    "zs": "Zero-shot",
    "fs": "Few-shot",
    "cot": "CoT (Perplexity R1)"
}

# Define finetuned models (these are not in the results directory)
FINETUNED_MODELS = {
    "longformer-base-4096": {
        "hamming_accuracy": (0.691, 0.015),
        "precision": (0.607, 0.037),
        "recall": (0.556, 0.072),
        "f1": (0.557, 0.033)
    },
    "deberta-v3-base": {
        "hamming_accuracy": (0.706, 0.009),
        "precision": (0.643, 0.015),
        "recall": (0.534, 0.034),
        "f1": (0.566, 0.022)
    },
    "BERT + BiLSTM": {
        "hamming_accuracy": (0.697, 0.015),
        "precision": (0.613, 0.020),
        "recall": (0.645, 0.070),
        "f1": (0.619, 0.039)
    }
}


def extract_model_info_from_filename(filename):
    """
    Extract model name and type from the evaluation filename.

    Args:
        filename: The evaluation filename

    Returns:
        tuple: (model_name, model_type)
    """
    # Remove the _evaluation.json suffix
    base_name = filename.replace("_evaluation.json", "")

    # Check if it's a zero-shot, few-shot, or CoT model
    if base_name.endswith("_zs"):
        model_name = base_name[:-3]
        model_type = "zs"
    elif base_name.endswith("_fs"):
        model_name = base_name[:-3]
        model_type = "fs"
    elif base_name.endswith("_cot"):
        model_name = base_name[:-4]
        model_type = "cot"
    else:
        # Default to zero-shot if no suffix
        model_name = base_name
        model_type = "zs"

    return model_name, model_type


def load_evaluation_results():
    """
    Load all evaluation results from the results directory.

    Returns:
        dict: Dictionary mapping model names to their evaluation results
    """
    results = {}

    for filename in os.listdir(RESULTS_DIR):
        if filename.endswith("_evaluation.json"):
            file_path = os.path.join(RESULTS_DIR, filename)

            with open(file_path, 'r') as f:
                data = json.load(f)

            model_name, model_type = extract_model_info_from_filename(
                filename[:-len("_evaluation.json")])

            # Use the display name if available
            display_name = MODEL_NAME_MAPPING.get(model_name, model_name)

            # Store the results with model name and type
            results[(display_name, model_type)] = data

    return results


def format_metric_with_std(mean, std):
    """
    Format a metric with its standard deviation.

    Args:
        mean: Mean value
        std: Standard deviation

    Returns:
        str: Formatted string
    """
    return f"{mean:.3f} ± {std:.3f}"


def create_results_table(results):
    """
    Create a results table from the evaluation results.

    Args:
        results: Dictionary mapping model names to their evaluation results

    Returns:
        pd.DataFrame: Results table
    """
    table_data = []

    # Process results for each model type
    for model_type, type_name in MODEL_TYPES.items():
        # Filter models of the current type
        type_models = {name: data for (
            name, mtype), data in results.items() if mtype == model_type}

        # Skip if no models of this type
        if not type_models:
            continue

        # Add a header row for the model type
        table_data.append({
            "Model": f"\\multicolumn{{5}}{{c}}{{{type_name}}}",
            "Accuracy (Hamming Score)": "",
            "Precision": "",
            "Recall": "",
            "F1": ""
        })

        # Add rows for each model
        for model_name, data in type_models.items():
            stats = data["statistical_analysis"]["overall"]

            row = {
                "Model": model_name,
                "Accuracy (Hamming Score)": format_metric_with_std(
                    stats["hamming_accuracy"]["mean"],
                    stats["hamming_accuracy"]["std"]
                ),
                "Precision": format_metric_with_std(
                    stats["precision"]["mean"],
                    stats["precision"]["std"]
                ),
                "Recall": format_metric_with_std(
                    stats["recall"]["mean"],
                    stats["recall"]["std"]
                ),
                "F1": format_metric_with_std(
                    stats["f1"]["mean"],
                    stats["f1"]["std"]
                )
            }

            table_data.append(row)

    # Add finetuned models
    table_data.append({
        "Model": "\\multicolumn{5}{c}{Finetuned}",
        "Accuracy (Hamming Score)": "",
        "Precision": "",
        "Recall": "",
        "F1": ""
    })

    for model_name, metrics in FINETUNED_MODELS.items():
        row = {
            "Model": model_name,
            "Accuracy (Hamming Score)": format_metric_with_std(
                metrics["hamming_accuracy"][0],
                metrics["hamming_accuracy"][1]
            ),
            "Precision": format_metric_with_std(
                metrics["precision"][0],
                metrics["precision"][1]
            ),
            "Recall": format_metric_with_std(
                metrics["recall"][0],
                metrics["recall"][1]
            ),
            "F1": format_metric_with_std(
                metrics["f1"][0],
                metrics["f1"][1]
            )
        }

        table_data.append(row)

    return pd.DataFrame(table_data)


def generate_latex_table(df):
    """
    Generate a LaTeX table from the DataFrame.

    Args:
        df: DataFrame containing the results

    Returns:
        str: LaTeX table
    """
    latex = "\\begin{table*}[htbp]\n"
    latex += "\\centering\n"
    latex += "\\begin{tabular}{lcccc}\n"
    latex += "\\hline\n"
    latex += "Model & Accuracy (Hamming Score) & Precision & Recall & F1 \\\\\n"
    latex += "\\hline\n"

    # Add rows
    for _, row in df.iterrows():
        if "\\multicolumn" in str(row["Model"]):
            # This is a header row
            latex += f"{row['Model']} \\\\\n"
            latex += "\\hline\n"
        else:
            # This is a data row
            latex += f"{row['Model']} & {row['Accuracy (Hamming Score)']} & {row['Precision']} & {row['Recall']} & {row['F1']} \\\\\n"

    latex += "\\hline\n"
    latex += "\\end{tabular}\n"
    latex += "\\caption{Performance comparison of different models. Values shown as mean ± standard deviation.}\n"
    latex += "\\label{table:prediction-modelling}\n"
    latex += "\\end{table*}"

    return latex


def main():
    """
    Main function to aggregate and format the results.
    """
    print("Loading evaluation results...")
    results = load_evaluation_results()

    print("Creating results table...")
    results_table = create_results_table(results)

    print("Generating LaTeX table...")
    latex_table = generate_latex_table(results_table)

    print("\nResults Table:")
    print(results_table.to_string(index=False))

    print("\nLaTeX Table:")
    print(latex_table)

    # Save the LaTeX table to a file
    output_file = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "results_table.tex")
    with open(output_file, 'w') as f:
        f.write(latex_table)

    print(f"\nLaTeX table saved to {output_file}")


if __name__ == "__main__":
    main()
