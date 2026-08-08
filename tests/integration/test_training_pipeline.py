from pathlib import Path

import numpy as np
import pytest

from src.models.architectures.hybrid_model import ModelConfig
from src.models.evaluation.evaluate import evaluate_model
from src.models.training.config import TrainingConfig
from src.models.training.train import train_model

TINY_MODEL_CONFIG = ModelConfig(
    window_size=8, n_channels=6,
    cnn_filters=(8,), bilstm_units=(8,),
    transformer_layers=1, transformer_heads=2, transformer_key_dim=4, transformer_ff_dim=16,
    dense_units=(8,), dropout=0.1,
)

TINY_TRAINING_CONFIG = TrainingConfig(
    batch_size=16, epochs=2, early_stopping_patience=2,
    lr_schedule_warmup_epochs=1,
)


def _make_npz(path: Path, n_samples: int, n_channels: int, window_size: int, seed: int, positive_rate: float = 0.3):
    rng = np.random.default_rng(seed)
    y = (rng.random(n_samples) < positive_rate).astype(np.int64)
    # make the signal at least weakly learnable so metrics aren't degenerate
    X = rng.normal(size=(n_samples, window_size, n_channels)).astype(np.float32)
    X[:, :, 0] += y[:, None] * 1.5
    np.savez_compressed(path, X=X, y=y, patient_ids=np.array([f"p{i}" for i in range(n_samples)]), window_end_time=np.arange(n_samples))


@pytest.fixture
def processed_dir(tmp_path: Path) -> Path:
    d = tmp_path / "processed"
    d.mkdir()
    _make_npz(d / "train.npz", n_samples=200, n_channels=6, window_size=8, seed=0)
    _make_npz(d / "val.npz", n_samples=60, n_channels=6, window_size=8, seed=1)
    _make_npz(d / "test.npz", n_samples=60, n_channels=6, window_size=8, seed=2)
    return d


def test_train_model_runs_and_saves_artifacts(processed_dir, tmp_path):
    output_dir = tmp_path / "models"
    model, history = train_model(
        train_npz=processed_dir / "train.npz",
        val_npz=processed_dir / "val.npz",
        output_dir=output_dir,
        model_config=TINY_MODEL_CONFIG,
        training_config=TINY_TRAINING_CONFIG,
    )

    assert "loss" in history
    assert len(history["loss"]) >= 1
    assert (output_dir / "saved" / "final_model.keras").exists()
    assert (output_dir / "logs" / "training_history.json").exists()

    # model is usable for prediction after training
    import numpy as np
    with np.load(processed_dir / "val.npz") as data:
        X_val = data["X"][:5]
    preds = model.predict(X_val, verbose=0)
    assert preds.shape == (5, 1)
    assert np.all((preds >= 0) & (preds <= 1))


def test_training_actually_learns_a_separable_signal(tmp_path):
    """Regression test for the tf.where shape-broadcast bug in binary_focal_loss:
    that bug made loss/accuracy look plausible while the model learned nothing
    (train AUROC stuck at ~0.5 no matter how separable the data was). Here the
    signal is blatant (channel 0 is offset by +3 for the positive class), so a
    correctly-training model must clearly beat chance within a few epochs."""
    d = tmp_path / "processed_separable"
    d.mkdir()
    rng = np.random.default_rng(0)
    n_samples = 400
    y = (rng.random(n_samples) < 0.3).astype(np.int64)
    X = rng.normal(scale=0.5, size=(n_samples, 8, 6)).astype(np.float32)
    X[:, :, 0] += y[:, None] * 3.0  # unmistakable signal on channel 0
    np.savez_compressed(d / "train.npz", X=X, y=y, patient_ids=np.array([f"p{i}" for i in range(n_samples)]), window_end_time=np.arange(n_samples))
    np.savez_compressed(d / "val.npz", X=X[:80], y=y[:80], patient_ids=np.array([f"p{i}" for i in range(80)]), window_end_time=np.arange(80))

    from sklearn.metrics import roc_auc_score

    _, history = train_model(
        train_npz=d / "train.npz",
        val_npz=d / "val.npz",
        output_dir=tmp_path / "models_separable",
        model_config=TINY_MODEL_CONFIG,
        training_config=TrainingConfig(batch_size=32, epochs=15, early_stopping_patience=15, lr_schedule_warmup_epochs=1),
    )

    assert max(history["auroc"]) > 0.8, f"model failed to learn an obvious signal; auroc history={history['auroc']}"


def test_evaluate_model_produces_all_artifacts(processed_dir, tmp_path):
    output_dir = tmp_path / "models"
    model, history = train_model(
        train_npz=processed_dir / "train.npz",
        val_npz=processed_dir / "val.npz",
        output_dir=output_dir,
        model_config=TINY_MODEL_CONFIG,
        training_config=TINY_TRAINING_CONFIG,
    )

    eval_dir = output_dir / "evaluation"
    report = evaluate_model(model, processed_dir / "test.npz", eval_dir, history=history)

    assert 0.0 <= report["auroc"] <= 1.0
    assert 0.0 <= report["auprc"] <= 1.0
    assert "metrics_at_0.5" in report
    assert "metrics_at_best_f1_threshold" in report

    for filename in [
        "metrics.json", "classification_report.txt", "roc_curve.png",
        "confusion_matrix_at_0.5.png", "confusion_matrix_at_best_f1.png", "training_curves.png",
    ]:
        path = eval_dir / filename
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0
