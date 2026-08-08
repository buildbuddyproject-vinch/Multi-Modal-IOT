"""Step 2 CLI entry point: run the dataset preprocessing pipeline.

Examples
--------
python scripts/run_preprocessing.py physionet
python scripts/run_preprocessing.py physionet --limit 2000 --window-size 8 --stride 1
python scripts/run_preprocessing.py mimic
python scripts/run_preprocessing.py all
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_settings
from src.data.preprocessing.pipeline import run_mimic_iv_pipeline, run_physionet_pipeline


def main():
    parser = argparse.ArgumentParser(description="Run Step 2 dataset preprocessing")
    parser.add_argument("dataset", choices=["physionet", "mimic", "all"])
    parser.add_argument("--limit", type=int, default=None, help="Limit number of PhysioNet patient files (for fast dev runs)")
    parser.add_argument("--window-size", type=int, default=8)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--val-size", type=float, default=0.15)
    parser.add_argument("--test-size", type=float, default=0.15)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--quiet", action="store_true", help="Disable per-file progress bars")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    if args.dataset in ("physionet", "all"):
        metadata = run_physionet_pipeline(
            raw_dir=settings.physionet_dir,
            output_dir=settings.processed_dir / "physionet2019",
            limit=args.limit,
            window_size=args.window_size,
            stride=args.stride,
            val_size=args.val_size,
            test_size=args.test_size,
            random_state=args.random_state,
            show_progress=not args.quiet,
        )
        print("PhysioNet pipeline complete. Counts:", metadata["counts"])

    if args.dataset in ("mimic", "all"):
        report = run_mimic_iv_pipeline(
            raw_dir=settings.mimic_iv_dir,
            output_dir=settings.processed_dir / "mimic_iv",
        )
        print(f"MIMIC-IV Demo pipeline complete. {report['n_patients']} patients, "
              f"{report['n_vitals_rows']} vitals rows, "
              f"{len(report['unresolved_channels'])} unresolved channels: {report['unresolved_channels']}")


if __name__ == "__main__":
    main()
