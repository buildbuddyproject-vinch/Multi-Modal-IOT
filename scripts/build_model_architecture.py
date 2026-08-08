"""Step 4 CLI entry point: build the hybrid model with the default (Step 2 schema
matched) configuration, verify it, and save the architecture -- no training.

Usage: python scripts/build_model_architecture.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import tensorflow as tf

from src.models.architectures.hybrid_model import ModelConfig, build_hybrid_model
from src.models.training.compile_utils import compile_model
from src.models.training.config import TrainingConfig

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "models" / "saved" / "architecture"


def main():
    model_config = ModelConfig()
    training_config = TrainingConfig()

    print(f"Building model with config: {model_config}")
    model = build_hybrid_model(model_config)
    compile_model(model, training_config)

    print(model.summary())

    x = tf.random.normal((4, model_config.window_size, model_config.n_channels))
    y = model(x, training=False).numpy()
    assert y.shape == (4, 1), f"unexpected output shape {y.shape}"
    assert np.all((y >= 0.0) & (y <= 1.0)), "sigmoid output out of [0,1] range"
    print(f"Forward-pass smoke test OK. Sample outputs: {y.ravel()}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUTPUT_DIR / "model_architecture.json").write_text(model.to_json(indent=2))

    summary_lines: list[str] = []
    model.summary(print_fn=lambda line: summary_lines.append(line))
    (OUTPUT_DIR / "model_summary.txt").write_text("\n".join(summary_lines))

    config_report = {
        "model_config": model_config.__dict__,
        "training_config": training_config.__dict__,
        "total_params": model.count_params(),
        "trainable_params": sum(int(tf.size(w)) for w in model.trainable_weights),
        "n_layers": len(model.layers),
    }
    (OUTPUT_DIR / "config_report.json").write_text(json.dumps(config_report, indent=2, default=str))

    print(f"\nSaved architecture artifacts to {OUTPUT_DIR}")
    print(f"Total params: {config_report['total_params']:,} (trainable: {config_report['trainable_params']:,})")


if __name__ == "__main__":
    main()
