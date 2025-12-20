"""
Main script to run Stage 4: Risk Probability Scoring.

Computes failure risk scores (0-100) for each meter based on:
1. Intra-cluster anomaly distance
2. Cluster-level degradation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Handle both module import and direct execution
try:
    from .risk_scoring import compute_risk_scores
    from .visualization import (
        generate_summary_statistics,
        plot_risk_distribution_by_cluster,
        plot_risk_vs_features,
        plot_top_risk_meters,
    )
except ImportError:
    # When run directly, add parent directory to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stage4_risk_probabilities.risk_scoring import compute_risk_scores
    from stage4_risk_probabilities.visualization import (
        generate_summary_statistics,
        plot_risk_distribution_by_cluster,
        plot_risk_vs_features,
        plot_top_risk_meters,
    )

# Default paths
DEFAULT_LATENT_PATH = Path(__file__).resolve().parents[1] / "stage2_outputs" / "latent_representations.csv"
DEFAULT_CLUSTER_PATH = Path(__file__).resolve().parents[1] / "stage3_outputs" / "cluster_labels.csv"
DEFAULT_PHYSICAL_PATH = Path(__file__).resolve().parents[1] / "stage1_outputs" / "stage1_physical_features_with_clusters.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "stage4_outputs"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "analytics.duckdb"


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Stage 4: Compute failure risk scores for water meters"
    )
    
    # Input paths
    parser.add_argument(
        "--latent-path",
        type=str,
        default=str(DEFAULT_LATENT_PATH),
        help="Path to latent_representations.csv from Stage 2",
    )
    parser.add_argument(
        "--cluster-path",
        type=str,
        default=str(DEFAULT_CLUSTER_PATH),
        help="Path to cluster_labels.csv from Stage 3",
    )
    parser.add_argument(
        "--physical-path",
        type=str,
        default=str(DEFAULT_PHYSICAL_PATH),
        help="Path to physical features CSV with age, canya (cluster_label from Stage 3 will be used)",
    )
    
    # Output paths
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to save outputs",
    )
    
    # Risk scoring parameters
    parser.add_argument(
        "--w1",
        type=float,
        default=0.5,
        help="Weight for anomaly score component (default: 0.5)",
    )
    parser.add_argument(
        "--w2",
        type=float,
        default=0.5,
        help="Weight for cluster degradation component (default: 0.5)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.6,
        help="Weight for age in degradation calculation (default: 0.6)",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=0.4,
        help="Weight for canya in degradation calculation (default: 0.4)",
    )
    parser.add_argument(
        "--distance-metric",
        type=str,
        choices=["euclidean", "mahalanobis"],
        default="euclidean",
        help="Distance metric for anomaly calculation (default: euclidean)",
    )
    parser.add_argument(
        "--disable-subcounting",
        action="store_true",
        help="Disable subcounting integration (by default it is enabled).",
    )
    parser.add_argument(
        "--subcount-gamma",
        type=float,
        default=0.8,
        help="Maximum additional independent failure probability contributed by subcounting (0-1, default: 0.8).",
    )
    parser.add_argument(
        "--subcount-use-cluster-peers",
        action="store_true",
        help="Use cluster-wise peers for subcounting normalisation instead of global peers.",
    )
    parser.add_argument(
        "--subcount-db-path",
        type=str,
        default=str(DEFAULT_DB_PATH),
        help="Path to DuckDB analytics database for subcounting (default: data/analytics.duckdb).",
    )
    
    # Visualization parameters
    parser.add_argument(
        "--top-percent",
        type=float,
        default=10.0,
        help="Percentage of top meters to highlight (default: 10.0)",
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization generation",
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    viz_dir = output_dir / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("STAGE 4: RISK PROBABILITY SCORING")
    print("=" * 80)
    print(f"\nInput files:")
    print(f"  Latent representations: {args.latent_path}")
    print(f"  Cluster labels: {args.cluster_path}")
    print(f"  Physical features: {args.physical_path}")
    print(f"\nOutput directory: {output_dir}")
    print(f"\nParameters:")
    print(f"  w1 (anomaly weight): {args.w1}")
    print(f"  w2 (degradation weight): {args.w2}")
    print(f"  alpha (age weight): {args.alpha}")
    print(f"  beta (canya weight): {args.beta}")
    print(f"  Distance metric: {args.distance_metric}")
    print(f"  Subcounting enabled: {not args.disable_subcounting}")
    print(f"  Subcount gamma: {args.subcount_gamma}")
    print(f"  Subcount use cluster peers: {args.subcount_use_cluster_peers}")
    print(f"  Subcount DB path: {args.subcount_db_path}")
    print("=" * 80)
    
    # Compute risk scores
    df_results = compute_risk_scores(
        latent_path=args.latent_path,
        cluster_labels_path=args.cluster_path,
        physical_features_path=args.physical_path,
        output_path=output_dir / "meter_failure_risk.csv",
        w1=args.w1,
        w2=args.w2,
        alpha=args.alpha,
        beta=args.beta,
        distance_metric=args.distance_metric,
        enable_subcounting=not args.disable_subcounting,
        subcount_gamma=args.subcount_gamma,
        use_subcount_cluster_peers=args.subcount_use_cluster_peers,
        subcount_db_path=args.subcount_db_path,
    )
    
    print(f"\n✓ Risk scores computed for {len(df_results):,} meters")
    print(f"\n  Base Risk (anomaly + degradation):")
    print(f"    Range: {df_results['risk_percent_base'].min():.2f}% - {df_results['risk_percent_base'].max():.2f}%")
    print(f"    Mean: {df_results['risk_percent_base'].mean():.2f}%")
    print(f"    Median: {df_results['risk_percent_base'].median():.2f}%")
    if "subcount_percent" in df_results.columns:
        print(f"\n  Subcounting Probability:")
        print(f"    Range: {df_results['subcount_percent'].min():.2f}% - {df_results['subcount_percent'].max():.2f}%")
        print(f"    Mean: {df_results['subcount_percent'].mean():.2f}%")
        print(f"    Median: {df_results['subcount_percent'].median():.2f}%")
    print(f"\n  Final Combined Risk:")
    print(f"    Range: {df_results['risk_percent'].min():.2f}% - {df_results['risk_percent'].max():.2f}%")
    print(f"    Mean: {df_results['risk_percent'].mean():.2f}%")
    print(f"    Median: {df_results['risk_percent'].median():.2f}%")
    
    # Generate summary statistics
    print("\nGenerating summary statistics...")
    df_summary = generate_summary_statistics(
        df_results,
        output_path=output_dir / "risk_summary_by_cluster.csv",
    )
    print(df_summary.to_string(index=False))
    
    # Visualizations
    if not args.no_viz:
        print("\nGenerating visualizations...")
        
        # Load physical features for visualization
        df_physical = pd.read_csv(args.physical_path)
        
        # Risk distribution by cluster
        plot_risk_distribution_by_cluster(
            df_results,
            output_path=viz_dir / "risk_distribution_by_cluster.png",
        )
        
        # Top risk meters
        plot_top_risk_meters(
            df_results,
            top_percent=args.top_percent,
            output_path=viz_dir / f"top_{args.top_percent}_percent_risk_meters.png",
        )
        
        # Risk vs features
        plot_risk_vs_features(
            df_results,
            df_physical,
            output_path=viz_dir / "risk_vs_features.png",
        )
        
        print(f"✓ Visualizations saved to: {viz_dir}")
    
    # Print top 20 highest-risk meters
    print("\n" + "=" * 80)
    print("TOP 20 HIGHEST-RISK METERS")
    print("=" * 80)
    display_cols = ["meter_id", "cluster_id", "risk_percent_base", "subcount_percent", "risk_percent"]
    # Only show subcount_percent if subcounting was enabled
    if "subcount_percent" not in df_results.columns:
        display_cols = [c for c in display_cols if c != "subcount_percent"]
    top_20 = df_results.head(20)[display_cols]
    print(top_20.to_string(index=False))
    
    print("\n" + "=" * 80)
    print("STAGE 4 COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\nOutput files:")
    print(f"  1. {output_dir / 'meter_failure_risk.csv'} - Full risk scores")
    print(f"  2. {output_dir / 'risk_summary_by_cluster.csv'} - Summary statistics")
    if not args.no_viz:
        print(f"  3. {viz_dir / 'risk_distribution_by_cluster.png'} - Distribution plots")
        print(f"  4. {viz_dir / f'top_{args.top_percent}_percent_risk_meters.png'} - Top risk meters")
        print(f"  5. {viz_dir / 'risk_vs_features.png'} - Risk vs features")


if __name__ == "__main__":
    main()

