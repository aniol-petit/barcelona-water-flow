"""
Build feature vectors for Stage II autoencoder input.

Creates the complete feature matrix with:
- 48 monthly average consumption values (4 years × 12 months)
- Normalized physical features (age: min-max, canya: z-score)
- One-hot encoded categorical features (diameter: 7 categories, brand_model: 17 categories)
- Cluster label from Stage I KMeans
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import sys
from pathlib import Path

import duckdb
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler, OneHotEncoder

# Handle both direct execution and module import
try:
    from .kmeans_physical import (
        DEFAULT_DB_PATH,
        CURRENT_YEAR,
        compute_physical_features,
    )
except ImportError:
    # When run directly, add parent directory to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stage1_kmeans.kmeans_physical import (
        DEFAULT_DB_PATH,
        CURRENT_YEAR,
        compute_physical_features,
    )

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "stage1_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "feature_vectors.csv"


def compute_monthly_averages(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    start_year: int = 2021,
    end_year: int = 2024,
) -> pd.DataFrame:
    """
    Compute monthly average consumption for each meter (48 months total).

    Parameters
    ----------
    db_path:
        Path to DuckDB database.
    start_year:
        First year of data (default: 2021).
    end_year:
        Last year of data (default: 2024).

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns: meter_id, month_2021_01, month_2021_02, ..., month_2024_12
        (48 columns total, one per month)
    """
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {path}. "
            "Run data/create_database.py to generate analytics.duckdb."
        )

    con = duckdb.connect(database=str(path), read_only=True)

    # Get all domestic meters first
    meters_sql = """
        SELECT DISTINCT "POLIZA_SUMINISTRO"::VARCHAR AS meter_id
        FROM counter_metadata
        WHERE US_AIGUA_GEST = 'D'
    """
    meters_df = con.execute(meters_sql).df()

    if meters_df.empty:
        raise ValueError("No domestic meters found.")

    # Compute monthly averages for each meter
    monthly_sql = """
    WITH monthly_consumption AS (
        SELECT
            cd."POLIZA_SUMINISTRO"::VARCHAR AS meter_id,
            EXTRACT(YEAR FROM cd.FECHA) AS year,
            EXTRACT(MONTH FROM cd.FECHA) AS month,
            AVG(cd.CONSUMO_REAL) AS avg_consumption
        FROM consumption_data cd
        JOIN counter_metadata cm
            ON cd."POLIZA_SUMINISTRO" = cm."POLIZA_SUMINISTRO"
        WHERE cm.US_AIGUA_GEST = 'D'
          AND EXTRACT(YEAR FROM cd.FECHA) BETWEEN ? AND ?
          AND cd.CONSUMO_REAL IS NOT NULL
        GROUP BY meter_id, year, month
    )
    SELECT
        meter_id,
        year,
        month,
        avg_consumption
    FROM monthly_consumption
    ORDER BY meter_id, year, month
    """

    monthly_df = con.execute(monthly_sql, [start_year, end_year]).df()
    con.close()

    if monthly_df.empty:
        raise ValueError("No monthly consumption data found for the specified years.")

    # Pivot to wide format: one row per meter, one column per month
    monthly_df["month_label"] = (
        monthly_df["year"].astype(str) + "_" + monthly_df["month"].astype(str).str.zfill(2)
    )

    monthly_pivot = monthly_df.pivot_table(
        index="meter_id",
        columns="month_label",
        values="avg_consumption",
        fill_value=0.0,  # Fill missing months with 0
    )

    # Ensure we have all 48 months (create missing ones with 0)
    expected_months = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            expected_months.append(f"{year}_{month:02d}")

    for month in expected_months:
        if month not in monthly_pivot.columns:
            monthly_pivot[month] = 0.0

    # Reorder columns to match expected order
    monthly_pivot = monthly_pivot[[m for m in expected_months if m in monthly_pivot.columns]]

    # Rename columns to month_YYYY_MM format
    monthly_pivot.columns = [f"month_{col}" for col in monthly_pivot.columns]

    return monthly_pivot.reset_index()


def build_stage2_feature_vectors(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    cluster_labels_path: str | Path | None = None,
    current_year: int = CURRENT_YEAR,
    start_year: int = 2021,
    end_year: int = 2024,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, dict]:
    """
    Build complete feature vectors for Stage II autoencoder.

    Parameters
    ----------
    db_path:
        Path to DuckDB database.
    cluster_labels_path:
        Path to CSV with cluster labels. If None, uses default location.
    current_year:
        Reference year for age calculation.
    start_year:
        First year for monthly averages.
    end_year:
        Last year for monthly averages.
    verbose:
        If True, print progress information.

    Returns
    -------
    tuple
        (feature_vectors_df, scalers_dict)
        - feature_vectors_df: DataFrame with all features ready for autoencoder
        - scalers_dict: Dictionary with fitted scalers/encoders for future use
    """
    if cluster_labels_path is None:
        cluster_labels_path = OUTPUT_DIR / "stage1_physical_features_with_clusters.csv"

    cluster_labels_path = Path(cluster_labels_path)
    if not cluster_labels_path.exists():
        raise FileNotFoundError(
            f"Cluster labels file not found at {cluster_labels_path}. "
            "Run stage1_kmeans/run_stage1.py first."
        )

    if verbose:
        print("=" * 70)
        print("BUILDING STAGE II FEATURE VECTORS")
        print("=" * 70)

    # Step 1: Load cluster labels
    if verbose:
        print("\nStep 1: Loading cluster labels...")
    cluster_df = pd.read_csv(cluster_labels_path)
    cluster_df = cluster_df[["meter_id", "cluster_label"]].copy()
    if verbose:
        print(f"  ✓ Loaded {len(cluster_df):,} meters with cluster labels")

    # Step 2: Compute monthly averages
    if verbose:
        print("\nStep 2: Computing monthly average consumption...")
    monthly_df = compute_monthly_averages(
        db_path=db_path, start_year=start_year, end_year=end_year
    )
    if verbose:
        print(f"  ✓ Computed {monthly_df.shape[1] - 1} monthly features for {len(monthly_df):,} meters")

    # Step 3: Load physical features
    if verbose:
        print("\nStep 3: Loading physical features...")
    physical_df = compute_physical_features(db_path=db_path, current_year=current_year)
    if verbose:
        print(f"  ✓ Loaded physical features for {len(physical_df):,} meters")

    # Step 4: Merge all data
    if verbose:
        print("\nStep 4: Merging data...")
    # Start with cluster labels (this is our base)
    merged = cluster_df.copy()

    # Merge monthly averages
    merged = merged.merge(monthly_df, on="meter_id", how="left")
    # Fill missing monthly values with 0
    monthly_cols = [col for col in merged.columns if col.startswith("month_")]
    merged[monthly_cols] = merged[monthly_cols].fillna(0.0)

    # Merge physical features
    merged = merged.merge(
        physical_df[["meter_id", "age", "diameter", "canya", "brand_model"]],
        on="meter_id",
        how="left",
    )

    if verbose:
        print(f"  ✓ Merged data: {len(merged):,} meters")

    # Step 5: Normalize features
    if verbose:
        print("\nStep 5: Normalizing features...")

    # 5a. Age: min-max scaling
    age_scaler = MinMaxScaler()
    merged["age_normalized"] = age_scaler.fit_transform(merged[["age"]]).flatten()

    # 5b. Canya: z-score standardization
    canya_scaler = StandardScaler()
    merged["canya_normalized"] = canya_scaler.fit_transform(merged[["canya"]]).flatten()

    # 5c. Diameter: one-hot encoding
    # Get all possible diameter values
    all_diameters = sorted(merged["diameter"].dropna().unique())
    diameter_encoder = OneHotEncoder(
        categories=[all_diameters],
        sparse_output=False,
        handle_unknown="ignore",
    )
    diameter_encoded = diameter_encoder.fit_transform(merged[["diameter"]])
    diameter_columns = [f"diameter__{int(d)}" for d in diameter_encoder.categories_[0]]
    diameter_df = pd.DataFrame(
        diameter_encoded, columns=diameter_columns, index=merged.index
    )

    # 5d. Brand_model: one-hot encoding
    # Get all possible brand_model combinations from database
    path = Path(db_path)
    con = duckdb.connect(database=str(path), read_only=True)
    all_brand_models_sql = """
        SELECT DISTINCT 
            CONCAT_WS('::', CAST(MARCA_COMP AS VARCHAR), CAST(CODI_MODEL AS VARCHAR)) AS brand_model
        FROM counter_metadata
        WHERE US_AIGUA_GEST = 'D'
        ORDER BY brand_model
    """
    all_brand_models_df = con.execute(all_brand_models_sql).df()
    con.close()

    all_brand_models = sorted(all_brand_models_df["brand_model"].tolist())
    brand_encoder = OneHotEncoder(
        categories=[all_brand_models],
        sparse_output=False,
        handle_unknown="ignore",
    )
    brand_encoded = brand_encoder.fit_transform(merged[["brand_model"]])
    brand_columns = [f"brand_model__{cat}" for cat in brand_encoder.categories_[0]]
    brand_df = pd.DataFrame(brand_encoded, columns=brand_columns, index=merged.index)

    if verbose:
        print(f"  ✓ Age: min-max scaled")
        print(f"  ✓ Canya: z-score standardized")
        print(f"  ✓ Diameter: one-hot encoded ({len(diameter_columns)} categories)")
        print(f"  ✓ Brand_model: one-hot encoded ({len(brand_columns)} categories)")

    # Step 6: Combine all features
    if verbose:
        print("\nStep 6: Combining all features...")

    # Select columns in the correct order
    feature_columns = (
        monthly_cols  # 48 monthly averages
        + ["age_normalized"]  # 1 normalized age
        + diameter_columns  # 7 diameter OHE
        + ["canya_normalized"]  # 1 normalized canya
        + ["cluster_label"]  # 1 cluster label
        + brand_columns  # 17 brand_model OHE
    )

    feature_vectors = pd.concat(
        [
            merged[["meter_id"]],
            merged[monthly_cols],
            merged[["age_normalized"]],
            diameter_df,
            merged[["canya_normalized"]],
            merged[["cluster_label"]],
            brand_df,
        ],
        axis=1,
    )

    # Ensure correct column order
    feature_vectors = feature_vectors[["meter_id"] + feature_columns]

    if verbose:
        print(f"  ✓ Final feature matrix shape: {feature_vectors.shape}")
        print(f"  ✓ Total features: {len(feature_columns)}")
        print(f"    - Monthly averages: {len(monthly_cols)}")
        print(f"    - Age (normalized): 1")
        print(f"    - Diameter (OHE): {len(diameter_columns)}")
        print(f"    - Canya (normalized): 1")
        print(f"    - Cluster label: 1")
        print(f"    - Brand_model (OHE): {len(brand_columns)}")

    # Save scalers for future use
    scalers_dict = {
        "age_scaler": age_scaler,
        "canya_scaler": canya_scaler,
        "diameter_encoder": diameter_encoder,
        "brand_encoder": brand_encoder,
    }

    return feature_vectors, scalers_dict


if __name__ == "__main__":
    feature_vectors, scalers = build_stage2_feature_vectors(verbose=True)

    # Save to CSV
    feature_vectors.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✓ Feature vectors saved to: {OUTPUT_FILE}")
    print(f"  Shape: {feature_vectors.shape}")
    print(f"  Columns: {len(feature_vectors.columns)} (1 meter_id + {len(feature_vectors.columns) - 1} features)")

    print("\n" + "=" * 70)
    print("FEATURE VECTORS READY FOR STAGE II AUTOENCODER")
    print("=" * 70)

