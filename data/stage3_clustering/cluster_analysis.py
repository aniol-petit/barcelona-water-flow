"""
Deep analysis and interpretation of clusters (average age, canya, diameter, model).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

# Import from stage1 to reuse physical features computation
try:
    from stage1_kmeans.kmeans_physical import (
        DEFAULT_DB_PATH,
        CURRENT_YEAR,
        compute_physical_features,
    )
except ImportError:
    # Handle direct execution
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stage1_kmeans.kmeans_physical import (
        DEFAULT_DB_PATH,
        CURRENT_YEAR,
        compute_physical_features,
    )


def load_cluster_labels(
    cluster_labels_path: str | Path,
) -> pd.DataFrame:
    """
    Load cluster labels from Stage 3 clustering.
    
    Parameters
    ----------
    cluster_labels_path : str or Path
        Path to CSV file with meter_id and cluster_label columns
        
    Returns
    -------
    pandas.DataFrame
        DataFrame with meter_id and cluster_label
    """
    cluster_labels_path = Path(cluster_labels_path)
    if not cluster_labels_path.exists():
        raise FileNotFoundError(f"Cluster labels file not found: {cluster_labels_path}")
    
    df = pd.read_csv(cluster_labels_path)
    
    if "meter_id" not in df.columns or "cluster_label" not in df.columns:
        raise ValueError("Cluster labels file must contain 'meter_id' and 'cluster_label' columns")
    
    return df


def compute_cluster_statistics(
    cluster_labels: pd.DataFrame,
    physical_features: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute comprehensive statistics for each cluster.
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    physical_features : pd.DataFrame
        DataFrame with meter_id, age, diameter, canya, brand_model
        
    Returns
    -------
    pandas.DataFrame
        Statistics per cluster
    """
    # Merge cluster labels with physical features
    merged = cluster_labels.merge(physical_features, on="meter_id", how="inner")
    
    # Group by cluster
    cluster_stats = []
    
    for cluster_id in sorted(merged["cluster_label"].unique()):
        cluster_data = merged[merged["cluster_label"] == cluster_id]
        n_meters = len(cluster_data)
        
        if n_meters == 0:
            continue
        
        # Numeric statistics
        stats_dict = {
            "cluster_id": cluster_id,
            "n_meters": n_meters,
            "percentage": 100 * n_meters / len(merged),
        }
        
        # Age statistics
        if "age" in cluster_data.columns:
            stats_dict.update({
                "age_mean": cluster_data["age"].mean(),
                "age_median": cluster_data["age"].median(),
                "age_std": cluster_data["age"].std(),
                "age_min": cluster_data["age"].min(),
                "age_max": cluster_data["age"].max(),
            })
        
        # Canya statistics
        if "canya" in cluster_data.columns:
            stats_dict.update({
                "canya_mean": cluster_data["canya"].mean(),
                "canya_median": cluster_data["canya"].median(),
                "canya_std": cluster_data["canya"].std(),
                "canya_min": cluster_data["canya"].min(),
                "canya_max": cluster_data["canya"].max(),
            })
        
        # Diameter statistics
        if "diameter" in cluster_data.columns:
            diameter_counts = cluster_data["diameter"].value_counts().to_dict()
            stats_dict["diameter_mode"] = cluster_data["diameter"].mode().iloc[0] if len(cluster_data["diameter"].mode()) > 0 else None
            stats_dict["diameter_distribution"] = diameter_counts
            
            # Add individual diameter counts
            for diam, count in diameter_counts.items():
                stats_dict[f"diameter_{int(diam)}_count"] = count
                stats_dict[f"diameter_{int(diam)}_pct"] = 100 * count / n_meters
        
        # Brand/Model statistics
        if "brand_model" in cluster_data.columns:
            brand_model_counts = cluster_data["brand_model"].value_counts().to_dict()
            stats_dict["brand_model_mode"] = cluster_data["brand_model"].mode().iloc[0] if len(cluster_data["brand_model"].mode()) > 0 else None
            stats_dict["brand_model_distribution"] = brand_model_counts
            
            # Top 3 brand/models
            top_brand_models = cluster_data["brand_model"].value_counts().head(3)
            for i, (bm, count) in enumerate(top_brand_models.items(), 1):
                stats_dict[f"top_brand_model_{i}"] = bm
                stats_dict[f"top_brand_model_{i}_count"] = count
                stats_dict[f"top_brand_model_{i}_pct"] = 100 * count / n_meters
        
        cluster_stats.append(stats_dict)
    
    stats_df = pd.DataFrame(cluster_stats)
    
    return stats_df


