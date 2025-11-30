"""
KMeans or DBSCAN clustering on latent vectors from autoencoder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

DEFAULT_LATENT_PATH = Path(__file__).resolve().parents[1] / "stage2_outputs" / "latent_representations.csv"
DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def load_latent_representations(
    latent_path: str | Path = DEFAULT_LATENT_PATH,
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Load latent representations from Stage 2 output.
    
    Parameters
    ----------
    latent_path : str or Path
        Path to latent_representations.csv file
        
    Returns
    -------
    tuple
        (DataFrame with meter_id and latent vectors, numpy array of latent vectors)
    """
    latent_path = Path(latent_path)
    if not latent_path.exists():
        raise FileNotFoundError(f"Latent representations file not found: {latent_path}")
    
    df = pd.read_csv(latent_path)
    
    # Extract meter IDs and latent vectors
    meter_ids = df["meter_id"].values
    latent_cols = [col for col in df.columns if col.startswith("z_")]
    latent_vectors = df[latent_cols].values
    
    print(f"Loaded {len(df):,} latent representations with {len(latent_cols)} dimensions")
    
    return df, latent_vectors


def perform_kmeans_clustering(
    latent_vectors: np.ndarray,
    n_clusters: int = 8,
    random_state: int = 42,
    n_init: int = 10,
    max_iter: int = 300,
) -> Tuple[KMeans, np.ndarray]:
    """
    Perform KMeans clustering on latent vectors.
    
    Parameters
    ----------
    latent_vectors : np.ndarray
        Latent representations (n_samples, n_features)
    n_clusters : int
        Number of clusters
    random_state : int
        Random seed for reproducibility
    n_init : int
        Number of times KMeans will be run with different centroid seeds
    max_iter : int
        Maximum number of iterations
        
    Returns
    -------
    tuple
        (Fitted KMeans model, cluster labels)
    """
    print(f"\nPerforming KMeans clustering with k={n_clusters}...")
    
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=n_init,
        max_iter=max_iter,
        verbose=1,
    )
    
    labels = kmeans.fit_predict(latent_vectors)
    
    # Compute evaluation metrics
    silhouette = silhouette_score(latent_vectors, labels)
    calinski_harabasz = calinski_harabasz_score(latent_vectors, labels)
    davies_bouldin = davies_bouldin_score(latent_vectors, labels)
    
    print(f"  ✓ Clustering complete")
    print(f"  - Silhouette score: {silhouette:.4f}")
    print(f"  - Calinski-Harabasz score: {calinski_harabasz:.2f}")
    print(f"  - Davies-Bouldin score: {davies_bouldin:.4f}")
    print(f"  - Cluster sizes: {np.bincount(labels)}")
    
    return kmeans, labels


def perform_dbscan_clustering(
    latent_vectors: np.ndarray,
    eps: float = 0.5,
    min_samples: int = 5,
    metric: str = "euclidean",
) -> Tuple[DBSCAN, np.ndarray]:
    """
    Perform DBSCAN clustering on latent vectors.
    
    Parameters
    ----------
    latent_vectors : np.ndarray
        Latent representations (n_samples, n_features)
    eps : float
        Maximum distance between samples to be considered neighbors
    min_samples : int
        Minimum number of samples in a neighborhood for a point to be a core point
    metric : str
        Distance metric to use
        
    Returns
    -------
    tuple
        (Fitted DBSCAN model, cluster labels where -1 indicates noise)
    """
    print(f"\nPerforming DBSCAN clustering with eps={eps}, min_samples={min_samples}...")
    
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric=metric)
    labels = dbscan.fit_predict(latent_vectors)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    print(f"  ✓ Clustering complete")
    print(f"  - Number of clusters: {n_clusters}")
    print(f"  - Number of noise points: {n_noise:,} ({100*n_noise/len(labels):.2f}%)")
    
    if n_clusters > 0:
        # Compute metrics only for non-noise points
        non_noise_mask = labels != -1
        if non_noise_mask.sum() > 1:
            silhouette = silhouette_score(latent_vectors[non_noise_mask], labels[non_noise_mask])
            print(f"  - Silhouette score (excluding noise): {silhouette:.4f}")
    
    return dbscan, labels


