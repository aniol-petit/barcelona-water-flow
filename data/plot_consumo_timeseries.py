"""
Time-series plot of CONSUMO_REAL over dates for selected counters (last N years).

Usage:
  python data/plot_consumo_timeseries.py \
    --parquet data/Dades_Comptadors_anonymized.parquet \
    --output data/consumo_timeseries.png \
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
    parser = argparse.ArgumentParser(description="Plot CONSUMO_REAL time series for counters")
    parser.add_argument(
        "--parquet",
        type=str,
        default="data/Dades_Comptadors_anonymized.parquet",
        help="Path to parquet file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/consumo_timeseries.png",
        help="Output image path",
    )
    parser.add_argument(
        "--counters",
        nargs="*",
        default=[
            "VECWAVDUULZDSBOP",

            #"RNWNF3RD2ANYMX5L",
            #"67BOUTIYOJRL6DFG",
            #"FB6OJEB34IWJB5E6",
        ],
        
        help="List of POLIZA_SUMINISTRO ids",
    )
    parser.add_argument("--years", type=int, default=4, help="How many most recent years")
    parser.add_argument(
        "--smooth_days",
        type=int,
        default=7,
        help="Rolling window (days) to smooth the daily series",
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

    counters_sql = ", ".join([f"'{c}'" for c in args.counters]) or "''"
    query = f"""
        SELECT 
            "POLIZA_SUMINISTRO" AS counter_id,
            FECHA,
            CONSUMO_REAL
        FROM '{parquet_path.as_posix()}'
        WHERE "POLIZA_SUMINISTRO" IN ({counters_sql})
          AND CONSUMO_REAL IS NOT NULL
    """

    df = con.execute(query).df()
    if df.empty:
        print("No data for the selected counters.")
        return

    df["FECHA"] = pd.to_datetime(df["FECHA"]).dt.tz_localize(None)

    # Filter to last N years
    if args.years > 0:
        end_date = df["FECHA"].max()
        start_date = end_date - pd.DateOffset(years=args.years)
        df = df[(df["FECHA"] >= start_date) & (df["FECHA"] <= end_date)].copy()

    # Daily mean per counter, then rolling smoothing
    df.set_index("FECHA", inplace=True)
    daily = (
        df.groupby("counter_id")["CONSUMO_REAL"]
        .resample("1D")
        .mean()
        .reset_index()
    )
    if args.smooth_days and args.smooth_days > 1:
        daily["CONSUMO_SMOOTH"] = (
            daily.sort_values(["counter_id", "FECHA"])  # ensure order
            .groupby("counter_id")["CONSUMO_REAL"]
            .transform(lambda s: s.rolling(args.smooth_days, min_periods=1).mean())
        )
        y_col = "CONSUMO_SMOOTH"
    else:
        y_col = "CONSUMO_REAL"

    plt.figure(figsize=(12, 6))
    sns.lineplot(data=daily, x="FECHA", y=y_col, hue="counter_id")
    plt.title(
        f"CONSUMO_REAL over time (last {args.years} years) for selected counters"
    )
    plt.xlabel("Date")
    plt.ylabel("CONSUMO_REAL")
    plt.tight_layout()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150)
    print(f"Saved figure to {out.as_posix()}")


if __name__ == "__main__":
    main()


