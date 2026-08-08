"""Step 3 CLI entry point: run exploratory data analysis and save graphs/stats.

Examples
--------
python scripts/run_eda.py                      # full PhysioNet + MIMIC-IV EDA
python scripts/run_eda.py --limit 5000          # faster dev run on a PhysioNet subset
python scripts/run_eda.py --skip-mimic
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.config.settings import get_settings
from src.data.loaders.physionet_loader import load_physionet_dataset
from src.data.schema import CLINICAL_CHANNELS, LABEL_COLUMN, PATIENT_ID_COLUMN, TIME_COLUMN
from src.eda.correlation import compute_correlation_matrix, top_correlated_pairs
from src.eda.feature_importance import compute_random_forest_importance, load_last_timestep_features
from src.eda.mimic_eda import channel_coverage, patient_demographics_summary
from src.eda.missingness import missingness_by_patient_summary, missingness_report
from src.eda.plots import (
    plot_correlation_heatmap,
    plot_distributions_grid,
    plot_feature_importance_bar,
    plot_missingness_bar,
    plot_patient_timeseries,
)
from src.eda.statistics import compute_descriptive_stats, compute_label_group_stats

logger = logging.getLogger(__name__)

EXAMPLE_TIMESERIES_CHANNELS = ["HR", "Resp", "MAP", "O2Sat", "Temp"]


def pick_example_patients(df: pd.DataFrame, n_per_group: int = 2, min_timesteps: int = 20) -> list[str]:
    per_patient = df.groupby(PATIENT_ID_COLUMN).agg(n_rows=(TIME_COLUMN, "size"), ever_septic=(LABEL_COLUMN, "max"))
    eligible = per_patient[per_patient["n_rows"] >= min_timesteps]
    septic = eligible[eligible["ever_septic"] == 1].head(n_per_group).index.tolist()
    healthy = eligible[eligible["ever_septic"] == 0].head(n_per_group).index.tolist()
    return septic + healthy


def run_physionet_eda(raw_dir: Path, processed_dir: Path, output_dir: Path, limit: int | None) -> dict:
    stats_dir, plots_dir = output_dir / "stats", output_dir / "plots"
    stats_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading raw PhysioNet data for EDA (limit=%s)", limit)
    df = load_physionet_dataset(raw_dir, limit=limit, show_progress=True)

    logger.info("Computing descriptive statistics")
    desc_stats = compute_descriptive_stats(df, CLINICAL_CHANNELS)
    desc_stats.to_csv(stats_dir / "descriptive_statistics.csv", index=False)

    label_stats = compute_label_group_stats(df, CLINICAL_CHANNELS, LABEL_COLUMN)
    label_stats.to_csv(stats_dir / "label_group_statistics.csv", index=False)

    logger.info("Computing missingness report")
    missing = missingness_report(df, CLINICAL_CHANNELS)
    missing.to_csv(stats_dir / "missingness_report.csv", index=False)
    plot_missingness_bar(missing, plots_dir / "missingness_by_channel.png")

    per_patient_missing = missingness_by_patient_summary(df, CLINICAL_CHANNELS, PATIENT_ID_COLUMN)
    per_patient_missing.to_csv(stats_dir / "missingness_by_patient.csv", index=False)

    logger.info("Computing correlation matrix")
    corr = compute_correlation_matrix(df, CLINICAL_CHANNELS)
    corr.to_csv(stats_dir / "correlation_matrix.csv")
    plot_correlation_heatmap(corr, plots_dir / "correlation_heatmap.png")
    top_pairs = top_correlated_pairs(corr, top_n=15)
    top_pairs.to_csv(stats_dir / "top_correlated_pairs.csv", index=False)

    logger.info("Plotting channel distributions by SepsisLabel")
    plot_distributions_grid(df, CLINICAL_CHANNELS, LABEL_COLUMN, plots_dir / "distributions_by_label.png")

    logger.info("Plotting example patient time-series")
    example_patients = pick_example_patients(df)
    importance = None
    if example_patients:
        plot_patient_timeseries(df, PATIENT_ID_COLUMN, TIME_COLUMN, EXAMPLE_TIMESERIES_CHANNELS, example_patients, plots_dir / "example_patient_timeseries.png")

    train_npz = processed_dir / "train.npz"
    if train_npz.exists():
        logger.info("Computing RandomForest feature importance from %s", train_npz)
        X, y = load_last_timestep_features(train_npz)
        importance = compute_random_forest_importance(X, y, CLINICAL_CHANNELS)
        importance.to_csv(stats_dir / "feature_importance.csv", index=False)
        plot_feature_importance_bar(importance, plots_dir / "feature_importance.png")
    else:
        logger.warning("No processed train.npz found at %s -- run scripts/run_preprocessing.py first for feature importance", train_npz)

    return {
        "n_rows": len(df),
        "n_patients": int(df[PATIENT_ID_COLUMN].nunique()),
        "positive_rate": float(df.groupby(PATIENT_ID_COLUMN)[LABEL_COLUMN].max().mean()),
        "top_missing_channel": missing.iloc[0]["channel"],
        "top_correlated_pair": f"{top_pairs.iloc[0]['feature_a']} / {top_pairs.iloc[0]['feature_b']}" if len(top_pairs) else None,
        "top_important_channel": importance.iloc[0]["channel"] if importance is not None else None,
        "example_patients": example_patients,
    }


def run_mimic_eda(processed_mimic_dir: Path, output_dir: Path) -> dict:
    stats_dir, plots_dir = output_dir / "stats", output_dir / "plots"
    stats_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    patients_path = processed_mimic_dir / "patients.parquet"
    vitals_path = processed_mimic_dir / "vitals_long.parquet"
    if not (patients_path.exists() and vitals_path.exists()):
        logger.warning("MIMIC-IV processed data not found at %s -- run scripts/run_preprocessing.py mimic first", processed_mimic_dir)
        return {}

    patients = pd.read_parquet(patients_path)
    vitals = pd.read_parquet(vitals_path)

    coverage = channel_coverage(vitals)
    coverage.to_csv(stats_dir / "mimic_channel_coverage.csv", index=False)

    demographics = patient_demographics_summary(patients)
    (stats_dir / "mimic_demographics.json").write_text(json.dumps(demographics, indent=2))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    fig, ax = plt.subplots(figsize=(8, 8))
    sns.barplot(data=coverage, y="channel", x="n_readings", ax=ax, color="#8172B2")
    ax.set_title("MIMIC-IV Demo: Readings per Channel")
    fig.tight_layout()
    fig.savefig(plots_dir / "mimic_channel_coverage.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {"n_patients": demographics["n_patients"], "n_channels_covered": len(coverage)}


def write_summary_report(output_dir: Path, physionet_summary: dict, mimic_summary: dict) -> None:
    lines = [
        "# EDA Summary Report (Step 3)",
        "",
        "## PhysioNet 2019 (training/validation/testing source)",
        f"- Rows analyzed: {physionet_summary.get('n_rows')}",
        f"- Patients analyzed: {physionet_summary.get('n_patients')}",
        f"- Patient-level sepsis prevalence: {physionet_summary.get('positive_rate'):.4f}" if physionet_summary.get("positive_rate") is not None else "",
        f"- Channel with most missing data: {physionet_summary.get('top_missing_channel')}",
        f"- Strongest correlated pair: {physionet_summary.get('top_correlated_pair')}",
        f"- Most important channel (RandomForest baseline): {physionet_summary.get('top_important_channel')}",
        f"- Example patients plotted: {physionet_summary.get('example_patients')}",
        "",
        "## MIMIC-IV Demo (schema/dashboard testing source)",
        f"- Patients: {mimic_summary.get('n_patients', 'N/A')}",
        f"- Channels with real coverage: {mimic_summary.get('n_channels_covered', 'N/A')}",
        "",
        "See stats/*.csv and plots/*.png for full detail.",
    ]
    (output_dir / "summary_report.md").write_text("\n".join(line for line in lines if line is not None))


def main():
    parser = argparse.ArgumentParser(description="Run Step 3 exploratory data analysis")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of PhysioNet patient files (for fast dev runs)")
    parser.add_argument("--skip-mimic", action="store_true")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    project_root = Path(__file__).resolve().parents[1]
    output_dir = Path(args.output_dir) if args.output_dir else project_root / "notebooks" / "eda" / "outputs"

    physionet_summary = run_physionet_eda(
        raw_dir=settings.physionet_dir,
        processed_dir=settings.processed_dir / "physionet2019",
        output_dir=output_dir,
        limit=args.limit,
    )
    print("PhysioNet EDA summary:", physionet_summary)

    mimic_summary = {}
    if not args.skip_mimic:
        mimic_summary = run_mimic_eda(settings.processed_dir / "mimic_iv", output_dir)
        print("MIMIC-IV EDA summary:", mimic_summary)

    write_summary_report(output_dir, physionet_summary, mimic_summary)
    print(f"Summary report written to {output_dir / 'summary_report.md'}")


if __name__ == "__main__":
    main()
