import numpy as np
import pytest
import tensorflow as tf

from src.models.architectures.hybrid_model import ModelConfig, build_hybrid_model
from src.models.training.compile_utils import compile_model
from src.models.training.config import TrainingConfig

SMALL_CONFIG = ModelConfig(
    window_size=8, n_channels=6,
    cnn_filters=(8, 8), bilstm_units=(8,),
    transformer_layers=1, transformer_heads=2, transformer_key_dim=4, transformer_ff_dim=16,
    dense_units=(8,), dropout=0.1,
)


def test_build_hybrid_model_input_output_shapes():
    model = build_hybrid_model(SMALL_CONFIG)
    assert model.input_shape == (None, 8, 6)
    assert model.output_shape == (None, 1)


def test_forward_pass_produces_values_in_unit_interval():
    model = build_hybrid_model(SMALL_CONFIG)
    x = tf.random.normal((4, 8, 6))
    y = model(x, training=False).numpy()
    assert y.shape == (4, 1)
    assert np.all(y >= 0.0) and np.all(y <= 1.0)
    assert np.all(np.isfinite(y))


def test_model_has_trainable_parameters():
    model = build_hybrid_model(SMALL_CONFIG)
    assert model.count_params() > 0
    assert len(model.trainable_variables) > 0


def test_model_output_deterministic_in_inference_mode():
    model = build_hybrid_model(SMALL_CONFIG)
    x = tf.random.normal((2, 8, 6), seed=0)
    y1 = model(x, training=False).numpy()
    y2 = model(x, training=False).numpy()
    np.testing.assert_allclose(y1, y2)


def test_different_window_size_and_channels():
    config = ModelConfig(
        window_size=12, n_channels=10,
        cnn_filters=(8,), bilstm_units=(8,),
        transformer_layers=1, transformer_heads=2, transformer_key_dim=4, transformer_ff_dim=16,
        dense_units=(8,),
    )
    model = build_hybrid_model(config)
    assert model.input_shape == (None, 12, 10)
    x = tf.random.normal((3, 12, 10))
    y = model(x, training=False).numpy()
    assert y.shape == (3, 1)


def test_compile_model_smoke_fit_runs_without_error():
    model = build_hybrid_model(SMALL_CONFIG)
    compile_model(model, TrainingConfig(learning_rate=1e-3, focal_loss_alpha=0.25, focal_loss_gamma=2.0))

    rng = np.random.default_rng(0)
    X = rng.normal(size=(32, 8, 6)).astype(np.float32)
    y = rng.integers(0, 2, size=32).astype(np.float32)

    history = model.fit(X, y, batch_size=8, epochs=1, verbose=0)
    assert "loss" in history.history
    assert np.isfinite(history.history["loss"][0])
    assert "auroc" in history.history


def test_model_save_load_roundtrip_preserves_predictions(tmp_path):
    """Regression test: SinusoidalPositionalEncoding (and BinaryFocalLoss) must be
    registered with @keras.saving.register_keras_serializable, or a saved model
    becomes permanently unloadable ('Could not locate class ...') even though
    saving itself reports no error. This must be caught here, not after a real
    training run has already produced an unrecoverable checkpoint."""
    import keras

    model = build_hybrid_model(SMALL_CONFIG)
    x = tf.random.normal((3, 8, 6))
    before = model(x, training=False).numpy()

    save_path = tmp_path / "model.keras"
    model.save(save_path)
    reloaded = keras.models.load_model(save_path, compile=False)
    after = reloaded(x, training=False).numpy()

    np.testing.assert_allclose(before, after, rtol=1e-5)


def test_default_model_config_matches_step2_schema():
    from src.data.schema import CLINICAL_CHANNELS
    config = ModelConfig()
    assert config.n_channels == len(CLINICAL_CHANNELS) == 34
    assert config.window_size == 8
