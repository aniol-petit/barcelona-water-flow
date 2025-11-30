"""
Main script to run Stage II: Autoencoder training and latent representation extraction.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

# Handle both direct execution and module import
try:
    from .model import Autoencoder
    from .trainer import (
        create_data_loaders,
        EarlyStopping,
        extract_latent_representations,
        train_autoencoder,
    )
except ImportError:
    # When run directly, add parent directory to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stage2_autoencoder.model import Autoencoder
    from stage2_autoencoder.trainer import (
        create_data_loaders,
        EarlyStopping,
        extract_latent_representations,
        train_autoencoder,
    )

# Paths
STAGE1_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "stage1_outputs"
STAGE2_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "stage2_outputs"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

STAGE1_FEATURE_VECTORS = STAGE1_OUTPUT_DIR / "feature_vectors.csv"
STAGE2_LATENT_OUTPUT = STAGE2_OUTPUT_DIR / "latent_representations.csv"
MODEL_PATH = MODELS_DIR / "stage2_autoencoder.pth"

# Create output directories
STAGE2_OUTPUT_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)


def run_stage2(
    feature_vectors_path: str | Path = STAGE1_FEATURE_VECTORS,
    latent_dim: int = 8,
    hidden_dims: list[int] | None = None,
    num_epochs: int = 100,
    batch_size: int = 64,
    learning_rate: float = 0.001,
    weight_decay: float = 0.0,
    dropout: float = 0.0,
    train_ratio: float = 0.8,
    early_stopping_patience: int = 10,
    device: str | None = None,
    random_seed: int = 42,
    verbose: bool = True,
) -> tuple[pd.DataFrame, Autoencoder]:
    """
    Run Stage II: Train autoencoder and extract latent representations.
    
    Parameters
    ----------
    feature_vectors_path : str | Path
        Path to feature vectors CSV from Stage I
    latent_dim : int
        Dimension of latent representation Z (default: 8)
    hidden_dims : list[int] | None
        Hidden layer dimensions [hidden1, hidden2]. Default: [64, 32]
    num_epochs : int
        Maximum number of training epochs
    batch_size : int
        Batch size for training
    learning_rate : float
        Learning rate for optimizer
    weight_decay : float
        L2 regularization weight decay
    dropout : float
        Dropout probability for regularization
    train_ratio : float
        Proportion of data for training (rest for validation)
    early_stopping_patience : int
        Patience for early stopping (epochs without improvement)
    device : str | None
        Device to train on ('cpu', 'cuda', or None for auto-detect)
    random_seed : int
        Random seed for reproducibility
    verbose : bool
        If True, print progress information
    
    Returns
    -------
    tuple[pd.DataFrame, Autoencoder]
        (latent_df, trained_model)
        - latent_df: DataFrame with meter_id and latent vectors Z
        - trained_model: Trained autoencoder model
    """
    # Set random seeds for reproducibility
    torch.manual_seed(random_seed)
    np.random.seed(random_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(random_seed)
    
    # Auto-detect device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if verbose:
        print("=" * 70)
        print("STAGE II: AUTOENCODER TRAINING")
        print("=" * 70)
        print(f"Device: {device}")
        print(f"Random seed: {random_seed}")
    
    # Step 1: Load feature vectors
    if verbose:
        print("\nStep 1: Loading feature vectors...")
    
    feature_vectors_path = Path(feature_vectors_path)
    if not feature_vectors_path.exists():
        raise FileNotFoundError(
            f"Feature vectors file not found at {feature_vectors_path}. "
            "Run Stage I first to generate feature_vectors.csv"
        )
    
    df = pd.read_csv(feature_vectors_path)
    if verbose:
        print(f"  ✓ Loaded {len(df):,} meters")
        print(f"  ✓ Total columns: {len(df.columns)}")
    
    # Separate meter_id from features
    meter_ids = df["meter_id"].values
    feature_columns = [col for col in df.columns if col != "meter_id"]
    X = df[feature_columns].values
    
    input_dim = X.shape[1]
    if verbose:
        print(f"  ✓ Input dimension: {input_dim}")
        print(f"  ✓ Feature columns: {len(feature_columns)}")
    
    # Step 2: Create data loaders
    if verbose:
        print("\nStep 2: Creating data loaders...")
    
    train_loader, val_loader = create_data_loaders(
        X,
        batch_size=batch_size,
        train_ratio=train_ratio,
        shuffle=True,
        random_seed=random_seed,
    )
    
    if verbose:
        print(f"  ✓ Training samples: {len(train_loader.dataset):,}")
        print(f"  ✓ Validation samples: {len(val_loader.dataset):,}")
        print(f"  ✓ Batch size: {batch_size}")
    
    # Step 3: Initialize model
    if verbose:
        print("\nStep 3: Initializing autoencoder model...")
    
    if hidden_dims is None:
        hidden_dims = [64, 32]
    
    model = Autoencoder(
        input_dim=input_dim,
        latent_dim=latent_dim,
        hidden_dims=hidden_dims,
        dropout=dropout,
    )
    
    if verbose:
        print(f"  ✓ Architecture: {input_dim} -> {hidden_dims[0]} -> {hidden_dims[1]} -> {latent_dim}")
        print(f"  ✓ Latent dimension: {latent_dim}")
        print(f"  ✓ Total parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Step 4: Train model
    if verbose:
        print("\nStep 4: Training autoencoder...")
    
    early_stopping = EarlyStopping(
        patience=early_stopping_patience,
        min_delta=0.0,
        restore_best_weights=True,
    )
    
    history = train_autoencoder(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=num_epochs,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        device=device,
        early_stopping=early_stopping,
        verbose=verbose,
    )
    
    if verbose:
        print(f"\n  ✓ Final train loss: {history['train_loss'][-1]:.6f}")
        if history['val_loss']:
            print(f"  ✓ Final val loss: {history['val_loss'][-1]:.6f}")
    
    # Step 5: Save model
    if verbose:
        print("\nStep 5: Saving model...")
    
    torch.save(model.state_dict(), MODEL_PATH)
    if verbose:
        print(f"  ✓ Model saved to: {MODEL_PATH}")
    
    # Step 6: Extract latent representations for all data
    if verbose:
        print("\nStep 6: Extracting latent representations...")
    
    # Create data loader for all data (no split)
    all_dataset = torch.utils.data.TensorDataset(torch.from_numpy(X.astype(np.float32)))
    all_loader = torch.utils.data.DataLoader(
        all_dataset,
        batch_size=batch_size,
        shuffle=False,
    )
    
    Z = extract_latent_representations(model, all_loader, device=device)
    
    if verbose:
        print(f"  ✓ Extracted latent vectors: {Z.shape}")
        print(f"    - Samples: {Z.shape[0]:,}")
        print(f"    - Latent dimension: {Z.shape[1]}")
    
    # Step 7: Save latent representations
    if verbose:
        print("\nStep 7: Saving latent representations...")
    
    latent_df = pd.DataFrame(
        Z,
        columns=[f"z_{i+1}" for i in range(latent_dim)],
    )
    latent_df.insert(0, "meter_id", meter_ids)
    
    latent_df.to_csv(STAGE2_LATENT_OUTPUT, index=False)
    if verbose:
        print(f"  ✓ Latent representations saved to: {STAGE2_LATENT_OUTPUT}")
    
    if verbose:
        print("\n" + "=" * 70)
        print("STAGE II COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"Output files:")
        print(f"  - Model: {MODEL_PATH}")
        print(f"  - Latent representations: {STAGE2_LATENT_OUTPUT}")
    
    return latent_df, model


if __name__ == "__main__":
    # Run with default parameters
    latent_df, model = run_stage2(verbose=True)

