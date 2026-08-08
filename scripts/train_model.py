"""Step 5 CLI entry point: train the hybrid model on the Step 2 PhysioNet windows,
then evaluate on the held-out test split and save every artifact.

Usage: python scripts/train_model.py [--epochs N] [--batch-size N] [--quick]
"""
import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_settings
from src.models.architectures.hybrid_model import ModelConfig
from src.models.evaluation.evaluate import evaluate_model
from src.models.training.config import TrainingConfig
from src.models.training.train import train_model


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate the Step 5 hybrid sepsis model")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--patience", type=int, default=None)
    parser.add_argument("--quick", action="store_true", help="Tiny run for a fast sanity check, not real training")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    processed_dir = settings.processed_dir / "physionet2019"
    output_dir = settings.resolve_path("./models")

    training_config = TrainingConfig()
    overrides = {}
    if args.epochs is not None:
        overrides["epochs"] = args.epochs
    if args.batch_size is not None:
        overrides["batch_size"] = args.batch_size
    if args.patience is not None:
        overrides["early_stopping_patience"] = args.patience
    if args.quick:
        overrides.setdefault("epochs", 2)
        overrides.setdefault("early_stopping_patience", 2)
    if overrides:
        training_config = replace(training_config, **overrides)

    print(f"Training config: {training_config}")
    model, history = train_model(
        train_npz=processed_dir / "train.npz",
        val_npz=processed_dir / "val.npz",
        output_dir=output_dir,
        model_config=ModelConfig(),
        training_config=training_config,
    )

    report = evaluate_model(
        model=model,
        test_npz=processed_dir / "test.npz",
        output_dir=output_dir / "evaluation",
        history=history,
    )
    print("Test set evaluation:")
    print(f"  AUROC: {report['auroc']:.4f}  AUPRC: {report['auprc']:.4f}")
    print(f"  @0.5 threshold      -> precision={report['metrics_at_0.5']['precision']:.4f} "
          f"recall={report['metrics_at_0.5']['recall_sensitivity']:.4f} "
          f"specificity={report['metrics_at_0.5']['specificity']:.4f} "
          f"f1={report['metrics_at_0.5']['f1_score']:.4f}")
    best = report["metrics_at_best_f1_threshold"]
    print(f"  @best-F1 threshold  -> t={best['threshold']:.3f} precision={best['precision']:.4f} "
          f"recall={best['recall_sensitivity']:.4f} specificity={best['specificity']:.4f} f1={best['f1_score']:.4f}")
    print(f"\nArtifacts saved under {output_dir}")


if __name__ == "__main__":
    main()
