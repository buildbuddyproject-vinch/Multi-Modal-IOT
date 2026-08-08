"""Wires a built (uncompiled) model to its optimizer, loss, and metrics."""
import keras

from src.models.training.config import TrainingConfig
from src.models.training.losses import BinaryFocalLoss


def compile_model(model: keras.Model, config: TrainingConfig = TrainingConfig()) -> keras.Model:
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=config.learning_rate),
        loss=BinaryFocalLoss(alpha=config.focal_loss_alpha, gamma=config.focal_loss_gamma),
        metrics=[
            keras.metrics.AUC(name="auroc", curve="ROC"),
            keras.metrics.AUC(name="auprc", curve="PR"),
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
            keras.metrics.BinaryAccuracy(name="accuracy"),
        ],
    )
    return model
