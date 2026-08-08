from pathlib import Path

import pytest
from tensorflow import keras

from src.models.training.callbacks import build_callbacks, warmup_exponential_decay_schedule
from src.models.training.config import TrainingConfig


def test_build_callbacks_returns_expected_types(tmp_path: Path):
    config = TrainingConfig()
    callbacks = build_callbacks(config, tmp_path / "ckpt" / "model.keras", tmp_path / "tb_logs")
    types = [type(c) for c in callbacks]
    assert keras.callbacks.EarlyStopping in types
    assert keras.callbacks.ModelCheckpoint in types
    assert keras.callbacks.LearningRateScheduler in types
    assert keras.callbacks.TensorBoard in types


def test_build_callbacks_creates_output_directories(tmp_path: Path):
    config = TrainingConfig()
    checkpoint_path = tmp_path / "ckpt" / "model.keras"
    tb_dir = tmp_path / "tb_logs"
    build_callbacks(config, checkpoint_path, tb_dir)
    assert checkpoint_path.parent.exists()
    assert tb_dir.exists()


def test_early_stopping_uses_configured_monitor(tmp_path: Path):
    config = TrainingConfig(early_stopping_monitor="val_loss", early_stopping_mode="min", early_stopping_patience=3)
    callbacks = build_callbacks(config, tmp_path / "ckpt" / "model.keras", tmp_path / "tb_logs")
    early_stop = next(c for c in callbacks if isinstance(c, keras.callbacks.EarlyStopping))
    assert early_stop.monitor == "val_loss"
    assert early_stop.patience == 3


def test_lr_schedule_ramps_up_during_warmup():
    config = TrainingConfig(learning_rate=1e-3, lr_schedule_warmup_epochs=4, lr_schedule_decay_rate=0.9)
    schedule = warmup_exponential_decay_schedule(config)
    lr_epoch0 = schedule(0, config.learning_rate)
    lr_epoch1 = schedule(1, config.learning_rate)
    lr_epoch3 = schedule(3, config.learning_rate)
    assert lr_epoch0 < lr_epoch1 < lr_epoch3
    assert lr_epoch3 == pytest.approx(config.learning_rate)


def test_lr_schedule_decays_after_warmup():
    config = TrainingConfig(learning_rate=1e-3, lr_schedule_warmup_epochs=2, lr_schedule_decay_rate=0.9)
    schedule = warmup_exponential_decay_schedule(config)
    lr_epoch2 = schedule(2, config.learning_rate)  # first post-warmup epoch
    lr_epoch3 = schedule(3, config.learning_rate)
    assert lr_epoch3 < lr_epoch2
