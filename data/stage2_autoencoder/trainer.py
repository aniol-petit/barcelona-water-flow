"""
Autoencoder training loop, validation, and early stopping.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from .model import Autoencoder


class EarlyStopping:
    """Early stopping to prevent overfitting."""
    
    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 0.0,
        restore_best_weights: bool = True,
    ):
        """
        Initialize early stopping.
        
        Parameters
        ----------
        patience : int
            Number of epochs to wait before stopping if no improvement
        min_delta : float
            Minimum change to qualify as an improvement
        restore_best_weights : bool
            If True, restore best model weights when stopping
        """
        self.patience = patience
        self.min_delta = min_delta
        self.restore_best_weights = restore_best_weights
        self.best_loss = float('inf')
        self.counter = 0
        self.best_weights = None
    
    def __call__(self, val_loss: float, model: nn.Module) -> bool:
        """
        Check if training should stop.
        
        Parameters
        ----------
        val_loss : float
            Current validation loss
        model : nn.Module
            Model to save weights from
        
        Returns
        -------
        bool
            True if training should stop, False otherwise
        """
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
            if self.restore_best_weights:
                self.best_weights = model.state_dict().copy()
            return False
        else:
            self.counter += 1
            return self.counter >= self.patience
    
    def restore_weights(self, model: nn.Module):
        """Restore best model weights."""
        if self.best_weights is not None:
            model.load_state_dict(self.best_weights)


def train_autoencoder(
    model: Autoencoder,
    train_loader: DataLoader,
    val_loader: DataLoader | None = None,
    num_epochs: int = 100,
    learning_rate: float = 0.001,
    weight_decay: float = 0.0,
    device: str | torch.device = "cpu",
    early_stopping: EarlyStopping | None = None,
    verbose: bool = True,
) -> dict:
    """
    Train the autoencoder model.
    
    Parameters
    ----------
    model : Autoencoder
        Autoencoder model to train
    train_loader : DataLoader
        Training data loader
    val_loader : DataLoader | None
        Validation data loader (optional)
    num_epochs : int
        Maximum number of training epochs
    learning_rate : float
        Learning rate for optimizer
    weight_decay : float
        L2 regularization weight decay
    device : str | torch.device
        Device to train on ('cpu' or 'cuda')
    early_stopping : EarlyStopping | None
        Early stopping callback (optional)
    verbose : bool
        If True, print training progress
    
    Returns
    -------
    dict
        Training history with keys: 'train_loss', 'val_loss' (if validation used)
    """
    device = torch.device(device)
    model = model.to(device)
    
    # Loss function: Mean Squared Error (reconstruction error)
    criterion = nn.MSELoss()
    
    # Optimizer: Adam
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )
    
    history = {
        'train_loss': [],
        'val_loss': [],
    }
    
    if verbose:
        print(f"Training on device: {device}")
        print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        print(f"Input dimension: {model.input_dim}, Latent dimension: {model.latent_dim}")
        print("-" * 70)
    
    for epoch in range(num_epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        train_batches = 0
        
        for batch_x in train_loader:
            batch_x = batch_x[0].to(device)  # Get features from DataLoader
            
            # Forward pass
            optimizer.zero_grad()
            z, x_reconstructed = model(batch_x)
            loss = criterion(x_reconstructed, batch_x)
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            train_batches += 1
        
        avg_train_loss = train_loss / train_batches
        history['train_loss'].append(avg_train_loss)
        
        # Validation phase
        if val_loader is not None:
            model.eval()
            val_loss = 0.0
            val_batches = 0
            
            with torch.no_grad():
                for batch_x in val_loader:
                    batch_x = batch_x[0].to(device)
                    z, x_reconstructed = model(batch_x)
                    loss = criterion(x_reconstructed, batch_x)
                    val_loss += loss.item()
                    val_batches += 1
            
            avg_val_loss = val_loss / val_batches
            history['val_loss'].append(avg_val_loss)
            
            if verbose and (epoch + 1) % 10 == 0:
                print(
                    f"Epoch {epoch + 1:3d}/{num_epochs} | "
                    f"Train Loss: {avg_train_loss:.6f} | "
                    f"Val Loss: {avg_val_loss:.6f}"
                )
            
            # Early stopping check
            if early_stopping is not None:
                if early_stopping(avg_val_loss, model):
                    if verbose:
                        print(f"\nEarly stopping at epoch {epoch + 1}")
                    if early_stopping.restore_best_weights:
                        early_stopping.restore_weights(model)
                    break
        else:
            if verbose and (epoch + 1) % 10 == 0:
                print(
                    f"Epoch {epoch + 1:3d}/{num_epochs} | "
                    f"Train Loss: {avg_train_loss:.6f}"
                )
    
    if verbose:
        print("-" * 70)
        print("Training completed!")
    
    return history


def extract_latent_representations(
    model: Autoencoder,
    data_loader: DataLoader,
    device: str | torch.device = "cpu",
) -> np.ndarray:
    """
    Extract latent representations Z for all samples in the data loader.
    
    Parameters
    ----------
    model : Autoencoder
        Trained autoencoder model
    data_loader : DataLoader
        Data loader containing features
    device : str | torch.device
        Device to run inference on
    
    Returns
    -------
    np.ndarray
        Latent representations Z of shape (n_samples, latent_dim)
    """
    device = torch.device(device)
    model = model.to(device)
    model.eval()
    
    latent_vectors = []
    
    with torch.no_grad():
        for batch_x in data_loader:
            batch_x = batch_x[0].to(device)
            z = model.encode(batch_x)
            latent_vectors.append(z.cpu().numpy())
    
    return np.vstack(latent_vectors)


def create_data_loaders(
    X: np.ndarray | pd.DataFrame,
    batch_size: int = 64,
    train_ratio: float = 0.8,
    shuffle: bool = True,
    random_seed: int = 42,
) -> tuple[DataLoader, DataLoader]:
    """
    Create train and validation data loaders.
    
    Parameters
    ----------
    X : np.ndarray | pd.DataFrame
        Feature matrix of shape (n_samples, n_features)
    batch_size : int
        Batch size for training
    train_ratio : float
        Proportion of data to use for training (rest for validation)
    shuffle : bool
        Whether to shuffle the data before splitting
    random_seed : int
        Random seed for reproducibility
    
    Returns
    -------
    tuple[DataLoader, DataLoader]
        (train_loader, val_loader)
    """
    if isinstance(X, pd.DataFrame):
        X = X.values
    
    # Convert to float32
    X = X.astype(np.float32)
    
    # Split into train and validation
    n_samples = len(X)
    n_train = int(n_samples * train_ratio)
    
    if shuffle:
        np.random.seed(random_seed)
        indices = np.random.permutation(n_samples)
        X = X[indices]
    
    X_train = X[:n_train]
    X_val = X[n_train:]
    
    # Create datasets
    train_dataset = TensorDataset(torch.from_numpy(X_train))
    val_dataset = TensorDataset(torch.from_numpy(X_val))
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
    )
    
    return train_loader, val_loader
