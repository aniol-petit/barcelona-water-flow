"""
Main script to run Stage 3: Clustering on latent space and cluster analysis.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Handle both module import and direct execution
try:
    from .cluster_analysis import generate_cluster_report
    from .latent_clustering import cluster_latent_space, DEFAULT_LATENT_PATH
except ImportError:
    # When run directly, add parent directory to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stage3_clustering.cluster_analysis import generate_cluster_report
    from stage3_clustering.latent_clustering import cluster_latent_space, DEFAULT_LATENT_PATH

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "stage3_outputs"
DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Stage 3: Cluster latent space and perform deep analysis"
    )
    
    # Clustering parameters
    parser.add_argument(
        "--latent-path",
        type=str,
        default=str(DEFAULT_LATENT_PATH),
        help="Path to latent_representations.csv from Stage 2",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["kmeans", "dbscan"],
        default="kmeans",
        help="Clustering method: kmeans or dbscan",
    )
    parser.add_argument(
        "--n-clusters",
        type=int,
        default=8,
        help="Number of clusters for KMeans (default: 8)",
    )
    parser.add_argument(
        "--auto-optimize",
        action="store_true",
        help="Enable automatic k optimization using silhouette score",
    )
    parser.add_argument(
        "--k-range",
        type=str,
        default="2-20",
        help="Range of k values to test (format: start-end, e.g., '2-20')",
    )
    parser.add_argument(
        "--dbscan-eps",
        type=float,
        default=0.5,
        help="Epsilon parameter for DBSCAN",
    )
    parser.add_argument(
        "--dbscan-min-samples",
        type=int,
        default=5,
        help="Min samples parameter for DBSCAN",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    
    # Analysis parameters
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to DuckDB database (default: data/analytics.duckdb)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to save analysis results",
    )
    parser.add_argument(
        "--no-save-model",
        action="store_true",
        help="Don't save the clustering model",
    )
    
    args = parser.parse_args()
    
    # Parse k-range
    if "-" in args.k_range:
        k_start, k_end = map(int, args.k_range.split("-"))
        k_range = range(k_start, k_end + 1)
    else:
        k_range = range(2, 21)
    
    # Set default DB path
    if args.db_path is None:
        args.db_path = Path(__file__).resolve().parents[1] / "analytics.duckdb"
    
    # If auto-optimize is enabled, ignore n_clusters (set to None)
    n_clusters_for_clustering = None if args.auto_optimize else args.n_clusters
    
    print("=" * 80)
    print("STAGE 3: LATENT SPACE CLUSTERING AND ANALYSIS")
    print("=" * 80)
    if args.auto_optimize:
        print(f"\nAuto-optimization enabled: Will test k values from {k_range.start} to {k_range.stop-1}")
    else:
        print(f"\nUsing fixed number of clusters: {args.n_clusters}")
    
    # Step 1: Perform clustering
    print("\n" + "-" * 80)
    print("STEP 1: Clustering Latent Space")
    print("-" * 80)
    
    cluster_labels_df, clustering_model = cluster_latent_space(
        latent_path=args.latent_path,
        method=args.method,
        n_clusters=n_clusters_for_clustering,
        auto_optimize_k=args.auto_optimize,
        k_range=k_range,
        dbscan_eps=args.dbscan_eps,
        dbscan_min_samples=args.dbscan_min_samples,
        save_model=not args.no_save_model,
        models_dir=DEFAULT_MODELS_DIR,
        random_state=args.random_state,
    )
    
    # Save cluster labels
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cluster_labels_path = output_dir / "cluster_labels.csv"
    cluster_labels_df.to_csv(cluster_labels_path, index=False)
    print(f"\n  ✓ Saved cluster labels to: {cluster_labels_path}")
    
    # Step 2: Deep cluster analysis
    print("\n" + "-" * 80)
    print("STEP 2: Deep Cluster Analysis")
    print("-" * 80)
    
    report = generate_cluster_report(
        cluster_labels=cluster_labels_df,
        db_path=args.db_path,
        output_dir=output_dir,
    )
    
    # Print summary
    print("\n" + "-" * 80)
    print("CLUSTERING SUMMARY")
    print("-" * 80)
    print(f"\nTotal meters clustered: {len(cluster_labels_df):,}")
    print(f"Number of clusters: {cluster_labels_df['cluster_label'].nunique()}")
    print(f"\nCluster distribution:")
    cluster_counts = cluster_labels_df["cluster_label"].value_counts().sort_index()
    for cluster_id, count in cluster_counts.items():
        pct = 100 * count / len(cluster_labels_df)
        print(f"  Cluster {cluster_id}: {count:,} meters ({pct:.2f}%)")
    
    # Print subcounting risk summary
    if "subcounting_risk" in report:
        print("\n" + "-" * 80)
        print("TOP 5 CLUSTERS BY SUBCountING RISK")
        print("-" * 80)
        top_risky = report["subcounting_risk"].head(5)
        for _, row in top_risky.iterrows():
            print(f"\nCluster {int(row['cluster_id'])}:")
            print(f"  Risk Score: {row['risk_score']:.4f}")
            print(f"  Meters: {int(row['n_meters']):,}")
            print(f"  Avg Age: {row['avg_age']:.2f} years")
            print(f"  Avg Canya: {row['avg_canya']:.2f}")
            print(f"  % High Age: {row['pct_high_age']:.2f}%")
            print(f"  % Low Canya: {row['pct_low_canya']:.2f}%")
    
    print("\n" + "=" * 80)
    print("STAGE 3 COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()

