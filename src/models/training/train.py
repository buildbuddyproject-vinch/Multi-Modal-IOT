"""Training orchestration: build -> compile -> fit -> save.

Deliberately does not touch the test split -- that is reserved for
src/models/evaluation, run once after training is finished.
"""
import json
import logging
from dataclasses import asdict
from pathlib import Path

import numpy as np
import tensorflow as tf
import keras

from src.models.architectures.hybrid_model import ModelConfig, build_hybrid_model
from src.models.training.callbacks import build_callbacks
from src.models.training.compile_utils import compile_model
from src.models.training.config import TrainingConfig

logger = logging.getLogger(__name__)


def load_split(npz_path: Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(npz_path) as data:
        return data["X"], data["y"]


def train_model(
    train_npz: Path,
    val_npz: Path,
    output_dir: Path,
    model_config: ModelConfig = ModelConfig(),
    training_config: TrainingConfig = TrainingConfig(),
) -> tuple[keras.Model, dict]:
    tf.random.set_seed(training_config.random_seed)
    np.random.seed(training_config.random_seed)

    output_dir = Path(output_dir)
    checkpoint_path = output_dir / "checkpoints" / "best_model.keras"
    tensorboard_dir = output_dir / "logs" / "tensorboard"
    saved_model_path = output_dir / "saved" / "final_model.keras"

    logger.info("Loading train/val windows")
    X_train, y_train = load_split(train_npz)
    X_val, y_val = load_split(val_npz)
    logger.info("Train: %s windows, positive rate %.4f", X_train.shape[0], y_train.mean())
    logger.info("Val:   %s windows, positive rate %.4f", X_val.shape[0], y_val.mean())

    logger.info("Building and compiling model")
    model = build_hybrid_model(model_config)
    compile_model(model, training_config)

    callbacks = build_callbacks(training_config, checkpoint_path, tensorboard_dir)

    logger.info(
        "Starting training: epochs=%d, batch_size=%d, early_stopping_patience=%d",
        training_config.epochs, training_config.batch_size, training_config.early_stopping_patience,
    )
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        batch_size=training_config.batch_size,
        epochs=training_config.epochs,
        callbacks=callbacks,
        verbose=2,
    )

    saved_model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(saved_model_path)
    logger.info("Saved final model -> %s", saved_model_path)

    history_dict = {k: [float(v) for v in vals] for k, vals in history.history.items()}
    history_path = output_dir / "logs" / "training_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps({
        "history": history_dict,
        "model_config": asdict(model_config),
        "training_config": asdict(training_config),
        "epochs_ran": len(history_dict.get("loss", [])),
        "checkpoint_path": str(checkpoint_path),
        "saved_model_path": str(saved_model_path),
    }, indent=2))
    logger.info("Saved training history -> %s", history_path)

    return model, history_dict
