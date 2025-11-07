"""
Average CONSUMO_REAL over dates for counters without long zero intervals.

Definition: Keep POLIZA_SUMINISTRO whose maximum consecutive days with CONSUMO_REAL = 0
           is <= zero_threshold (default: 5). Compute daily average across the
           remaining counters and plot a time series.

Usage:
  python data/plot_consumo_avg_no_long_zeros.py \
    --parquet data/data/Dades_Comptadors_anonymized.parquet \
    --output data/insights/consumo_avg_no_long_zeros.png \
    --zero_threshold 5 \
    --years 4 \
    --smooth_days 7
"""

import argparse
from pathlib import Path

import duckdb
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot average CONSUMO_REAL over dates for counters without >N consecutive zero days"
        )
    )
    parser.add_argument(
        "--parquet",
        type=str,
        default="data/data/Dades_Comptadors_anonymized.parquet",
        help="Path to parquet file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/insights/consumo_avg_no_long_zeros.png",
        help="Path to save the output figure (PNG)",
    )
    parser.add_argument(
        "--hist_output",
        type=str,
        default="data/insights/consumo_avg_no_long_zeros_hist.png",
        help="Path to save the histogram figure (PNG)",
    )
    parser.add_argument(
        "--zero_threshold",
        type=int,
        default=5,
        help="Maximum allowed consecutive zero days per counter (keep if <= this)",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=4,
        help="Number of most recent years to include (0 means all)",
    )
    parser.add_argument(
        "--smooth_days",
        type=int,
        default=7,
        help="Rolling window (days) to smooth the averaged daily series (0 to disable)",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=60,
        help="Number of bins for the histogram of average values",
    )
    parser.add_argument(
        "--max_avg",
        type=float,
        default=400.0,
        help="Exclude days where the daily average exceeds this value (treat as outliers)",
    )
    parser.add_argument(
        "--min_avg",
        type=float,
        default=280.0,
        help="Exclude days where the daily average is below this value (treat as outliers)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    parquet_path = Path(args.parquet)
    if not parquet_path.exists():
        alt = Path(__file__).with_name(parquet_path.name)
        if alt.exists():
            parquet_path = alt
        else:
            raise FileNotFoundError(f"Parquet file not found: {args.parquet}")

    con = duckdb.connect()

    # 1) Detect counters with longest consecutive zero run
    consecutive_sql = f"""
        WITH ordered_readings AS (
            SELECT 
                "POLIZA_SUMINISTRO" AS counter_id,
                FECHA::DATE AS day,
                CONSUMO_REAL,
                CASE WHEN CONSUMO_REAL = 0 THEN 1 ELSE 0 END AS is_zero,
                SUM(CASE WHEN CONSUMO_REAL = 0 THEN 0 ELSE 1 END)
                    OVER (PARTITION BY "POLIZA_SUMINISTRO" ORDER BY FECHA::DATE)
                    AS zero_group
            FROM '{parquet_path.as_posix()}'
        ),
        zero_runs AS (
            SELECT 
                counter_id,
                zero_group,
                COUNT(*) AS run_len
            FROM ordered_readings
            WHERE is_zero = 1
            GROUP BY counter_id, zero_group
        ),
        max_runs AS (
            SELECT counter_id, COALESCE(MAX(run_len), 0) AS max_zero_run
            FROM zero_runs
            GROUP BY counter_id
        )
        SELECT counter_id
        FROM max_runs
        WHERE max_zero_run <= {args.zero_threshold}
    """

    keep_counters = con.execute(consecutive_sql).df()
    if keep_counters.empty:
        print(
            "No counters meet the zero-threshold criterion. Try increasing --zero_threshold."
        )
        return

    counters_sql = ", ".join([f"'{c}'" for c in keep_counters["counter_id"].tolist()])

    # 2) Fetch readings only for kept counters
    data_sql = f"""
        SELECT 
            "POLIZA_SUMINISTRO" AS counter_id,
            FECHA::DATE AS day,
            CONSUMO_REAL
        FROM '{parquet_path.as_posix()}'
        WHERE "POLIZA_SUMINISTRO" IN ({counters_sql})
          AND CONSUMO_REAL IS NOT NULL
    """
    df = con.execute(data_sql).df()
    if df.empty:
        print("No readings found after filtering. Nothing to plot.")
        return

    # Parse date and optional year filter
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    if args.years > 0:
        end_date = df["day"].max()
        start_date = end_date - pd.DateOffset(years=args.years)
        df = df[(df["day"] >= start_date) & (df["day"] <= end_date)].copy()

    # Daily average across counters
    daily_avg = (
        df.groupby("day")["CONSUMO_REAL"].mean().reset_index(name="avg_consumo")
    )

    # Remove outlier days based on the daily average thresholds
    daily_avg = daily_avg[(daily_avg["avg_consumo"] <= args.max_avg) & (daily_avg["avg_consumo"] >= args.min_avg)].copy()

    if args.smooth_days and args.smooth_days > 1:
        daily_avg = daily_avg.sort_values("day").copy()
        daily_avg["avg_consumo_smooth"] = (
            daily_avg["avg_consumo"].rolling(args.smooth_days, min_periods=1).mean()
        )
        y_col = "avg_consumo_smooth"
        y_label = f"Average CONSUMO_REAL ({args.smooth_days}-day mean)"
    else:
        y_col = "avg_consumo"
        y_label = "Average CONSUMO_REAL"

    # Plot
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=daily_avg, x="day", y=y_col, color="#2563eb")
    plt.title(
        f"Average CONSUMO_REAL over time (<= {args.zero_threshold} zero-run, {args.min_avg}≤avg≤{args.max_avg})"
    )
    plt.xlabel("Date")
    plt.ylabel(y_label)
    plt.tight_layout()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    print(f"Saved figure to {out_path.as_posix()}")

    # Histogram of the average values that were plotted above
    values = daily_avg[y_col].dropna()
    plt.figure(figsize=(10, 6))
    sns.histplot(values, bins=args.bins, stat="count", color="#0ea5e9", edgecolor="white")
    plt.title(
        f"Histogram of daily average CONSUMO_REAL (<= {args.zero_threshold} zero-run, {args.min_avg}≤avg≤{args.max_avg})"
    )
    plt.xlabel("Average CONSUMO_REAL")
    plt.ylabel("Frequency")
    plt.tight_layout()

    hist_path = Path(args.hist_output)
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(hist_path, dpi=150)
    print(f"Saved histogram to {hist_path.as_posix()}")


if __name__ == "__main__":
    main()


