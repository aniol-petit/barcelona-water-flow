"""
Risk scoring module for water meters.

Computes failure risk scores based on:
1. Intra-cluster anomaly distance (Euclidean distance to cluster centroid)
2. Cluster-level degradation (weighted combination of age and canya)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


def compute_intra_cluster_anomaly_scores(
    latent_vectors: np.ndarray,
    cluster_labels: np.ndarray,
    distance_metric: str = "euclidean",
) -> np.ndarray:
    """
    Compute anomaly scores based on distance to cluster centroids.

    Parameters
    ----------
    latent_vectors : np.ndarray
        Array of shape [n_meters, z_dim] containing latent representations.
    cluster_labels : np.ndarray
        Array of shape [n_meters] containing cluster assignments.
    distance_metric : str
        Distance metric to use. Options: 'euclidean', 'mahalanobis'.
        Default: 'euclidean'.

    Returns
    -------
    np.ndarray
        Normalized anomaly scores in [0, 1] for each meter.
    """
    n_meters, z_dim = latent_vectors.shape
    unique_clusters = np.unique(cluster_labels)
    distances = np.zeros(n_meters)

    if distance_metric == "euclidean":
        for cluster_id in unique_clusters:
            mask = cluster_labels == cluster_id
            cluster_points = latent_vectors[mask]
            centroid = np.mean(cluster_points, axis=0)
            
            # Compute Euclidean distance to centroid
            cluster_distances = np.linalg.norm(
                latent_vectors[mask] - centroid, axis=1
            )
            distances[mask] = cluster_distances

    elif distance_metric == "mahalanobis":
        for cluster_id in unique_clusters:
            mask = cluster_labels == cluster_id
            cluster_points = latent_vectors[mask]
            
            if len(cluster_points) < z_dim:
                # Fallback to Euclidean if not enough points for covariance
                centroid = np.mean(cluster_points, axis=0)
                distances[mask] = np.linalg.norm(
                    latent_vectors[mask] - centroid, axis=1
                )
            else:
                centroid = np.mean(cluster_points, axis=0)
                cov = np.cov(cluster_points.T)
                
                # Add small regularization to avoid singular matrix
                cov += np.eye(z_dim) * 1e-6
                inv_cov = np.linalg.inv(cov)
                
                # Compute Mahalanobis distance
                diff = latent_vectors[mask] - centroid
                mahal_distances = np.sqrt(
                    np.sum(diff @ inv_cov * diff, axis=1)
                )
                distances[mask] = mahal_distances
    else:
        raise ValueError(f"Unknown distance metric: {distance_metric}")

    # Normalize distances to [0, 1]
    d_min, d_max = distances.min(), distances.max()
    if d_max > d_min:
        normalized_scores = (distances - d_min) / (d_max - d_min)
    else:
        # All distances are the same
        normalized_scores = np.zeros(n_meters)

    return normalized_scores


def compute_cluster_degradation(
    df_physical: pd.DataFrame,
    cluster_labels: np.ndarray,
    alpha: float = 0.6,
    beta: float = 0.4,
) -> pd.Series:
    """
    Compute degradation index for each cluster based on age and canya.

    Parameters
    ----------
    df_physical : pd.DataFrame
        DataFrame with columns: meter_id, age, canya.
    cluster_labels : np.ndarray
        Array of cluster labels (from Stage 3 latent clustering) for each meter.
    alpha : float
        Weight for age component. Default: 0.6.
    beta : float
        Weight for canya component. Default: 0.4.

    Returns
    -------
    pd.Series
        Series indexed by cluster_id with degradation scores in [0, 1].
    """
    # Add cluster labels to dataframe
    df_merged = df_physical.copy()
    df_merged["cluster_label"] = cluster_labels
    
    # Normalize age and canya across all meters
    scaler_age = MinMaxScaler()
    scaler_canya = MinMaxScaler()
    
    age_normalized = scaler_age.fit_transform(
        df_merged[["age"]].values
    ).flatten()
    canya_normalized = scaler_canya.fit_transform(
        df_merged[["canya"]].values
    ).flatten()
    
    # Compute degradation per cluster
    cluster_degradation = {}
    
    for cluster_id in df_merged["cluster_label"].unique():
        mask = df_merged["cluster_label"] == cluster_id
        cluster_age = age_normalized[mask]
        cluster_canya = canya_normalized[mask]
        
        # Mean normalized age and canya for this cluster
        mean_age = np.mean(cluster_age)
        mean_canya = np.mean(cluster_canya)
        
        # Degradation index
        D_k = alpha * mean_age + beta * mean_canya
        cluster_degradation[cluster_id] = D_k
    
    # Normalize degradation scores across clusters to [0, 1]
    degradation_values = np.array(list(cluster_degradation.values()))
    d_min, d_max = degradation_values.min(), degradation_values.max()
    
    if d_max > d_min:
        normalized_degradation = {
            cluster_id: (D_k - d_min) / (d_max - d_min)
            for cluster_id, D_k in cluster_degradation.items()
        }
    else:
        normalized_degradation = {
            cluster_id: 0.0
            for cluster_id in cluster_degradation.keys()
        }
    
    return pd.Series(normalized_degradation)


def compute_risk_scores(
    latent_path: str | Path,
    cluster_labels_path: str | Path,
    physical_features_path: str | Path,
    output_path: Optional[str | Path] = None,
    w1: float = 0.5,
    w2: float = 0.5,
    alpha: float = 0.6,
    beta: float = 0.4,
    distance_metric: str = "euclidean",
) -> pd.DataFrame:
    """
    Compute failure risk scores for all meters.

    Parameters
    ----------
    latent_path : str | Path
        Path to latent_representations.csv.
    cluster_labels_path : str | Path
        Path to cluster_labels.csv.
    physical_features_path : str | Path
        Path to physical features CSV (must contain age, canya).
    output_path : str | Path, optional
        Path to save results. If None, returns DataFrame only.
    w1 : float
        Weight for anomaly score component. Default: 0.5.
    w2 : float
        Weight for cluster degradation component. Default: 0.5.
    alpha : float
        Weight for age in degradation calculation. Default: 0.6.
    beta : float
        Weight for canya in degradation calculation. Default: 0.4.
    distance_metric : str
        Distance metric for anomaly calculation. Default: 'euclidean'.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - meter_id
        - cluster_id
        - anomaly_score
        - cluster_degradation
        - risk_percent
    """
    # Load data
    print("Loading data...")
    df_latent = pd.read_csv(latent_path)
    df_clusters = pd.read_csv(cluster_labels_path)
    df_physical = pd.read_csv(physical_features_path)

    # Ensure meter_id alignment
    meter_ids = df_latent["meter_id"].values
    
    # Extract latent vectors (all columns except meter_id)
    z_cols = [col for col in df_latent.columns if col.startswith("z_")]
    latent_vectors = df_latent[z_cols].values
    
    # Get cluster labels aligned with latent vectors
    cluster_map = dict(zip(df_clusters["meter_id"], df_clusters["cluster_label"]))
    cluster_labels = np.array([cluster_map[mid] for mid in meter_ids])
    
    # Ensure physical features are aligned
    physical_map = df_physical.set_index("meter_id")
    df_physical_aligned = physical_map.loc[meter_ids].reset_index()
    
    # Step 1: Compute intra-cluster anomaly scores
    print("Step 1: Computing intra-cluster anomaly scores...")
    anomaly_scores = compute_intra_cluster_anomaly_scores(
        latent_vectors, cluster_labels, distance_metric=distance_metric
    )
    
    # Step 2: Compute cluster-level degradation
    print("Step 2: Computing cluster-level degradation...")
    cluster_degradation_map = compute_cluster_degradation(
        df_physical_aligned, cluster_labels, alpha=alpha, beta=beta
    )
    
    # Map degradation to each meter
    cluster_degradation_per_meter = np.array([
        cluster_degradation_map[cluster_id]
        for cluster_id in cluster_labels
    ])
    
    # Step 3: Combine individual and cluster risk
    print("Step 3: Combining anomaly and degradation scores...")
    combined_risk = w1 * anomaly_scores + w2 * cluster_degradation_per_meter
    
    # Normalize to [0, 1] then scale to percentage
    risk_min, risk_max = combined_risk.min(), combined_risk.max()
    if risk_max > risk_min:
        risk_normalized = (combined_risk - risk_min) / (risk_max - risk_min)
    else:
        risk_normalized = np.zeros_like(combined_risk)
    
    risk_percent = 100 * risk_normalized
    
    # Create output DataFrame
    df_results = pd.DataFrame({
        "meter_id": meter_ids,
        "cluster_id": cluster_labels,
        "anomaly_score": anomaly_scores,
        "cluster_degradation": cluster_degradation_per_meter,
        "risk_percent": risk_percent,
    })
    
    # Sort by risk (highest first)
    df_results = df_results.sort_values("risk_percent", ascending=False).reset_index(drop=True)
    
    # Save if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_results.to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")
    
    return df_results