def analyze_cluster_characteristics(
    cluster_labels: pd.DataFrame,
    physical_features: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """
    Perform deep analysis of cluster characteristics.
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    physical_features : pd.DataFrame
        DataFrame with meter_id, age, diameter, canya, brand_model
        
    Returns
    -------
    dict
        Dictionary with various analysis DataFrames:
        - 'summary': Overall cluster statistics
        - 'age_analysis': Age distribution per cluster
        - 'canya_analysis': Canya distribution per cluster
        - 'diameter_analysis': Diameter distribution per cluster
        - 'brand_model_analysis': Brand/model distribution per cluster
        - 'detailed_stats': Detailed statistics per cluster
    """
    # Merge data
    merged = cluster_labels.merge(physical_features, on="meter_id", how="inner")
    
    results = {}
    
    # 1. Overall summary statistics
    summary = merged.groupby("cluster_label").agg({
        "meter_id": "count",
        "age": ["mean", "median", "std", "min", "max"],
        "canya": ["mean", "median", "std", "min", "max"],
        "diameter": ["mean", "median"],
    }).round(4)
    summary.columns = ["_".join(col).strip("_") for col in summary.columns.values]
    summary = summary.reset_index()
    
    # Compute mode separately (pandas groupby doesn't support mode in agg dict)
    diameter_mode = merged.groupby("cluster_label")["diameter"].apply(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else None)
    summary["diameter_mode"] = summary["cluster_label"].map(diameter_mode)
    
    summary["percentage"] = 100 * summary["meter_id_count"] / len(merged)
    results["summary"] = summary
    
    # 2. Age analysis
    age_analysis = merged.groupby("cluster_label")["age"].describe().reset_index()
    results["age_analysis"] = age_analysis
    
    # 3. Canya analysis
    canya_analysis = merged.groupby("cluster_label")["canya"].describe().reset_index()
    results["canya_analysis"] = canya_analysis
    
    # 4. Diameter distribution
    diameter_crosstab = pd.crosstab(merged["cluster_label"], merged["diameter"], normalize="index") * 100
    diameter_crosstab = diameter_crosstab.reset_index()
    results["diameter_analysis"] = diameter_crosstab
    
    # 5. Brand/Model distribution
    brand_model_crosstab = pd.crosstab(merged["cluster_label"], merged["brand_model"], normalize="index") * 100
    brand_model_crosstab = brand_model_crosstab.reset_index()
    results["brand_model_analysis"] = brand_model_crosstab
    
    # 6. Detailed statistics
    detailed_stats = compute_cluster_statistics(cluster_labels, physical_features)
    results["detailed_stats"] = detailed_stats
    
    return results


def identify_subcounting_patterns(
    cluster_labels: pd.DataFrame,
    physical_features: pd.DataFrame,
    canya_threshold: float | None = None,
    age_threshold: float | None = None,
) -> pd.DataFrame:
    """
    Identify clusters that may indicate subcounting behavior.
    
    Subcounting indicators:
    - High age (older meters more likely to malfunction)
    - Low canya (unexpectedly low consumption for age)
    - Specific brand/model combinations
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    physical_features : pd.DataFrame
        DataFrame with meter_id, age, diameter, canya, brand_model
    canya_threshold : float, optional
        Threshold below which canya is considered suspicious (default: 25th percentile)
    age_threshold : float, optional
        Threshold above which age is considered high (default: 75th percentile)
        
    Returns
    -------
    pandas.DataFrame
        Clusters ranked by subcounting risk
    """
    merged = cluster_labels.merge(physical_features, on="meter_id", how="inner")
    
    # Set default thresholds based on data distribution
    if canya_threshold is None:
        canya_threshold = merged["canya"].quantile(0.25)
    if age_threshold is None:
        age_threshold = merged["age"].quantile(0.75)
    
    # Compute risk score per cluster
    risk_scores = []
    
    for cluster_id in sorted(merged["cluster_label"].unique()):
        cluster_data = merged[merged["cluster_label"] == cluster_id]
        
        # Risk indicators
        pct_high_age = 100 * (cluster_data["age"] > age_threshold).sum() / len(cluster_data)
        pct_low_canya = 100 * (cluster_data["canya"] < canya_threshold).sum() / len(cluster_data)
        avg_age = cluster_data["age"].mean()
        avg_canya = cluster_data["canya"].mean()
        
        # Risk score (higher = more suspicious)
        # Weight: 40% age, 40% canya, 20% size (smaller clusters might be anomalies)
        risk_score = (
            0.4 * (pct_high_age / 100) +
            0.4 * (1 - pct_low_canya / 100) +  # Inverted: low canya = high risk
            0.2 * (1 - len(cluster_data) / len(merged))  # Smaller clusters = slightly higher risk
        )
        
        risk_scores.append({
            "cluster_id": cluster_id,
            "n_meters": len(cluster_data),
            "avg_age": avg_age,
            "avg_canya": avg_canya,
            "pct_high_age": pct_high_age,
            "pct_low_canya": pct_low_canya,
            "risk_score": risk_score,
        })
    
    risk_df = pd.DataFrame(risk_scores).sort_values("risk_score", ascending=False)
    
    return risk_df


def perform_statistical_tests(
    cluster_labels: pd.DataFrame,
    physical_features: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """
    Perform statistical tests to validate cluster differences.
    
    Tests:
    - ANOVA for age differences across clusters
    - ANOVA for canya differences across clusters
    - Chi-square tests for diameter and brand_model distributions
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    physical_features : pd.DataFrame
        DataFrame with meter_id, age, diameter, canya, brand_model
        
    Returns
    -------
    dict
        Dictionary with test results
    """
    merged = cluster_labels.merge(physical_features, on="meter_id", how="inner")
    
    results = {}
    
    # ANOVA for age
    age_groups = [group["age"].values for _, group in merged.groupby("cluster_label")]
    if len(age_groups) > 1 and all(len(g) > 1 for g in age_groups):
        f_stat_age, p_value_age = stats.f_oneway(*age_groups)
        results["age_anova"] = {
            "f_statistic": f_stat_age,
            "p_value": p_value_age,
            "significant": p_value_age < 0.05,
        }
    
    # ANOVA for canya
    canya_groups = [group["canya"].values for _, group in merged.groupby("cluster_label")]
    if len(canya_groups) > 1 and all(len(g) > 1 for g in canya_groups):
        f_stat_canya, p_value_canya = stats.f_oneway(*canya_groups)
        results["canya_anova"] = {
            "f_statistic": f_stat_canya,
            "p_value": p_value_canya,
            "significant": p_value_canya < 0.05,
        }
    
    # Chi-square for diameter
    diameter_crosstab = pd.crosstab(merged["cluster_label"], merged["diameter"])
    if diameter_crosstab.shape[0] > 1 and diameter_crosstab.shape[1] > 1:
        chi2_diam, p_diam, dof_diam, expected_diam = stats.chi2_contingency(diameter_crosstab)
        results["diameter_chi2"] = {
            "chi2_statistic": chi2_diam,
            "p_value": p_diam,
            "degrees_of_freedom": dof_diam,
            "significant": p_diam < 0.05,
        }
    
    # Chi-square for brand_model
    brand_model_crosstab = pd.crosstab(merged["cluster_label"], merged["brand_model"])
    if brand_model_crosstab.shape[0] > 1 and brand_model_crosstab.shape[1] > 1:
        chi2_bm, p_bm, dof_bm, expected_bm = stats.chi2_contingency(brand_model_crosstab)
        results["brand_model_chi2"] = {
            "chi2_statistic": chi2_bm,
            "p_value": p_bm,
            "degrees_of_freedom": dof_bm,
            "significant": p_bm < 0.05,
        }
    
    return results


def generate_cluster_report(
    cluster_labels: pd.DataFrame,
    db_path: str | Path = DEFAULT_DB_PATH,
    current_year: int = CURRENT_YEAR,
    output_dir: str | Path | None = None,
) -> Dict[str, pd.DataFrame | dict]:
    """
    Generate comprehensive cluster analysis report.
    
    Parameters
    ----------
    cluster_labels : pd.DataFrame
        DataFrame with meter_id and cluster_label
    db_path : str or Path
        Path to DuckDB database
    current_year : int
        Current year for age calculation
    output_dir : str or Path, optional
        Directory to save analysis results (if None, uses stage3_outputs/)
        
    Returns
    -------
    dict
        Dictionary with all analysis results
    """
    print("\n" + "=" * 80)
    print("STAGE 3: CLUSTER ANALYSIS")
    print("=" * 80)
    
    # Load physical features
    print("\nLoading physical features from database...")
    physical_features = compute_physical_features(db_path=db_path, current_year=current_year)
    print(f"  ✓ Loaded features for {len(physical_features):,} meters")
    
    # Perform comprehensive analysis
    print("\nPerforming cluster analysis...")
    analysis_results = analyze_cluster_characteristics(cluster_labels, physical_features)
    
    # Identify subcounting patterns
    print("\nIdentifying potential subcounting patterns...")
    subcounting_analysis = identify_subcounting_patterns(cluster_labels, physical_features)
    
    # Statistical tests
    print("\nPerforming statistical tests...")
    statistical_tests = perform_statistical_tests(cluster_labels, physical_features)
    
    # Compile all results
    report = {
        "summary": analysis_results["summary"],
        "age_analysis": analysis_results["age_analysis"],
        "canya_analysis": analysis_results["canya_analysis"],
        "diameter_analysis": analysis_results["diameter_analysis"],
        "brand_model_analysis": analysis_results["brand_model_analysis"],
        "detailed_stats": analysis_results["detailed_stats"],
        "subcounting_risk": subcounting_analysis,
        "statistical_tests": statistical_tests,
    }
    
    # Save results
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nSaving analysis results to {output_dir}...")
        
        # Save each DataFrame
        for key, value in report.items():
            if isinstance(value, pd.DataFrame):
                output_path = output_dir / f"cluster_analysis_{key}.csv"
                value.to_csv(output_path, index=False)
                print(f"  ✓ Saved {key} to {output_path}")
        
        # Save statistical tests as text
        if statistical_tests:
            stats_path = output_dir / "statistical_tests.txt"
            with open(stats_path, "w") as f:
                f.write("STATISTICAL TESTS RESULTS\n")
                f.write("=" * 80 + "\n\n")
                for test_name, test_results in statistical_tests.items():
                    f.write(f"{test_name.upper()}\n")
                    f.write("-" * 80 + "\n")
                    for stat_name, stat_value in test_results.items():
                        f.write(f"  {stat_name}: {stat_value}\n")
                    f.write("\n")
            print(f"  ✓ Saved statistical tests to {stats_path}")
    
    print("\n" + "=" * 80)
    print("CLUSTER ANALYSIS COMPLETE")
    print("=" * 80)
    
    return report
