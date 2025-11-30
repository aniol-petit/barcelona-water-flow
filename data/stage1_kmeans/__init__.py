"""
Stage I: KMeans clustering on physical features to generate pseudo-labels.

This module implements Stage I of the clustering pipeline:
1. Compute physical features (age, diameter, canya, brand_model)
2. Normalize features (min-max for age/diameter, standardization for canya, one-hot for brand_model)
3. Find optimal k using silhouette score
4. Perform KMeans clustering on physical features
5. Return cluster labels to be used as features in the autoencoder input
"""

from .kmeans_physical import (
    build_stage1_feature_matrix,
    compute_physical_features,
    perform_stage1_kmeans,
)
from .run_stage1 import run_stage1_pipeline
from .silhouette_optimizer import find_optimal_k, plot_silhouette_scores

__all__ = [
    "build_stage1_feature_matrix",
    "compute_physical_features",
    "perform_stage1_kmeans",
    "find_optimal_k",
    "plot_silhouette_scores",
    "run_stage1_pipeline",
]



