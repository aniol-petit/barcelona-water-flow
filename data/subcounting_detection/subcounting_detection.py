"""
Subcounting detection utilities.

This module computes a robust, interpretable subcounting score for each meter
based on its consumption time series. The score is designed to be combined
with the existing Stage 4 risk probabilities.

High-level steps:
1. Load daily consumption from DuckDB views (`consumption_data`).
2. Aggregate to monthly consumption per meter and smooth.
3. Normalise each meter's monthly series by a peer/cluster median.
4. Compute three complementary indicators:
   - Long-term drop ratio (recent vs baseline).
   - Linear trend on the normalised series.
   - Change in slope between first and second half of the series.
5. Combine these indicators into a subcounting score in [0, 1].
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import duckdb
import numpy as np
import pandas as pd


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "analytics.duckdb"


@dataclass
class SubcountingConfig:
    """
    Configuration parameters for subcounting detection.
    """

    # Temporal aggregation
    freq: str = "M"  # Monthly aggregation ('W' for weekly)
    min_months: int = 12  # Minimum number of aggregated periods required

    # Windows (measured in aggregated periods: months or weeks)
    baseline_window: int = 12  # Length of baseline window
    recent_window: int = 6  # Length of recent window

    # Peer normalisation
    use_cluster_peers: bool = False  # If True, normalise by cluster median

    # Sub-score weighting
    w_ratio: float = 0.4
    w_trend: float = 0.3
    w_slope_change: float = 0.3

    # Optional: cap the influence of subcounting when combining with base risk
    gamma: float = 0.8


def load_consumption_data(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """
    Load daily consumption data for domestic meters from DuckDB.

    Returns
    -------
    pandas.DataFrame
        Columns: meter_id, date, consumo_real
    """
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {path}. "
            "Run data/create_database.py to generate analytics.duckdb."
        )

    con = duckdb.connect(database=str(path), read_only=True)

    sql = """
        SELECT
            cd."POLIZA_SUMINISTRO"::VARCHAR AS meter_id,
            CAST(cd.FECHA AS DATE) AS date,
            cd.CONSUMO_REAL AS consumo_real
        FROM consumption_data cd
        JOIN counter_metadata cm
            ON cd."POLIZA_SUMINISTRO" = cm."POLIZA_SUMINISTRO"
        WHERE cm.US_AIGUA_GEST = 'D'
    """

    df = con.execute(sql).df()
    con.close()

    if df.empty:
        raise ValueError("No domestic consumption data found in consumption_data view.")

    df["date"] = pd.to_datetime(df["date"])

    return df


def _aggregate_monthly_consumption(
    df: pd.DataFrame,
    freq: str = "M",
) -> pd.DataFrame:
    """
    Aggregate daily consumption to monthly (or weekly) per meter.

    Parameters
    ----------
    df : pd.DataFrame
        Columns: meter_id, date, consumo_real
    freq : str
        Pandas offset alias ('M' for month-end, 'W' for weekly, etc.).

    Returns
    -------
    pd.DataFrame
        Columns: meter_id, period, consumo
    """
    df = df.copy()
    df["period"] = df["date"].dt.to_period(freq).dt.to_timestamp()

    agg = (
        df.groupby(["meter_id", "period"], as_index=False)["consumo_real"]
        .sum()
        .rename(columns={"consumo_real": "consumo"})
    )

    return agg


def _compute_peer_normalisation(
    df_monthly: pd.DataFrame,
    cluster_labels: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Compute peer-normalised monthly series.

    If cluster_labels is provided, normalisation is done within each cluster.
    Otherwise, a global median across all meters is used per period.

    Parameters
    ----------
    df_monthly : pd.DataFrame
        Columns: meter_id, period, consumo
    cluster_labels : pd.DataFrame, optional
        Columns: meter_id, cluster_label

    Returns
    -------
    pd.DataFrame
        Columns: meter_id, period, consumo, peer_median, x_norm
    """
    df = df_monthly.copy()

    if cluster_labels is not None:
        df = df.merge(cluster_labels, on="meter_id", how="left")
        if "cluster_label" not in df.columns:
            raise ValueError("cluster_labels must contain 'meter_id' and 'cluster_label' columns.")

        peer = (
            df.groupby(["cluster_label", "period"])["consumo"]
            .median()
            .rename("peer_median")
            .reset_index()
        )
        df = df.merge(peer, on=["cluster_label", "period"], how="left")
    else:
        peer = (
            df.groupby("period")["consumo"]
            .median()
            .rename("peer_median")
            .reset_index()
        )
        df = df.merge(peer, on="period", how="left")

    eps = 1e-6
    df["x_norm"] = df["consumo"] / (df["peer_median"] + eps)

    return df


