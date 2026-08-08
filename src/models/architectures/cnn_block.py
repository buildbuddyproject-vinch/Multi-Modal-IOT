"""1D convolutional block: extracts local temporal patterns (short-term trends,
sudden spikes/drops across channels) before the recurrent/attention stages.

Uses padding="same" so the output keeps the same sequence length as the input --
the CNN block's job is local feature extraction, not downsampling; the sequence is
still needed intact for the Bi-LSTM and Transformer stages that follow.
"""
import keras
from keras import layers


def build_cnn_block(
    inputs: keras.KerasTensor,
    filters: tuple[int, ...] = (64, 64),
    kernel_size: int = 3,
    dropout: float = 0.2,
    name: str = "cnn_block",
) -> keras.KerasTensor:
    """inputs: (batch, timesteps, channels) -> returns (batch, timesteps, filters[-1])"""
    x = inputs
    for i, n_filters in enumerate(filters):
        x = layers.Conv1D(
            filters=n_filters, kernel_size=kernel_size, padding="same",
            activation=None, name=f"{name}_conv{i+1}",
        )(x)
        x = layers.BatchNormalization(name=f"{name}_bn{i+1}")(x)
        x = layers.Activation("relu", name=f"{name}_relu{i+1}")(x)
        x = layers.Dropout(dropout, name=f"{name}_dropout{i+1}")(x)
    return x
