"""Channel-to-channel correlation analysis (pairwise-complete, so raw data with
missing values can be used directly without imputation bias)."""
import pandas as pd


def compute_correlation_matrix(df: pd.DataFrame, channels: list[str], method: str = "pearson") -> pd.DataFrame:
    return df[channels].corr(method=method, min_periods=30)


def top_correlated_pairs(corr: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Strongest channel pairs by absolute correlation, excluding the diagonal and
    duplicate (a,b)/(b,a) pairs."""
    pairs = []
    channels = corr.columns.tolist()
    for i, a in enumerate(channels):
        for b in channels[i + 1:]:
            value = corr.loc[a, b]
            if pd.notna(value):
                pairs.append({"feature_a": a, "feature_b": b, "correlation": value})
    pairs_df = pd.DataFrame(pairs)
    pairs_df["abs_correlation"] = pairs_df["correlation"].abs()
    return pairs_df.sort_values("abs_correlation", ascending=False).head(top_n).drop(columns="abs_correlation").reset_index(drop=True)