def _compute_long_term_drop_ratio(
    series: pd.Series,
    min_points: int,
    baseline_window: int,
    recent_window: int,
) -> float:
    """
    Compute long-term drop ratio R = mean_recent / mean_baseline.
    """
    if len(series) < min_points:
        return 1.0

    recent = series.iloc[-recent_window:]
    baseline = series.iloc[max(0, len(series) - recent_window - baseline_window) : -recent_window]

    if len(baseline) == 0:
        return 1.0

    mean_recent = recent.mean()
    mean_baseline = baseline.mean()

    if mean_baseline <= 0:
        return 1.0

    return float(mean_recent / mean_baseline)


def _compute_trend_slope(series: pd.Series) -> float:
    """
    Compute linear trend slope on a time-indexed series.
    Returns the slope (change per period).
    """
    if len(series) < 3:
        return 0.0

    y = series.values.astype(float)
    x = np.arange(len(y), dtype=float)
    x_mean = x.mean()
    y_mean = y.mean()

    denom = np.sum((x - x_mean) ** 2)
    if denom <= 0:
        return 0.0

    slope = float(np.sum((x - x_mean) * (y - y_mean)) / denom)
    return slope


def _compute_slope_change(series: pd.Series) -> float:
    """
    Compute relative slope change between first and second half of the series.

    Returns
    -------
    float
        Ratio s_second / s_first. Values < 1 indicate a slowdown.
    """
    n = len(series)
    if n < 6:
        return 1.0

    mid = n // 2
    first = series.iloc[:mid]
    second = series.iloc[mid:]

    s_first = _compute_trend_slope(first)
    s_second = _compute_trend_slope(second)

    if abs(s_first) < 1e-6:
        return 1.0

    return float(s_second / s_first)


def _score_from_ratio(R: float) -> float:
    """
    Map drop ratio R to sub-score s_R in [0, 1].
    """
    if R <= 0.5:
        return 1.0
    if R >= 0.8:
        return 0.0
    return float((0.8 - R) / (0.8 - 0.5))


def _score_from_slope(slope: float, series: pd.Series) -> float:
    """
    Map trend slope to sub-score s_T in [0, 1].

    We normalise the slope by the median level of the series to make it
    approximately scale-invariant.
    """
    if len(series) < 6:
        return 0.0

    median_level = np.median(series.values)
    if median_level <= 0:
        return 0.0

    # Normalised slope: relative change per period
    rel_slope = slope / median_level

    # Heuristic thresholds (tunable):
    #   rel_slope <= -0.05 -> strong negative trend  (score 1)
    #   rel_slope >= 0     -> no negative trend      (score 0)
    if rel_slope >= 0:
        return 0.0
    if rel_slope <= -0.05:
        return 1.0

    # Linear interpolation between 0 and -0.05
    return float((-rel_slope) / 0.05)


def _score_from_slope_change(delta_s: float) -> float:
    """
    Map slope ratio s_second / s_first to sub-score s_delta in [0, 1].
    """
    if delta_s <= 0.5:
        return 1.0
    if delta_s >= 0.8:
        return 0.0
    return float((0.8 - delta_s) / (0.8 - 0.5))


