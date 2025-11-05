"""
Average CONSUMO_REAL over dates: ALL users vs DOMESTIC (D) users comparison.

Plots both all users and domestic users on the same graphs for comparison.
No zero-run or min/max filters applied.

Usage:
  python data/plot_consumo_avg_all.py \
    --parquet data/Dades_Comptadors_anonymized.parquet \
    --output data/consumo_avg_all.png \
    --hist_output data/consumo_avg_all_hist.png \
    --years 4 \
    --smooth_days 7 \
    --bins 60
"""

import argparse
from pathlib import Path

import duckdb
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot average CONSUMO_REAL over time (all users vs domestic users)")
    p.add_argument(
        "--parquet",
        type=str,
        default="data/Dades_Comptadors_anonymized.parquet",
        help="Path to parquet file",
    )
    p.add_argument(
        "--output",
        type=str,
        default="data/consumo_avg_all.png",
        help="Path to save the time-series figure",
    )
    p.add_argument(
        "--hist_output",
        type=str,
        default="data/consumo_avg_all_hist.png",
        help="Path to save the histogram figure",
    )
    p.add_argument("--years", type=int, default=4, help="Number of most recent years to include (0 = all)")
    p.add_argument(
        "--smooth_days",
        type=int,
        default=7,
        help="Rolling window (days) to smooth the averaged daily series (0 to disable)",
    )
    p.add_argument("--bins", type=int, default=60, help="Bins for the histogram")
    return p.parse_args()


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

    # Query for all users
    sql_all = f"""
        SELECT 
            FECHA::DATE AS day,
            CONSUMO_REAL,
            'All users' AS user_type
        FROM '{parquet_path.as_posix()}'
        WHERE CONSUMO_REAL IS NOT NULL
    """
    
    # Query for domestic users only
    sql_domestic = f"""
        SELECT 
            FECHA::DATE AS day,
            CONSUMO_REAL,
            'Domestic (D)' AS user_type
        FROM '{parquet_path.as_posix()}'
        WHERE CONSUMO_REAL IS NOT NULL
          AND "US_AIGUA_GEST" = 'D'
    """
    
    df_all = con.execute(sql_all).df()
    df_domestic = con.execute(sql_domestic).df()
    
    if df_all.empty and df_domestic.empty:
        print("No data found in the provided parquet.")
        return
    
    # Combine both datasets
    df = pd.concat([df_all, df_domestic], ignore_index=True)
    
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    if args.years > 0:
        end_date = df["day"].max()
        start_date = end_date - pd.DateOffset(years=args.years)
        df = df[(df["day"] >= start_date) & (df["day"] <= end_date)].copy()

    # Daily average per user type
    daily_avg = df.groupby(["day", "user_type"])["CONSUMO_REAL"].mean().reset_index(name="avg_consumo")

    # Apply smoothing per user type
    if args.smooth_days and args.smooth_days > 1:
        daily_avg = daily_avg.sort_values(["user_type", "day"]).copy()
        daily_avg["avg_consumo_smooth"] = (
            daily_avg.groupby("user_type")["avg_consumo"]
            .transform(lambda s: s.rolling(args.smooth_days, min_periods=1).mean())
        )
        y_col = "avg_consumo_smooth"
        y_label = f"Average CONSUMO_REAL ({args.smooth_days}-day mean)"
    else:
        y_col = "avg_consumo"
        y_label = "Average CONSUMO_REAL"

    # Plot line - both on same graph
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=daily_avg, x="day", y=y_col, hue="user_type", palette=["#2563eb", "#10b981"])
    plt.title("Average CONSUMO_REAL over time (all users vs domestic users)")
    plt.xlabel("Date")
    plt.ylabel(y_label)
    plt.legend(title="User type")
    plt.tight_layout()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150)
    print(f"Saved figure to {out.as_posix()}")

    # Histogram - both on same graph
    plt.figure(figsize=(10, 6))
    for user_type, color in [("All users", "#2563eb"), ("Domestic (D)", "#10b981")]:
        values = daily_avg[daily_avg["user_type"] == user_type][y_col].dropna()
        if not values.empty:
            sns.histplot(values, bins=args.bins, stat="count", label=user_type, 
                        alpha=0.6, color=color, edgecolor="white")
    plt.title("Histogram of daily average CONSUMO_REAL (all users vs domestic users)")
    plt.xlabel("Average CONSUMO_REAL")
    plt.ylabel("Frequency")
    plt.legend(title="User type")
    plt.tight_layout()
    hist_out = Path(args.hist_output)
    hist_out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(hist_out, dpi=150)
    print(f"Saved histogram to {hist_out.as_posix()}")


if __name__ == "__main__":
    main()



