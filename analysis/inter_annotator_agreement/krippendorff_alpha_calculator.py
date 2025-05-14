"""
Krippendorff's Alpha Calculator

This script calculates Krippendorff's alpha for two annotators with arrays of length 10.
It provides a simple example and a function that can be reused for other arrays.
"""

from nltk.metrics import agreement
import numpy as np


def calculate_krippendorff_alpha(annotator1_ratings, annotator2_ratings):
    """
    Calculate Krippendorff's alpha for two annotators.

    Args:
        annotator1_ratings: List of ratings from the first annotator
        annotator2_ratings: List of ratings from the second annotator

    Returns:
        Krippendorff's alpha value
    """
    # Validate inputs
    if len(annotator1_ratings) != len(annotator2_ratings):
        raise ValueError(
            "Both annotators must have the same number of ratings")

    # Prepare data in the format required by NLTK's AnnotationTask
    # Format: [(coder, item, label), ...]
    data = []

    for i in range(len(annotator1_ratings)):
        data.append(("annotator1", f"item{i}", str(annotator1_ratings[i])))
        data.append(("annotator2", f"item{i}", str(annotator2_ratings[i])))

    # Create an AnnotationTask
    task = agreement.AnnotationTask(data=data)

    # Calculate Krippendorff's alpha
    try:
        alpha = task.alpha()
        return alpha
    except ValueError as e:
        print(f"Error calculating Krippendorff's alpha: {e}")
        return None


def main():
    """
    Example usage with two arrays of length 10 containing values of 1.
    """
    # Two annotators with arrays of length 10, all containing 1s
    annotator1 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    annotator2 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

    print("Annotator 1 ratings:", annotator1)
    print("Annotator 2 ratings:", annotator2)

    # Calculate Krippendorff's alpha
    alpha = calculate_krippendorff_alpha(annotator1, annotator2)

    if alpha is not None:
        print(f"Krippendorff's alpha: {alpha:.4f}")

        # Interpret the result
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

    # Example with some disagreement
    print("\n--- Example with some disagreement ---")
    annotator1_mixed = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    annotator2_mixed = [1, 1, 1, 1, 1, 1, 1, 1, 1, 0]  # Two different values

    print("Annotator 1 ratings:", annotator1_mixed)
    print("Annotator 2 ratings:", annotator2_mixed)

    alpha_mixed = calculate_krippendorff_alpha(
        annotator1_mixed, annotator2_mixed)

    if alpha_mixed is not None:
        print(f"Krippendorff's alpha: {alpha_mixed:.4f}")


if __name__ == "__main__":
    main()
