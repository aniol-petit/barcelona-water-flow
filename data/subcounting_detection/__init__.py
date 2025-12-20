"""
Subcounting detection package.

This module exposes high-level utilities to compute a per-meter
subcounting score from the raw consumption time series.
"""

from .subcounting_detection import (
    SubcountingConfig,
    compute_subcounting_metrics,
    compute_subcounting_scores,
    load_consumption_data,
)

__all__ = [
    "SubcountingConfig",
    "compute_subcounting_metrics",
    "compute_subcounting_scores",
    "load_consumption_data",
]



