"""
Investigate the two peaks in the average CONSUMO_REAL graph.

Checks:
1. Number of counters contributing on peak days vs normal days
2. Distribution of individual counter values (mean vs median)
3. Top outlier counters on peak days
4. Whether the peaks are due to fewer counters or extreme values
"""

import argparse
from pathlib import Path

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def parse_args():
    p = argparse.ArgumentParser(description="Investigate peaks in average CONSUMO_REAL")
    p.add_argument(
        "--parquet",
        type=str,
        default="data/Dades_Comptadors_anonymized.parquet",
        help="Path to parquet file",
    )
    return p.parse_args()


def main():
    args = parse_args()
    
    parquet_path = Path(args.parquet)
    if not parquet_path.exists():
        alt = Path(__file__).with_name(parquet_path.name)
        if alt.exists():
            parquet_path = alt
        else:
            raise FileNotFoundError(f"Parquet file not found: {args.parquet}")
    
    con = duckdb.connect()
    
    # Get daily stats for all users
    sql = f"""
        SELECT 
            FECHA::DATE AS day,
            COUNT(*) AS num_readings,
            COUNT(DISTINCT "POLIZA_SUMINISTRO") AS num_counters,
            AVG(CONSUMO_REAL) AS mean_consumo,
            MEDIAN(CONSUMO_REAL) AS median_consumo,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY CONSUMO_REAL) AS p95_consumo,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY CONSUMO_REAL) AS p99_consumo,
            MAX(CONSUMO_REAL) AS max_consumo
        FROM '{parquet_path.as_posix()}'
        WHERE CONSUMO_REAL IS NOT NULL
        GROUP BY FECHA::DATE
        ORDER BY day
    """
    
    daily_stats = con.execute(sql).df()
    daily_stats["day"] = pd.to_datetime(daily_stats["day"]).dt.tz_localize(None)
    
    # Identify peak days (top 20 days by mean)
    peak_days = daily_stats.nlargest(20, "mean_consumo")
    
    print("=" * 80)
    print("TOP 20 PEAK DAYS (by mean CONSUMO_REAL):")
    print("=" * 80)
    print(peak_days[["day", "mean_consumo", "median_consumo", "num_counters", "p95_consumo", "p99_consumo", "max_consumo"]].to_string())
    
    # Compare peak days to normal days
    normal_days = daily_stats.nsmallest(100, "mean_consumo")
    
    print("\n" + "=" * 80)
    print("COMPARISON: Peak Days vs Normal Days")
    print("=" * 80)
    print(f"\nPeak Days (top 20):")
    print(f"  Mean consumo: {peak_days['mean_consumo'].mean():.2f}")
    print(f"  Median consumo: {peak_days['median_consumo'].mean():.2f}")
    print(f"  Avg num counters: {peak_days['num_counters'].mean():.0f}")
    print(f"  P95: {peak_days['p95_consumo'].mean():.2f}")
    print(f"  P99: {peak_days['p99_consumo'].mean():.2f}")
    print(f"  Max: {peak_days['max_consumo'].mean():.2f}")
    
    print(f"\nNormal Days (bottom 100):")
    print(f"  Mean consumo: {normal_days['mean_consumo'].mean():.2f}")
    print(f"  Median consumo: {normal_days['median_consumo'].mean():.2f}")
    print(f"  Avg num counters: {normal_days['num_counters'].mean():.0f}")
    print(f"  P95: {normal_days['p95_consumo'].mean():.2f}")
    print(f"  P99: {normal_days['p99_consumo'].mean():.2f}")
    print(f"  Max: {normal_days['max_consumo'].mean():.2f}")
    
    # Check if mean >> median (indicates outliers)
    peak_ratio = peak_days['mean_consumo'].mean() / peak_days['median_consumo'].mean()
    normal_ratio = normal_days['mean_consumo'].mean() / normal_days['median_consumo'].mean()
    
    print(f"\nMean/Median ratio:")
    print(f"  Peak days: {peak_ratio:.2f} (higher = more skewed by outliers)")
    print(f"  Normal days: {normal_ratio:.2f}")
    
    if peak_ratio > 1.5:
        print("\n⚠️  WARNING: Peak days show high mean/median ratio - likely caused by outliers!")
    
    # Get top outlier counters on peak days
    peak_day_list = peak_days['day'].dt.strftime('%Y-%m-%d').tolist()
    peak_days_str = "', '".join(peak_day_list)
    
    sql_outliers = f"""
        SELECT 
            FECHA::DATE AS day,
            "POLIZA_SUMINISTRO" AS counter_id,
            CONSUMO_REAL,
            "US_AIGUA_GEST" AS user_type
        FROM '{parquet_path.as_posix()}'
        WHERE FECHA::DATE IN ('{peak_days_str}')
          AND CONSUMO_REAL IS NOT NULL
        ORDER BY CONSUMO_REAL DESC
        LIMIT 50
    """
    
    top_outliers = con.execute(sql_outliers).df()
    top_outliers["day"] = pd.to_datetime(top_outliers["day"]).dt.tz_localize(None)
    
    print("\n" + "=" * 80)
    print("TOP 50 OUTLIER READINGS ON PEAK DAYS:")
    print("=" * 80)
    print(top_outliers[["day", "counter_id", "CONSUMO_REAL", "user_type"]].to_string())
    
    # Check if same counters appear multiple times
    counter_counts = top_outliers['counter_id'].value_counts()
    print("\n" + "=" * 80)
    print("COUNTERS APPEARING MULTIPLE TIMES IN TOP OUTLIERS:")
    print("=" * 80)
    repeat_counters = counter_counts[counter_counts > 1]
    if len(repeat_counters) > 0:
        print(repeat_counters)
        print("\n⚠️  These counters may have systematic issues!")
    else:
        print("No counters appear multiple times - peaks are likely from different counters each time.")
    
    # Plot: Mean vs Median over time
    plt.figure(figsize=(14, 6))
    plt.plot(daily_stats['day'], daily_stats['mean_consumo'], label='Mean', alpha=0.7, color='blue')
    plt.plot(daily_stats['day'], daily_stats['median_consumo'], label='Median', alpha=0.7, color='green')
    plt.xlabel('Date')
    plt.ylabel('CONSUMO_REAL')
    plt.title('Mean vs Median CONSUMO_REAL over time (large gap = outliers skewing average)')
    plt.legend()
    plt.tight_layout()
    out_path = Path('data/peak_investigation_mean_vs_median.png')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    print(f"\nSaved mean vs median plot to {out_path}")
    
    # Plot: Number of counters over time
    plt.figure(figsize=(14, 6))
    plt.plot(daily_stats['day'], daily_stats['num_counters'], alpha=0.7, color='purple')
    plt.xlabel('Date')
    plt.ylabel('Number of counters')
    plt.title('Number of counters contributing to daily average (drops = fewer data points)')
    plt.tight_layout()
    out_path = Path('data/peak_investigation_num_counters.png')
    plt.savefig(out_path, dpi=150)
    print(f"Saved num counters plot to {out_path}")


if __name__ == "__main__":
    main()


