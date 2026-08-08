"""SHAP explainability for the hybrid model.

Two design choices, both driven by the same constraint -- the model mixes Conv1D,
LSTM, and MultiHeadAttention, so SHAP's gradient-based explainers
(DeepExplainer/GradientExplainer) are unreliable or unsupported here, leaving only
model-agnostic (black-box) explainers, which are evaluation-hungry:

1. The model is wrapped as a plain function over the flattened (timestep, channel)
   window rather than anything gradient-based -- correctness over speed.
2. SHAP values are computed at the CHANNEL level (34 units), not per (timestep,
   channel) pair (272 units): a custom masker treats each channel's full 8-hour
   trace as one maskable group, masked-out channels are replaced with that
   channel's mean trace from the background sample. This cuts the Permutation
   explainer's default evaluation budget from 2*272+1=545 to 2*34+1=69 per
   instance, and is also the clinically meaningful granularity -- "Lactate
   mattered for this prediction" is the right level of explanation, not
   "Lactate at hour t-3 mattered but t-5 didn't".
"""
import numpy as np
import shap
from keras import Model as KerasModel

from src.data.schema import CLINICAL_CHANNELS


def make_predict_fn(model: KerasModel, window_size: int, n_channels: int):
    """Wraps the model as f(X_flat: (N, window_size*n_channels)) -> (N,) probabilities.

    Uses the model's direct __call__ rather than model.predict(): SHAP calls this
    function hundreds of times per explained instance, and predict()'s per-call
    overhead (progress bar setup, input pipeline construction) dominates when
    repeated that often.
    """

    def predict_fn(X_flat: np.ndarray) -> np.ndarray:
        X_flat = np.asarray(X_flat, dtype=np.float32)
        X = X_flat.reshape(-1, window_size, n_channels)
        return model(X, training=False).numpy().ravel()

    return predict_fn


class ChannelGroupMasker(shap.maskers.Masker):
    """Declares `n_channels` maskable groups (not window_size*n_channels raw scalars)
    by overriding `.shape`, which SHAP's Permutation explainer reads to decide how
    long a mask vector it should generate. Masking channel c means replacing that
    channel's entire timestep trace with its mean value from the background sample.
    """

    def __init__(self, background_X: np.ndarray, window_size: int, n_channels: int):
        self.window_size = window_size
        self.n_channels = n_channels
        self.background_fill = background_X.mean(axis=(0, 1))  # (n_channels,)

    def shape(self, *args) -> tuple[int, int]:
        return (1, self.n_channels)

    def mask_shapes(self, *args) -> list[tuple[int]]:
        """Tells SHAP's Explanation builder that the *output* mask dimension is
        n_channels, not the raw flattened-input dimension (window_size*n_channels).
        Without this it falls back to `[a.shape for a in args]` (the raw input
        shape) and crashes trying to reshape n_channels-long SHAP values into that."""
        return [(self.n_channels,) for _ in args]

    def __call__(self, mask: np.ndarray, x: np.ndarray) -> np.ndarray:
        mask = np.asarray(mask, dtype=bool)
        x_reshaped = x.reshape(self.window_size, self.n_channels).copy()
        x_reshaped[:, ~mask] = self.background_fill[~mask]
        return x_reshaped.reshape(1, -1)


def build_explainer(
    model: KerasModel,
    background_X: np.ndarray,
    window_size: int,
    n_channels: int,
    channel_names: list[str] = CLINICAL_CHANNELS,
) -> shap.Explainer:
    """background_X: (n_background, window_size, n_channels) -- a small representative
    sample (e.g. from the train split) used as the SHAP masking baseline."""
    predict_fn = make_predict_fn(model, window_size, n_channels)
    masker = ChannelGroupMasker(background_X, window_size, n_channels)
    return shap.Explainer(predict_fn, masker, feature_names=channel_names, algorithm="permutation")


def compute_shap_values(explainer: shap.Explainer, X: np.ndarray, max_evals: int | str = "auto") -> shap.Explanation:
    """X: (n_samples, window_size, n_channels) -> shap.Explanation over channel-grouped features.

    `.data` is overridden to the per-channel mean over the window (one value per
    channel, matching `.values`/`.feature_names`) -- SHAP's own masker/explainer
    plumbing returns the raw flattened (window_size*n_channels) instance in `.data`
    by default, which is the wrong shape for shap's plotting functions (summary_plot,
    waterfall, etc.) to pair against 34 channel-level SHAP values.
    """
    n_samples, window_size, n_channels = X.shape
    X_flat = X.reshape(n_samples, -1)
    explanation = explainer(X_flat, max_evals=max_evals)
    channel_means = X.mean(axis=1)  # (n_samples, n_channels)
    return shap.Explanation(
        values=explanation.values,
        base_values=explanation.base_values,
        data=channel_means,
        feature_names=explanation.feature_names,
    )
