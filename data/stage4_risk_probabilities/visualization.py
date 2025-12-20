"""
Visualization utilities for risk scoring results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Set style
sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 150


def plot_risk_distribution_by_cluster(
    df_results: pd.DataFrame,
    output_path: Optional[str | Path] = None,
    figsize: tuple[int, int] = (14, 8),
) -> None:
    """
    Plot distribution of risk scores by cluster.

    Parameters
    ----------
    df_results : pd.DataFrame
        DataFrame with columns: meter_id, cluster_id, risk_percent.
    output_path : str | Path, optional
        Path to save figure. If None, displays plot.
    figsize : tuple
        Figure size. Default: (14, 8).
    """
    fig, axes = plt.subplots(2, 1, figsize=figsize)
    
    # Box plot
    sns.boxplot(
        data=df_results,
        x="cluster_id",
        y="risk_percent",
        ax=axes[0],
        hue="cluster_id",
        palette="Set2",
        legend=False,
    )
    axes[0].set_title("Risk Score Distribution by Cluster (Box Plot)", fontsize=14, fontweight="bold")
    axes[0].set_xlabel("Cluster ID", fontsize=12)
    axes[0].set_ylabel("Risk Score (%)", fontsize=12)
    axes[0].grid(True, alpha=0.3)
    
    # Violin plot
    sns.violinplot(
        data=df_results,
        x="cluster_id",
        y="risk_percent",
        ax=axes[1],
        hue="cluster_id",
        palette="Set2",
        legend=False,
    )
    axes[1].set_title("Risk Score Distribution by Cluster (Violin Plot)", fontsize=14, fontweight="bold")
    axes[1].set_xlabel("Cluster ID", fontsize=12)
    axes[1].set_ylabel("Risk Score (%)", fontsize=12)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches="tight", dpi=150)
        print(f"Saved plot to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_top_risk_meters(
    df_results: pd.DataFrame,
    top_percent: float = 10.0,
    output_path: Optional[str | Path] = None,
    figsize: tuple[int, int] = (14, 8),
) -> None:
    """
    Highlight top N% highest-risk meters.

    Parameters
    ----------
    df_results : pd.DataFrame
        DataFrame with columns: meter_id, cluster_id, risk_percent.
    top_percent : float
        Percentage of top meters to highlight. Default: 10.0.
    output_path : str | Path, optional
        Path to save figure. If None, displays plot.
    figsize : tuple
        Figure size. Default: (14, 8).
    """
    n_top = int(len(df_results) * top_percent / 100)
    top_meters = df_results.head(n_top)
    
    fig, axes = plt.subplots(2, 1, figsize=figsize)
    
    # Overall distribution with top meters highlighted
    axes[0].hist(
        df_results["risk_percent"],
        bins=50,
        alpha=0.6,
        color="lightblue",
        edgecolor="black",
        label="All meters",
    )
    axes[0].hist(
        top_meters["risk_percent"],
        bins=50,
        alpha=0.8,
        color="red",
        edgecolor="black",
        label=f"Top {top_percent}%",
    )
    axes[0].axvline(
        top_meters["risk_percent"].min(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Threshold ({top_meters['risk_percent'].min():.2f}%)",
    )
    axes[0].set_title(f"Risk Score Distribution (Top {top_percent}% Highlighted)", fontsize=14, fontweight="bold")
    axes[0].set_xlabel("Risk Score (%)", fontsize=12)
    axes[0].set_ylabel("Number of Meters", fontsize=12)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Top meters by cluster
    cluster_counts = top_meters["cluster_id"].value_counts().sort_index()
    cluster_counts_all = df_results["cluster_id"].value_counts().sort_index()
    
    # Ensure we have all clusters (fill missing with 0)
    cluster_counts = cluster_counts.reindex(cluster_counts_all.index, fill_value=0)
    cluster_pct = (cluster_counts / cluster_counts_all * 100).fillna(0)
    
    bars = axes[1].bar(
        cluster_counts_all.index.astype(str),
        cluster_pct.values,
        color="coral",
        edgecolor="black",
        alpha=0.8,
    )
    axes[1].set_title(f"Top {top_percent}% High-Risk Meters by Cluster", fontsize=14, fontweight="bold")
    axes[1].set_xlabel("Cluster ID", fontsize=12)
    axes[1].set_ylabel(f"% of Cluster in Top {top_percent}%", fontsize=12)
    axes[1].grid(True, alpha=0.3, axis="y")
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        axes[1].text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    
    plt.tight_layout()
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches="tight", dpi=150)
        print(f"Saved plot to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_risk_vs_features(
    df_results: pd.DataFrame,
    df_physical: pd.DataFrame,
    output_path: Optional[str | Path] = None,
    figsize: tuple[int, int] = (16, 10),
) -> None:
    """
    Plot risk scores vs physical features (age, canya, diameter).

    Parameters
    ----------
    df_results : pd.DataFrame
        DataFrame with columns: meter_id, risk_percent.
    df_physical : pd.DataFrame
        DataFrame with columns: meter_id, age, canya, diameter.
    output_path : str | Path, optional
        Path to save figure. If None, displays plot.
    figsize : tuple
        Figure size. Default: (16, 10).
    """
    # Merge data
    df_merged = df_results.merge(
        df_physical[["meter_id", "age", "canya", "diameter"]],
        on="meter_id",
        how="left",
    )
    
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    axes = axes.flatten()
    
    # Risk vs Age
    axes[0].scatter(
        df_merged["age"],
        df_merged["risk_percent"],
        alpha=0.5,
        s=20,
        color="steelblue",
    )
    axes[0].set_xlabel("Age (years)", fontsize=12)
    axes[0].set_ylabel("Risk Score (%)", fontsize=12)
    axes[0].set_title("Risk Score vs Age", fontsize=13, fontweight="bold")
    axes[0].grid(True, alpha=0.3)
    
    # Risk vs Canya
    axes[1].scatter(
        df_merged["canya"],
        df_merged["risk_percent"],
        alpha=0.5,
        s=20,
        color="coral",
    )
    axes[1].set_xlabel("Canya", fontsize=12)
    axes[1].set_ylabel("Risk Score (%)", fontsize=12)
    axes[1].set_title("Risk Score vs Canya", fontsize=13, fontweight="bold")
    axes[1].grid(True, alpha=0.3)
    
    # Risk vs Diameter
    diameter_counts = df_merged["diameter"].value_counts().sort_index()
    diameter_risk = df_merged.groupby("diameter")["risk_percent"].mean().sort_index()
    
    axes[2].bar(
        diameter_counts.index.astype(str),
        diameter_risk.values,
        color="mediumseagreen",
        edgecolor="black",
        alpha=0.8,
    )
    axes[2].set_xlabel("Diameter (mm)", fontsize=12)
    axes[2].set_ylabel("Average Risk Score (%)", fontsize=12)
    axes[2].set_title("Average Risk Score by Diameter", fontsize=13, fontweight="bold")
    axes[2].grid(True, alpha=0.3, axis="y")
    
    # Risk distribution histogram
    axes[3].hist(
        df_merged["risk_percent"],
        bins=50,
        color="purple",
        alpha=0.7,
        edgecolor="black",
    )
    axes[3].axvline(
        df_merged["risk_percent"].median(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Median: {df_merged['risk_percent'].median():.2f}%",
    )
    axes[3].set_xlabel("Risk Score (%)", fontsize=12)
    axes[3].set_ylabel("Number of Meters", fontsize=12)
    axes[3].set_title("Overall Risk Score Distribution", fontsize=13, fontweight="bold")
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches="tight", dpi=150)
        print(f"Saved plot to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def generate_summary_statistics(
    df_results: pd.DataFrame,
    output_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Generate summary statistics by cluster.

    Parameters
    ----------
    df_results : pd.DataFrame
        DataFrame with columns: meter_id, cluster_id, anomaly_score, cluster_degradation, risk_percent.
    output_path : str | Path, optional
        Path to save summary CSV. If None, returns DataFrame only.

    Returns
    -------
    pd.DataFrame
        Summary statistics by cluster.
    """
    # Build aggregation dictionary based on available columns
    agg_dict = {
        "meter_id": "count",
        "risk_percent": ["mean", "std", "min", "max", "median"],
        "anomaly_score": ["mean", "std"],
        "cluster_degradation": "first",  # Same for all meters in cluster
    }
    
    # Add base risk and subcounting if available
    if "risk_percent_base" in df_results.columns:
        agg_dict["risk_percent_base"] = ["mean", "std", "min", "max", "median"]
    if "subcount_percent" in df_results.columns:
        agg_dict["subcount_percent"] = ["mean", "std", "min", "max", "median"]
    
    summary = df_results.groupby("cluster_id").agg(agg_dict).round(4)
    
    # Flatten column names
    col_names = ["n_meters", "risk_mean", "risk_std", "risk_min", "risk_max", "risk_median"]
    if "risk_percent_base" in agg_dict:
        col_names.extend(["risk_base_mean", "risk_base_std", "risk_base_min", "risk_base_max", "risk_base_median"])
    if "subcount_percent" in agg_dict:
        col_names.extend(["subcount_mean", "subcount_std", "subcount_min", "subcount_max", "subcount_median"])
    col_names.extend(["anomaly_mean", "anomaly_std", "cluster_degradation"])
    
    summary.columns = col_names
    
    summary = summary.reset_index()
    summary = summary.sort_values("risk_mean", ascending=False)
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(output_path, index=False)
        print(f"Summary statistics saved to: {output_path}")
    
    return summary

