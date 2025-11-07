"""
Time-series plot of CONSUMO_REAL over dates for selected counters (last N years).

Usage:
  python data/plot_consumo_timeseries.py \
    --parquet data/data/Dades_Comptadors_anonymized.parquet \
    --output data/insights/consumo_timeseries.png \
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
        default="data/data/Dades_Comptadors_anonymized.parquet",
        help="Path to parquet file (will auto-detect if not found)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="insights/consumo_timeseries.png",
        help="Output image path",
    )
    parser.add_argument(
        "--counters",
        nargs="*",
        default=[
            "2SAGBLJAUEXGZNPM",  # Rank 10: Score 90.8, max ratio 134x
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
    
    # Try to find the parquet file in multiple locations
    if not parquet_path.exists():
        # Try relative to script location (data/data/)
        script_dir = Path(__file__).parent
        alt1 = script_dir / "data" / "Dades_Comptadors_anonymized.parquet"
        
        # Try relative to project root (data/data/)
        project_root = script_dir.parent
        alt2 = project_root / "data" / "data" / "Dades_Comptadors_anonymized.parquet"
        
        # Try just the filename in script directory
        alt3 = script_dir / "Dades_Comptadors_anonymized.parquet"
        
        if alt1.exists():
            parquet_path = alt1
        elif alt2.exists():
            parquet_path = alt2
        elif alt3.exists():
            parquet_path = alt3
        else:
            raise FileNotFoundError(
                f"Parquet file not found: {args.parquet}\n"
                f"Tried:\n"
                f"  - {parquet_path.absolute()}\n"
                f"  - {alt1.absolute()}\n"
                f"  - {alt2.absolute()}\n"
                f"  - {alt3.absolute()}"
            )

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

    # Resolve output path relative to script or project root
    out = Path(args.output)
    if not out.is_absolute():
        # Try relative to script location first
        script_dir = Path(__file__).parent
        if (script_dir / out).exists() or (script_dir / out.parent).exists():
            out = script_dir / out
        else:
            # Try relative to project root
            project_root = script_dir.parent
            out = project_root / out
    
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150)
    print(f"Saved figure to {out.absolute()}")


if __name__ == "__main__":
    main()