def compute_subcounting_metrics(
    df_monthly_norm: pd.DataFrame,
    config: Optional[SubcountingConfig] = None,
) -> pd.DataFrame:
    """
    Compute per-meter subcounting metrics from normalised monthly data.

    Parameters
    ----------
    df_monthly_norm : pd.DataFrame
        Columns: meter_id, period, consumo, peer_median, x_norm
    config : SubcountingConfig, optional
        Configuration object.

    Returns
    -------
    pd.DataFrame
        One row per meter with metrics:
        - meter_id
        - n_periods
        - R (drop ratio)
        - slope
        - delta_s (s_second / s_first)
        - s_R, s_T, s_delta (sub-scores)
        - subcount_score (combined in [0, 1])
    """
    if config is None:
        config = SubcountingConfig()

    records = []

    grouped = df_monthly_norm.sort_values(["meter_id", "period"]).groupby("meter_id")

    for meter_id, grp in grouped:
        x = grp["x_norm"]
        n = len(x)

        R = _compute_long_term_drop_ratio(
            x,
            min_points=config.min_months,
            baseline_window=config.baseline_window,
            recent_window=config.recent_window,
        )
        slope = _compute_trend_slope(x)
        delta_s = _compute_slope_change(x)

        s_R = _score_from_ratio(R)
        s_T = _score_from_slope(slope, x)
        s_delta = _score_from_slope_change(delta_s)

        subcount_score = (
            config.w_ratio * s_R
            + config.w_trend * s_T
            + config.w_slope_change * s_delta
        )

        # Simple logical reinforcement:
        strong_signals = sum(score > 0.7 for score in (s_R, s_T, s_delta))
        if strong_signals >= 2:
            subcount_score = max(subcount_score, 0.7)

        records.append(
            {
                "meter_id": meter_id,
                "n_periods": n,
                "R": R,
                "slope": slope,
                "delta_s": delta_s,
                "s_R": s_R,
                "s_T": s_T,
                "s_delta": s_delta,
                "subcount_score_raw": subcount_score,
            }
        )

    df_metrics = pd.DataFrame(records)

    # Normalise raw subcount_score to [0, 1] across meters for comparability
    if not df_metrics.empty:
        vals = df_metrics["subcount_score_raw"].values
        v_min, v_max = vals.min(), vals.max()
        if v_max > v_min:
            df_metrics["subcount_score"] = (vals - v_min) / (v_max - v_min)
        else:
            df_metrics["subcount_score"] = 0.0
    else:
        df_metrics["subcount_score"] = []

    return df_metrics


def compute_subcounting_scores(
    db_path: str | Path = DEFAULT_DB_PATH,
    cluster_labels: Optional[pd.DataFrame] = None,
    config: Optional[SubcountingConfig] = None,
) -> pd.DataFrame:
    """
    High-level helper: load data, aggregate, normalise, and compute scores.

    Parameters
    ----------
    db_path : str | Path
        Path to DuckDB database.
    cluster_labels : pd.DataFrame, optional
        If provided, used to compute cluster-wise peer medians.
        Columns: meter_id, cluster_label
    config : SubcountingConfig, optional
        Configuration parameters.

    Returns
    -------
    pd.DataFrame
        One row per meter with subcounting metrics and scores.
    """
    if config is None:
        config = SubcountingConfig()

    df_daily = load_consumption_data(db_path=db_path)
    df_monthly = _aggregate_monthly_consumption(df_daily, freq=config.freq)

    if config.use_cluster_peers and cluster_labels is not None:
        df_monthly_norm = _compute_peer_normalisation(df_monthly, cluster_labels=cluster_labels)
    else:
        df_monthly_norm = _compute_peer_normalisation(df_monthly, cluster_labels=None)

    df_metrics = compute_subcounting_metrics(df_monthly_norm, config=config)
    return df_metrics


