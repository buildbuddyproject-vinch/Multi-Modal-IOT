"""Transformer encoder block: multi-head self-attention over the Bi-LSTM output
sequence, so the model can directly weigh which ICU hours (within the window)
matter most for the current prediction, independent of their recency.

A sinusoidal positional encoding is added before the first encoder layer --
self-attention has no inherent notion of order, and although the Bi-LSTM upstream
already encodes some ordering, an explicit positional signal is standard practice
and lets attention distinguish "3 hours ago" from "1 hour ago" directly.
"""
import numpy as np
import tensorflow as tf
import keras
from keras import layers


@keras.saving.register_keras_serializable(package="sepsis_model")
class SinusoidalPositionalEncoding(layers.Layer):
    """Fixed (non-trainable) sinusoidal positional encoding, added to the input."""

    def __init__(self, name: str = "positional_encoding", **kwargs):
        super().__init__(name=name, **kwargs)

    def build(self, input_shape):
        timesteps, d_model = input_shape[-2], input_shape[-1]
        positions = np.arange(timesteps)[:, np.newaxis]
        dims = np.arange(d_model)[np.newaxis, :]
        angle_rates = 1.0 / np.power(10000, (2 * (dims // 2)) / np.float32(d_model))
        angles = positions * angle_rates
        angles[:, 0::2] = np.sin(angles[:, 0::2])
        angles[:, 1::2] = np.cos(angles[:, 1::2])
        self.pos_encoding = tf.constant(angles[np.newaxis, ...], dtype=tf.float32)
        super().build(input_shape)

    def call(self, inputs):
        return inputs + self.pos_encoding


def _transformer_encoder_layer(
    inputs: keras.KerasTensor,
    num_heads: int,
    key_dim: int,
    ff_dim: int,
    dropout: float,
    name: str,
) -> keras.KerasTensor:
    d_model = inputs.shape[-1]

    attn_output = layers.MultiHeadAttention(
        num_heads=num_heads, key_dim=key_dim, dropout=dropout, name=f"{name}_mha",
    )(inputs, inputs)
    attn_output = layers.Dropout(dropout, name=f"{name}_mha_dropout")(attn_output)
    x = layers.LayerNormalization(epsilon=1e-6, name=f"{name}_ln1")(inputs + attn_output)

    ff_output = layers.Dense(ff_dim, activation="relu", name=f"{name}_ff1")(x)
    ff_output = layers.Dense(d_model, name=f"{name}_ff2")(ff_output)
    ff_output = layers.Dropout(dropout, name=f"{name}_ff_dropout")(ff_output)
    return layers.LayerNormalization(epsilon=1e-6, name=f"{name}_ln2")(x + ff_output)


def build_transformer_block(
    inputs: keras.KerasTensor,
    num_layers: int = 2,
    num_heads: int = 4,
    key_dim: int = 16,
    ff_dim: int = 128,
    dropout: float = 0.2,
    name: str = "transformer_block",
) -> keras.KerasTensor:
    """inputs: (batch, timesteps, d_model) -> returns (batch, timesteps, d_model)"""
    x = SinusoidalPositionalEncoding(name=f"{name}_pos_enc")(inputs)
    for i in range(num_layers):
        x = _transformer_encoder_layer(x, num_heads, key_dim, ff_dim, dropout, name=f"{name}_layer{i+1}")
    return x
