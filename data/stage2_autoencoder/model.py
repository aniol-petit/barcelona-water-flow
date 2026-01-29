"""
Autoencoder model architecture definition using PyTorch.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class Autoencoder(nn.Module):
    """
    Autoencoder for learning latent representations of water meter features.
    
    Architecture:
    - Encoder: Input -> Hidden1 -> Hidden2 -> Latent (Z)
    - Decoder: Latent (Z) -> Hidden2 -> Hidden1 -> Output
    
    The model captures non-linear relationships between:
    - 48 monthly average consumption values
    - Normalized physical features (age, diameter, canya)
    - Cluster label from Stage I
    - One-hot encoded brand/model
    """
    
    def __init__(
        self,
        input_dim: int,
        latent_dim: int = 8,
        hidden_dims: list[int] | None = None,
        dropout: float = 0.0,
    ):
        """
        Initialize the autoencoder.
        
        Parameters
        ----------
        input_dim : int
            Dimension of input features (typically 72: 48 monthly + 1 age + 4 diameter + 
            1 canya + 1 cluster_label + 17 brand_model)
        latent_dim : int
            Dimension of latent representation Z (default: 8, should be tuned)
        hidden_dims : list[int] | None
            Dimensions of hidden layers. If None, uses [64, 32] as default.
            The encoder will be: input_dim -> hidden_dims[0] -> hidden_dims[1] -> latent_dim
            The decoder will be: latent_dim -> hidden_dims[1] -> hidden_dims[0] -> input_dim
        dropout : float
            Dropout probability for regularization (default: 0.0, no dropout)
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        # Default hidden dimensions if not provided
        if hidden_dims is None:
            hidden_dims = [64, 32]
        
        if len(hidden_dims) != 2:
            raise ValueError("hidden_dims must have exactly 2 elements")
        
        hidden1_dim, hidden2_dim = hidden_dims
        
        # Encoder layers
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden1_dim),
            nn.ReLU(),
            nn.Dropout(dropout) if dropout > 0 else nn.Identity(),
            nn.Linear(hidden1_dim, hidden2_dim),
            nn.ReLU(),
            nn.Dropout(dropout) if dropout > 0 else nn.Identity(),
            nn.Linear(hidden2_dim, latent_dim),
        )
        
        # Decoder layers
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden2_dim),
            nn.ReLU(),
            nn.Dropout(dropout) if dropout > 0 else nn.Identity(),
            nn.Linear(hidden2_dim, hidden1_dim),
            nn.ReLU(),
            nn.Dropout(dropout) if dropout > 0 else nn.Identity(),
            nn.Linear(hidden1_dim, input_dim),
        )
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Encode input features to latent representation.
        
        Parameters
        ----------
        x : torch.Tensor
            Input features of shape (batch_size, input_dim)
        
        Returns
        -------
        torch.Tensor
            Latent representation Z of shape (batch_size, latent_dim)
        """
        return self.encoder(x)
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """
        Decode latent representation to reconstructed features.
        
        Parameters
        ----------
        z : torch.Tensor
            Latent representation of shape (batch_size, latent_dim)
        
        Returns
        -------
        torch.Tensor
            Reconstructed features of shape (batch_size, input_dim)
        """
        return self.decoder(z)
    
    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass: encode and decode.
        
        Parameters
        ----------
        x : torch.Tensor
            Input features of shape (batch_size, input_dim)
        
        Returns
        -------
        tuple[torch.Tensor, torch.Tensor]
            (latent_z, reconstructed_x)
            - latent_z: Latent representation of shape (batch_size, latent_dim)
            - reconstructed_x: Reconstructed features of shape (batch_size, input_dim)
        """
        z = self.encode(x)
        x_reconstructed = self.decode(z)
        return z, x_reconstructed
    
    def get_latent_representations(self, x: torch.Tensor) -> torch.Tensor:
        """
        Get latent representations for input features (convenience method).
        
        Parameters
        ----------
        x : torch.Tensor
            Input features of shape (batch_size, input_dim)
        
        Returns
        -------
        torch.Tensor
            Latent representation Z of shape (batch_size, latent_dim)
        """
        self.eval()
        with torch.no_grad():
            z = self.encode(x)
        return z
