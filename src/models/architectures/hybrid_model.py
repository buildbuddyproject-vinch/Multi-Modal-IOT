"""Hybrid CNN -> Bi-LSTM -> Transformer Encoder -> Dense -> Sigmoid model for
sepsis-onset prediction from a fixed-length window of ICU vitals/labs.

Input:  (batch, window_size, n_channels)   -- see src/data/preprocessing/windowing.py
Output: (batch, 1)                          -- P(sepsis onset within the challenge's
                                                6h window, as of the last timestep)
"""
from dataclasses import dataclass

import keras
from keras import layers

from src.data.schema import CLINICAL_CHANNELS
from src.models.architectures.bilstm_block import build_bilstm_block
from src.models.architectures.cnn_block import build_cnn_block
from src.models.architectures.transformer_block import build_transformer_block


@dataclass(frozen=True)
class ModelConfig:
    window_size: int = 8
    n_channels: int = len(CLINICAL_CHANNELS)
    cnn_filters: tuple[int, ...] = (64, 64)
    cnn_kernel_size: int = 3
    bilstm_units: tuple[int, ...] = (64,)
    transformer_layers: int = 2
    transformer_heads: int = 4
    transformer_key_dim: int = 16
    transformer_ff_dim: int = 128
    dense_units: tuple[int, ...] = (64, 32)
    dropout: float = 0.2
    model_name: str = "hybrid_cnn_bilstm_transformer"


def build_hybrid_model(config: ModelConfig = ModelConfig()) -> keras.Model:
    inputs = keras.Input(shape=(config.window_size, config.n_channels), name="vitals_window")

    x = build_cnn_block(inputs, filters=config.cnn_filters, kernel_size=config.cnn_kernel_size, dropout=config.dropout)
    x = build_bilstm_block(x, units=config.bilstm_units, dropout=config.dropout)
    x = build_transformer_block(
        x,
        num_layers=config.transformer_layers,
        num_heads=config.transformer_heads,
        key_dim=config.transformer_key_dim,
        ff_dim=config.transformer_ff_dim,
        dropout=config.dropout,
    )

    x = layers.GlobalAveragePooling1D(name="temporal_pool")(x)

    for i, units in enumerate(config.dense_units):
        x = layers.Dense(units, activation="relu", name=f"dense_{i+1}")(x)
        x = layers.Dropout(config.dropout, name=f"dense_{i+1}_dropout")(x)

    outputs = layers.Dense(1, activation="sigmoid", name="sepsis_probability")(x)

    return keras.Model(inputs=inputs, outputs=outputs, name=config.model_name)