def find_optimal_k(
    latent_vectors: np.ndarray,
    k_range: range | list[int] = range(2, 21),
    random_state: int = 42,
    n_init: int = 10,
) -> Tuple[int, dict]:
    """
    Find optimal number of clusters using silhouette score.
    
    Parameters
    ----------
    latent_vectors : np.ndarray
        Latent representations
    k_range : range or list
        Range of k values to test
    random_state : int
        Random seed
    n_init : int
        Number of KMeans runs per k
        
    Returns
    -------
    tuple
        (Optimal k, dictionary with scores for all k values)
    """
    print("\nFinding optimal k using silhouette score...")
    
    scores = {}
    best_k = None
    best_score = -1
    
    for k in k_range:
        kmeans = KMeans(
            n_clusters=k,
            random_state=random_state,
            n_init=n_init,
            max_iter=300,
        )
        labels = kmeans.fit_predict(latent_vectors)
        
        # Compute silhouette score
        silhouette = silhouette_score(latent_vectors, labels)
        calinski_harabasz = calinski_harabasz_score(latent_vectors, labels)
        davies_bouldin = davies_bouldin_score(latent_vectors, labels)
        
        scores[k] = {
            "silhouette": silhouette,
            "calinski_harabasz": calinski_harabasz,
            "davies_bouldin": davies_bouldin,
        }
        
        if silhouette > best_score:
            best_score = silhouette
            best_k = k
        
        print(f"  k={k:2d}: silhouette={silhouette:.4f}, "
              f"CH={calinski_harabasz:.2f}, DB={davies_bouldin:.4f}")
    
    print(f"\n  ✓ Optimal k: {best_k} (silhouette score: {best_score:.4f})")
    
    return best_k, scores


def cluster_latent_space(
    latent_path: str | Path = DEFAULT_LATENT_PATH,
    method: Literal["kmeans", "dbscan"] = "kmeans",
    n_clusters: int | None = None,
    auto_optimize_k: bool = True,
    k_range: range | list[int] = range(2, 21),
    dbscan_eps: float = 0.5,
    dbscan_min_samples: int = 5,
    save_model: bool = True,
    models_dir: str | Path = DEFAULT_MODELS_DIR,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, object]:
    """
    Main function to cluster latent space representations.
    
    Parameters
    ----------
    latent_path : str or Path
        Path to latent_representations.csv
    method : str
        Clustering method: "kmeans" or "dbscan"
    n_clusters : int, optional
        Number of clusters for KMeans (if None and auto_optimize_k=True, will find optimal k)
    auto_optimize_k : bool
        If True, find optimal k using silhouette score
    k_range : range or list
        Range of k values to test (only used if auto_optimize_k=True)
    dbscan_eps : float
        Epsilon parameter for DBSCAN
    dbscan_min_samples : int
        Min samples parameter for DBSCAN
    save_model : bool
        Whether to save the fitted model
    models_dir : str or Path
        Directory to save models
    random_state : int
        Random seed
        
    Returns
    -------
    tuple
        (DataFrame with meter_id and cluster labels, fitted clustering model)
    """
    # Load latent representations
    latent_df, latent_vectors = load_latent_representations(latent_path)
    
    # Perform clustering
    if method == "kmeans":
        if auto_optimize_k and n_clusters is None:
            optimal_k, scores = find_optimal_k(latent_vectors, k_range=k_range, random_state=random_state)
            n_clusters = optimal_k
        
        if n_clusters is None:
            raise ValueError("n_clusters must be specified if auto_optimize_k=False")
        
        model, labels = perform_kmeans_clustering(
            latent_vectors,
            n_clusters=n_clusters,
            random_state=random_state,
        )
        
    elif method == "dbscan":
        model, labels = perform_dbscan_clustering(
            latent_vectors,
            eps=dbscan_eps,
            min_samples=dbscan_min_samples,
        )
        
    else:
        raise ValueError(f"Unknown clustering method: {method}. Use 'kmeans' or 'dbscan'")
    
    # Create results DataFrame
    results_df = pd.DataFrame({
        "meter_id": latent_df["meter_id"].values,
        "cluster_label": labels,
    })
    
    # Save model
    if save_model:
        models_dir = Path(models_dir)
        models_dir.mkdir(exist_ok=True)
        
        model_path = models_dir / f"stage3_{method}_clustering.joblib"
        joblib.dump(model, model_path)
        print(f"\n  ✓ Saved clustering model to: {model_path}")
    
    return results_df, model
