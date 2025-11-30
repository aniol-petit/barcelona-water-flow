"""
Visualization utilities for clusters, reconstructions, and latent space.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# Set style
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 8)


def plot_cluster_distribution(
    cluster_labels: pd.DataFrame,
    output_path: str | Path | None = None,
    title: str = "Cluster Distribution",
) -> None:
    """
    Plot the distribution of meters across clusters.
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    output_path : str or Path, optional
        Path to save the plot
    title : str
        Plot title
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Count plot
    cluster_counts = cluster_labels["cluster_label"].value_counts().sort_index()
    
    ax1.bar(cluster_counts.index.astype(str), cluster_counts.values, color="steelblue", alpha=0.7)
    ax1.set_xlabel("Cluster ID")
    ax1.set_ylabel("Number of Meters")
    ax1.set_title(f"{title} - Count")
    ax1.grid(axis="y", alpha=0.3)
    
    # Percentage plot
    percentages = 100 * cluster_counts / len(cluster_labels)
    ax2.bar(percentages.index.astype(str), percentages.values, color="coral", alpha=0.7)
    ax2.set_xlabel("Cluster ID")
    ax2.set_ylabel("Percentage (%)")
    ax2.set_title(f"{title} - Percentage")
    ax2.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved cluster distribution plot to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_latent_space_2d(
    latent_vectors: np.ndarray,
    cluster_labels: np.ndarray,
    method: str = "pca",
    output_path: str | Path | None = None,
    title: str = "Latent Space Visualization (2D)",
) -> None:
    """
    Visualize latent space in 2D using PCA or t-SNE.
    
    Parameters
    ----------
    latent_vectors : np.ndarray
        Latent representations (n_samples, n_features)
    cluster_labels : np.ndarray
        Cluster labels for each sample
    method : str
        Dimensionality reduction method: "pca" or "tsne"
    output_path : str or Path, optional
        Path to save the plot
    title : str
        Plot title
    """
    if method == "pca":
        reducer = PCA(n_components=2, random_state=42)
        reduced = reducer.fit_transform(latent_vectors)
        xlabel = f"PC1 ({100*reducer.explained_variance_ratio_[0]:.1f}% variance)"
        ylabel = f"PC2 ({100*reducer.explained_variance_ratio_[1]:.1f}% variance)"
    elif method == "tsne":
        reducer = TSNE(n_components=2, random_state=42, perplexity=30)
        reduced = reducer.fit_transform(latent_vectors)
        xlabel = "t-SNE Component 1"
        ylabel = "t-SNE Component 2"
    else:
        raise ValueError(f"Unknown method: {method}. Use 'pca' or 'tsne'")
    
    # Create scatter plot
    unique_clusters = np.unique(cluster_labels)
    colors = plt.cm.tab20(np.linspace(0, 1, len(unique_clusters)))
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    for i, cluster_id in enumerate(unique_clusters):
        mask = cluster_labels == cluster_id
        label = f"Cluster {cluster_id}" if cluster_id != -1 else "Noise"
        ax.scatter(
            reduced[mask, 0],
            reduced[mask, 1],
            c=[colors[i]],
            label=label,
            alpha=0.6,
            s=20,
        )
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved latent space visualization to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_cluster_features(
    cluster_labels: pd.DataFrame,
    physical_features: pd.DataFrame,
    feature_name: str,
    output_path: str | Path | None = None,
) -> None:
    """
    Plot distribution of a feature across clusters.
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    physical_features : pd.DataFrame
        DataFrame with meter_id and feature columns
    feature_name : str
        Name of the feature to plot (e.g., "age", "canya", "diameter")
    output_path : str or Path, optional
        Path to save the plot
    """
    merged = cluster_labels.merge(physical_features, on="meter_id", how="inner")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Box plot
    sns.boxplot(data=merged, x="cluster_label", y=feature_name, ax=ax1)
    ax1.set_title(f"{feature_name.capitalize()} Distribution by Cluster")
    ax1.set_xlabel("Cluster ID")
    ax1.set_ylabel(feature_name.capitalize())
    ax1.grid(axis="y", alpha=0.3)
    
    # Violin plot
    sns.violinplot(data=merged, x="cluster_label", y=feature_name, ax=ax2)
    ax2.set_title(f"{feature_name.capitalize()} Distribution by Cluster (Violin)")
    ax2.set_xlabel("Cluster ID")
    ax2.set_ylabel(feature_name.capitalize())
    ax2.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved {feature_name} distribution plot to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_brand_model_distribution(
    cluster_labels: pd.DataFrame,
    physical_features: pd.DataFrame,
    top_n: int = 10,
    output_path: str | Path | None = None,
) -> None:
    """
    Plot brand/model distribution across clusters.
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    physical_features : pd.DataFrame
        DataFrame with meter_id and brand_model
    top_n : int
        Number of top brand/models to show
    output_path : str or Path, optional
        Path to save the plot
    """
    merged = cluster_labels.merge(physical_features, on="meter_id", how="inner")
    
    # Get top N brand/models overall
    top_brand_models = merged["brand_model"].value_counts().head(top_n).index.tolist()
    
    # Create crosstab
    crosstab = pd.crosstab(merged["cluster_label"], merged["brand_model"])
    crosstab = crosstab[top_brand_models]  # Keep only top N
    
    # Normalize by cluster size
    crosstab_pct = crosstab.div(crosstab.sum(axis=1), axis=0) * 100
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    
    # Count heatmap
    sns.heatmap(crosstab, annot=True, fmt="d", cmap="YlOrRd", ax=ax1, cbar_kws={"label": "Count"})
    ax1.set_title("Brand/Model Distribution by Cluster (Count)")
    ax1.set_xlabel("Brand/Model")
    ax1.set_ylabel("Cluster ID")
    
    # Percentage heatmap
    sns.heatmap(crosstab_pct, annot=True, fmt=".1f", cmap="YlOrRd", ax=ax2, cbar_kws={"label": "Percentage (%)"})
    ax2.set_title("Brand/Model Distribution by Cluster (Percentage)")
    ax2.set_xlabel("Brand/Model")
    ax2.set_ylabel("Cluster ID")
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved brand/model distribution plot to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_subcounting_risk(
    subcounting_risk_df: pd.DataFrame,
    output_path: str | Path | None = None,
    top_n: int = 10,
) -> None:
    """
    Plot subcounting risk scores for clusters.
    
    Parameters
    ----------
    subcounting_risk_df : pd.DataFrame
        DataFrame with cluster_id, risk_score, and other metrics
    output_path : str or Path, optional
        Path to save the plot
    top_n : int
        Number of top clusters to show
    """
    top_risky = subcounting_risk_df.head(top_n)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Risk score bar plot
    axes[0, 0].barh(range(len(top_risky)), top_risky["risk_score"].values, color="crimson", alpha=0.7)
    axes[0, 0].set_yticks(range(len(top_risky)))
    axes[0, 0].set_yticklabels([f"Cluster {int(c)}" for c in top_risky["cluster_id"]])
    axes[0, 0].set_xlabel("Risk Score")
    axes[0, 0].set_title("Subcounting Risk Score (Top Clusters)")
    axes[0, 0].grid(axis="x", alpha=0.3)
    axes[0, 0].invert_yaxis()
    
    # Age vs Canya scatter
    axes[0, 1].scatter(top_risky["avg_age"], top_risky["avg_canya"], 
                       s=top_risky["n_meters"]*2, alpha=0.6, c=top_risky["risk_score"], 
                       cmap="Reds", edgecolors="black")
    axes[0, 1].set_xlabel("Average Age (years)")
    axes[0, 1].set_ylabel("Average Canya")
    axes[0, 1].set_title("Age vs Canya (Size = # Meters, Color = Risk)")
    axes[0, 1].grid(alpha=0.3)
    for _, row in top_risky.iterrows():
        axes[0, 1].annotate(f"C{int(row['cluster_id'])}", 
                           (row["avg_age"], row["avg_canya"]),
                           fontsize=8)
    
    # Percentage high age
    axes[1, 0].barh(range(len(top_risky)), top_risky["pct_high_age"].values, color="orange", alpha=0.7)
    axes[1, 0].set_yticks(range(len(top_risky)))
    axes[1, 0].set_yticklabels([f"Cluster {int(c)}" for c in top_risky["cluster_id"]])
    axes[1, 0].set_xlabel("Percentage (%)")
    axes[1, 0].set_title("Percentage of Meters with High Age")
    axes[1, 0].grid(axis="x", alpha=0.3)
    axes[1, 0].invert_yaxis()
    
    # Percentage low canya
    axes[1, 1].barh(range(len(top_risky)), top_risky["pct_low_canya"].values, color="purple", alpha=0.7)
    axes[1, 1].set_yticks(range(len(top_risky)))
    axes[1, 1].set_yticklabels([f"Cluster {int(c)}" for c in top_risky["cluster_id"]])
    axes[1, 1].set_xlabel("Percentage (%)")
    axes[1, 1].set_title("Percentage of Meters with Low Canya")
    axes[1, 1].grid(axis="x", alpha=0.3)
    axes[1, 1].invert_yaxis()
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved subcounting risk plot to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def create_comprehensive_visualization_report(
    cluster_labels: pd.DataFrame,
    latent_vectors: np.ndarray,
    physical_features: pd.DataFrame,
    subcounting_risk_df: pd.DataFrame,
    output_dir: str | Path,
) -> None:
    """
    Create a comprehensive visualization report for Stage 3.
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    latent_vectors : np.ndarray
        Latent representations
    physical_features : pd.DataFrame
        DataFrame with physical features
    subcounting_risk_df : pd.DataFrame
        DataFrame with subcounting risk analysis
    output_dir : str or Path
        Directory to save all plots
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nGenerating visualization report...")
    
    # 1. Cluster distribution
    plot_cluster_distribution(
        cluster_labels,
        output_path=output_dir / "cluster_distribution.png",
    )
    
    # 2. Latent space visualization (PCA)
    cluster_labels_array = cluster_labels["cluster_label"].values
    plot_latent_space_2d(
        latent_vectors,
        cluster_labels_array,
        method="pca",
        output_path=output_dir / "latent_space_pca.png",
    )
    
    # 3. Latent space visualization (t-SNE)
    plot_latent_space_2d(
        latent_vectors,
        cluster_labels_array,
        method="tsne",
        output_path=output_dir / "latent_space_tsne.png",
    )
    
    # 4. Feature distributions
    for feature in ["age", "canya", "diameter"]:
        if feature in physical_features.columns:
            plot_cluster_features(
                cluster_labels,
                physical_features,
                feature,
                output_path=output_dir / f"{feature}_distribution.png",
            )
    
    # 5. Brand/model distribution
    plot_brand_model_distribution(
        cluster_labels,
        physical_features,
        output_path=output_dir / "brand_model_distribution.png",
    )
    
    # 6. Subcounting risk
    plot_subcounting_risk(
        subcounting_risk_df,
        output_path=output_dir / "subcounting_risk.png",
    )
    
    print(f"\n  ✓ All visualizations saved to: {output_dir}")


def main():
    """
    Main function to generate all visualizations for Stage 3.
    Loads data from stage outputs and generates comprehensive visualization report.
    """
    import argparse
    import sys
    from pathlib import Path
    
    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
    try:
        from stage1_kmeans.kmeans_physical import (
            DEFAULT_DB_PATH,
            compute_physical_features,
        )
    except ImportError:
        print("Error: Could not import stage1_kmeans.kmeans_physical")
        print("Make sure you're running from the data directory")
        return
    
    # Get data directory (parent of utils)
    data_dir = Path(__file__).resolve().parent.parent
    
    parser = argparse.ArgumentParser(
        description="Generate comprehensive visualization report for Stage 3"
    )
    parser.add_argument(
        "--cluster-labels",
        type=str,
        default=None,
        help="Path to cluster_labels.csv (default: data/stage3_outputs/cluster_labels.csv)",
    )
    parser.add_argument(
        "--latent-representations",
        type=str,
        default=None,
        help="Path to latent_representations.csv (default: data/stage2_outputs/latent_representations.csv)",
    )
    parser.add_argument(
        "--subcounting-risk",
        type=str,
        default=None,
        help="Path to cluster_analysis_subcounting_risk.csv (default: data/stage3_outputs/cluster_analysis_subcounting_risk.csv)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to DuckDB database (default: data/analytics.duckdb)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save visualizations (default: data/stage3_outputs/visualizations)",
    )
    
    args = parser.parse_args()
    
    # Set default paths relative to data directory
    if args.cluster_labels is None:
        args.cluster_labels = data_dir / "stage3_outputs" / "cluster_labels.csv"
    else:
        args.cluster_labels = Path(args.cluster_labels)
    
    if args.latent_representations is None:
        args.latent_representations = data_dir / "stage2_outputs" / "latent_representations.csv"
    else:
        args.latent_representations = Path(args.latent_representations)
    
    if args.subcounting_risk is None:
        args.subcounting_risk = data_dir / "stage3_outputs" / "cluster_analysis_subcounting_risk.csv"
    else:
        args.subcounting_risk = Path(args.subcounting_risk)
    
    if args.db_path is None:
        args.db_path = data_dir / "analytics.duckdb"
    else:
        args.db_path = Path(args.db_path)
    
    if args.output_dir is None:
        args.output_dir = data_dir / "stage3_outputs" / "visualizations"
    else:
        args.output_dir = Path(args.output_dir)
    
    print("=" * 80)
    print("STAGE 3: VISUALIZATION REPORT GENERATION")
    print("=" * 80)
    
    # Load cluster labels
    print("\nLoading cluster labels...")
    print(f"  Looking for: {args.cluster_labels}")
    if not args.cluster_labels.exists():
        print(f"Error: Cluster labels file not found: {args.cluster_labels}")
        print(f"  Absolute path: {args.cluster_labels.resolve()}")
        return
    cluster_labels = pd.read_csv(args.cluster_labels)
    print(f"  ✓ Loaded {len(cluster_labels):,} cluster labels")
    
    # Load latent representations
    print("\nLoading latent representations...")
    print(f"  Looking for: {args.latent_representations}")
    if not args.latent_representations.exists():
        print(f"Error: Latent representations file not found: {args.latent_representations}")
        print(f"  Absolute path: {args.latent_representations.resolve()}")
        return
    latent_df = pd.read_csv(args.latent_representations)
    latent_cols = [col for col in latent_df.columns if col.startswith("z_")]
    latent_vectors = latent_df[latent_cols].values
    print(f"  ✓ Loaded {len(latent_df):,} latent vectors with {len(latent_cols)} dimensions")
    
    # Load physical features from database
    print("\nLoading physical features from database...")
    print(f"  Looking for: {args.db_path}")
    try:
        physical_features = compute_physical_features(db_path=args.db_path)
        print(f"  ✓ Loaded physical features for {len(physical_features):,} meters")
    except Exception as e:
        print(f"Error loading physical features: {e}")
        return
    
    # Load subcounting risk
    print("\nLoading subcounting risk analysis...")
    print(f"  Looking for: {args.subcounting_risk}")
    if not args.subcounting_risk.exists():
        print(f"Warning: Subcounting risk file not found: {args.subcounting_risk}")
        print("  Creating empty DataFrame...")
        subcounting_risk_df = pd.DataFrame(columns=["cluster_id", "risk_score", "n_meters", 
                                                     "avg_age", "avg_canya", "pct_high_age", "pct_low_canya"])
    else:
        subcounting_risk_df = pd.read_csv(args.subcounting_risk)
        print(f"  ✓ Loaded subcounting risk for {len(subcounting_risk_df)} clusters")
    
    # Ensure meter_id columns match
    if "meter_id" not in cluster_labels.columns:
        print("Error: cluster_labels must have 'meter_id' column")
        return
    
    if "meter_id" not in latent_df.columns:
        print("Error: latent_representations must have 'meter_id' column")
        return
    
    if "meter_id" not in physical_features.columns:
        print("Error: physical_features must have 'meter_id' column")
        return
    
    # Generate visualizations
    print("\n" + "=" * 80)
    print("GENERATING VISUALIZATIONS")
    print("=" * 80)
    
    output_dir = Path(args.output_dir)
    
    try:
        create_comprehensive_visualization_report(
            cluster_labels=cluster_labels,
            latent_vectors=latent_vectors,
            physical_features=physical_features,
            subcounting_risk_df=subcounting_risk_df,
            output_dir=output_dir,
        )
        print("\n" + "=" * 80)
        print("VISUALIZATION GENERATION COMPLETE")
        print("=" * 80)
        print(f"\nAll visualizations saved to: {output_dir.absolute()}")
    except Exception as e:
        print(f"\nError generating visualizations: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
