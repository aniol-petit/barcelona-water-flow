"""
Stage II: Autoencoder to capture non-linear relationships and generate latent representations.
"""

from .model import Autoencoder
from .run_stage2 import run_stage2
from .trainer import (
    EarlyStopping,
    create_data_loaders,
    extract_latent_representations,
    train_autoencoder,
)

__all__ = [
    "Autoencoder",
    "run_stage2",
    "train_autoencoder",
    "extract_latent_representations",
    "create_data_loaders",
    "EarlyStopping",
]
