"""Bidirectional LSTM block: captures longer-range temporal dependencies (both
forward-in-time and backward-in-time) in the CNN-extracted feature sequence."""
import keras
from keras import layers


def build_bilstm_block(
    inputs: keras.KerasTensor,
    units: tuple[int, ...] = (64,),
    dropout: float = 0.2,
    recurrent_dropout: float = 0.0,
    name: str = "bilstm_block",
) -> keras.KerasTensor:
    """inputs: (batch, timesteps, features) -> returns (batch, timesteps, 2*units[-1])
    (return_sequences=True throughout, so the Transformer block downstream still
    has a full sequence to attend over)."""
    x = inputs
    for i, n_units in enumerate(units):
        x = layers.Bidirectional(
            layers.LSTM(n_units, return_sequences=True, dropout=dropout, recurrent_dropout=recurrent_dropout),
            name=f"{name}_bilstm{i+1}",
        )(x)
    return x
