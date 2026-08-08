"""Training hyperparameters, kept separate from the architecture (ModelConfig) so
Step 5 can sweep these without touching the model definition."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TrainingConfig:
    # batch_size=1024 was chosen from a CPU throughput benchmark (see Step 5 notes):
    # ~126s/epoch on the full 888,791-window train set vs. ~436s/epoch at batch_size=256.
    batch_size: int = 1024
    epochs: int = 30
    learning_rate: float = 1e-3
    focal_loss_alpha: float = 0.25
    focal_loss_gamma: float = 2.0
    early_stopping_patience: int = 5
    early_stopping_monitor: str = "val_auroc"
    early_stopping_mode: str = "max"
    lr_schedule_warmup_epochs: int = 3
    lr_schedule_decay_rate: float = 0.95
    checkpoint_monitor: str = "val_auroc"
    checkpoint_mode: str = "max"
    random_seed: int = 42
