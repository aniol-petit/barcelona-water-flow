"""
Stage 4: Risk Probability Scoring

Computes failure risk scores (0-100) for each meter based on:
1. Intra-cluster anomaly distance (how atypical within cluster)
2. Cluster-level degradation (based on age and canya)
"""

from .risk_scoring import compute_risk_scores

__all__ = ["compute_risk_scores"]

