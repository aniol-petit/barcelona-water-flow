"""
Silhouette score optimization to determine optimal k for KMeans.

Tests a range of k values and computes silhouette scores to find the optimal
number of clusters for Stage I KMeans clustering on physical features.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from .kmeans_physical import build_stage1_feature_matrix, DEFAULT_DB_PATH


def find_optimal_k(
    *,
    k_range: range | list[int] = range(2, 21),
    db_path: str | Path = DEFAULT_DB_PATH,
    random_state: int = 42,
    n_init: int = 10,
    max_iter: int = 300,
    verbose: bool = True,
) -> Tuple[int, dict[int, float], pd.DataFrame]:
    """
    Find optimal k for KMeans using silhouette score.

    Parameters
    ----------
    k_range:
        Range of k values to test. Default: range(2, 21) tests k from 2 to 20.
    db_path:
        Path to DuckDB database.
    random_state:
        Random seed for reproducibility.
    n_init:
        Number of KMeans initializations per k.
    max_iter:
        Maximum iterations for KMeans.
    verbose:
        If True, print progress and results.

    Returns
    -------
    tuple
        (optimal_k, scores_dict, results_df)
        - optimal_k: k value with highest silhouette score
        - scores_dict: dictionary mapping k -> silhouette_score
        - results_df: DataFrame with k, silhouette_score, and other metrics
    """
    # Load feature matrix
    if verbose:
        print("Loading feature matrix...")
    features, _, _, _ = build_stage1_feature_matrix(db_path=db_path)

    # Extract feature columns (exclude meter_id)
    feature_cols = [col for col in features.columns if col != "meter_id"]
    X = features[feature_cols].values

    if verbose:
        print(f"Feature matrix shape: {X.shape}")
        print(f"Testing k values: {list(k_range)}")
        print("-" * 60)

    scores = {}
    results = []

    for k in k_range:
        if verbose:
            print(f"Testing k={k}...", end=" ")

        # Fit KMeans
        kmeans = KMeans(
            n_clusters=k,
            random_state=random_state,
            n_init=n_init,
            max_iter=max_iter,
        )
        labels = kmeans.fit_predict(X)

        # Compute silhouette score
        score = silhouette_score(X, labels)
        scores[k] = score

        # Store results
        results.append(
            {
                "k": k,
                "silhouette_score": score,
                "inertia": kmeans.inertia_,
                "n_iter": kmeans.n_iter_,
            }
        )

        if verbose:
            print(f"silhouette_score = {score:.4f}")

    results_df = pd.DataFrame(results)

    # Find optimal k (highest silhouette score)
    optimal_k = results_df.loc[results_df["silhouette_score"].idxmax(), "k"]

    if verbose:
        print("-" * 60)
        print(f"\nOptimal k: {optimal_k}")
        print(f"Best silhouette score: {scores[optimal_k]:.4f}")
        print("\nTop 5 k values by silhouette score:")
        print(
            results_df.nlargest(5, "silhouette_score")[
                ["k", "silhouette_score"]
            ].to_string(index=False)
        )

    return optimal_k, scores, results_df


def plot_silhouette_scores(
    results_df: pd.DataFrame,
    save_path: str | Path | None = None,
) -> None:
    """
    Plot silhouette scores vs k values.

    Parameters
    ----------
    results_df:
        DataFrame from find_optimal_k() with columns: k, silhouette_score
    save_path:
        Optional path to save the plot. If None, displays interactively.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. Install with: pip install matplotlib"
        )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(results_df["k"], results_df["silhouette_score"], marker="o", linewidth=2)
    ax.axvline(
        results_df.loc[results_df["silhouette_score"].idxmax(), "k"],
        color="r",
        linestyle="--",
        label="Optimal k",
    )
    ax.set_xlabel("Number of clusters (k)", fontsize=12)
    ax.set_ylabel("Silhouette Score", fontsize=12)
    ax.set_title("Silhouette Score vs Number of Clusters (Stage I KMeans)", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Plot saved to: {save_path}")
    else:
        plt.show()


if __name__ == "__main__":
    # Find optimal k
    optimal_k, scores, results_df = find_optimal_k()

    # Plot results
    output_dir = Path(__file__).parent.parent
    plot_path = output_dir / "insights" / "stage1_silhouette_scores.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plot_silhouette_scores(results_df, save_path=plot_path)
