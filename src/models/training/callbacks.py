"""Callback factory: EarlyStopping, ModelCheckpoint, a warmup+exponential-decay
Learning Rate Scheduler, and TensorBoard logging (used starting Step 5's training run)."""
from pathlib import Path

import keras

from src.models.training.config import TrainingConfig


def warmup_exponential_decay_schedule(config: TrainingConfig):
    """LR ramps linearly for `lr_schedule_warmup_epochs`, then decays exponentially.
    Warmup avoids early large-gradient instability from the randomly-initialized
    Transformer block; decay lets training settle as it approaches convergence."""

    def schedule(epoch: int, lr: float) -> float:
        if epoch < config.lr_schedule_warmup_epochs:
            return config.learning_rate * (epoch + 1) / config.lr_schedule_warmup_epochs
        decayed_epoch = epoch - config.lr_schedule_warmup_epochs
        return config.learning_rate * (config.lr_schedule_decay_rate ** decayed_epoch)

    return schedule


def build_callbacks(
    config: TrainingConfig,
    checkpoint_path: Path,
    tensorboard_log_dir: Path,
) -> list[keras.callbacks.Callback]:
    checkpoint_path = Path(checkpoint_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    tensorboard_log_dir = Path(tensorboard_log_dir)
    tensorboard_log_dir.mkdir(parents=True, exist_ok=True)

    return [
        keras.callbacks.EarlyStopping(
            monitor=config.early_stopping_monitor,
            mode=config.early_stopping_mode,
            patience=config.early_stopping_patience,
            restore_best_weights=True,
        ),
        keras.callbacks.ModelCheckpoint(
            filepath=str(checkpoint_path),
            monitor=config.checkpoint_monitor,
            mode=config.checkpoint_mode,
            save_best_only=True,
        ),
        keras.callbacks.LearningRateScheduler(warmup_exponential_decay_schedule(config)),
        keras.callbacks.TensorBoard(log_dir=str(tensorboard_log_dir)),
    ]
