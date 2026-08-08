import numpy as np
import pytest

from src.models.architectures.hybrid_model import ModelConfig, build_hybrid_model
from src.models.explainability.shap_explainer import (
    ChannelGroupMasker,
    build_explainer,
    compute_shap_values,
    make_predict_fn,
)

TINY_CONFIG = ModelConfig(
    window_size=4, n_channels=4,
    cnn_filters=(4,), bilstm_units=(4,),
    transformer_layers=1, transformer_heads=1, transformer_key_dim=2, transformer_ff_dim=8,
    dense_units=(4,),
)
CHANNEL_NAMES = ["HR", "Temp", "Glucose", "WBC"]


def test_channel_group_masker_declares_channel_level_shape():
    background = np.random.default_rng(0).normal(size=(10, 4, 4)).astype(np.float32)
    masker = ChannelGroupMasker(background, window_size=4, n_channels=4)
    assert masker.shape() == (1, 4)
    assert masker.mask_shapes(np.zeros(16)) == [(4,)]


def test_channel_group_masker_replaces_masked_channels_with_background_mean():
    background = np.zeros((5, 4, 4), dtype=np.float32)
    background[..., 0] = 100.0  # channel 0's background mean is 100
    masker = ChannelGroupMasker(background, window_size=4, n_channels=4)

    x = np.arange(16, dtype=np.float32)  # real instance, reshape (4,4)
    mask = np.array([False, True, True, True])  # mask out channel 0 only
    masked = masker(mask, x)

    assert masked.shape == (1, 16)
    masked_reshaped = masked.reshape(4, 4)
    np.testing.assert_allclose(masked_reshaped[:, 0], 100.0)  # channel 0 replaced
    np.testing.assert_allclose(masked_reshaped[:, 1:], x.reshape(4, 4)[:, 1:])  # others untouched


def test_predict_fn_reshapes_and_returns_1d():
    model = build_hybrid_model(TINY_CONFIG)
    predict_fn = make_predict_fn(model, window_size=4, n_channels=4)
    X_flat = np.random.default_rng(0).normal(size=(5, 16)).astype(np.float32)
    out = predict_fn(X_flat)
    assert out.shape == (5,)
    assert np.all((out >= 0) & (out <= 1))


def test_compute_shap_values_satisfies_additivity():
    """The defining property of Shapley values: base_value + sum(shap_values) must
    equal the model's actual prediction for that instance (up to numerical tolerance
    from the Permutation explainer's finite sampling)."""
    model = build_hybrid_model(TINY_CONFIG)
    rng = np.random.default_rng(0)
    background = rng.normal(size=(15, 4, 4)).astype(np.float32)
    X_eval = rng.normal(size=(2, 4, 4)).astype(np.float32)

    explainer = build_explainer(model, background, window_size=4, n_channels=4, channel_names=CHANNEL_NAMES)
    shap_values = compute_shap_values(explainer, X_eval, max_evals=50)

    predict_fn = make_predict_fn(model, 4, 4)
    preds = predict_fn(X_eval.reshape(2, -1))

    for i in range(2):
        reconstructed = shap_values.base_values[i] + shap_values.values[i].sum()
        assert reconstructed == pytest.approx(preds[i], abs=1e-4)


def test_compute_shap_values_shapes_and_names():
    model = build_hybrid_model(TINY_CONFIG)
    rng = np.random.default_rng(1)
    background = rng.normal(size=(15, 4, 4)).astype(np.float32)
    X_eval = rng.normal(size=(3, 4, 4)).astype(np.float32)

    explainer = build_explainer(model, background, window_size=4, n_channels=4, channel_names=CHANNEL_NAMES)
    shap_values = compute_shap_values(explainer, X_eval, max_evals=50)

    assert shap_values.values.shape == (3, 4)
    assert np.array(shap_values.data).shape == (3, 4)  # channel-level, not raw flattened
    assert list(shap_values.feature_names) == CHANNEL_NAMES
