"""
Utilities to build the physical feature matrix used by Stage I (KMeans)
by querying the DuckDB views (`counter_metadata`, `consumption_data`).

The feature set contains, per domestic meter:
- ``age``: years since installation (2024 – installation year).
- ``diameter``: physical diameter of the meter (``DIAM_COMP``).
- ``canya``: proxy for accumulated consumption
  (median of yearly mean consumptions × age).
- ``brand_model``: joint categorical label for ``MARCA_COMP`` + ``CODI_MODEL``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import duckdb
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler, StandardScaler, OneHotEncoder

CURRENT_YEAR = 2024
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "analytics.duckdb"
NUMERIC_FEATURES = ["age", "diameter", "canya"]


def compute_physical_features(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    current_year: int = CURRENT_YEAR,
) -> pd.DataFrame:
    """
    Compute physical features required by Stage I.

    Parameters
    ----------
    db_path:
        Path to ``analytics.duckdb`` containing the required views.
    current_year:
        Reference year used to compute meter age. Defaults to 2024.

    Returns
    -------
    pandas.DataFrame
        DataFrame indexed by meter id with the columns:
        ``age``, ``diameter``, ``canya``, ``brand_model``.
    """

    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {path}. "
            "Run data/create_database.py to generate analytics.duckdb."
        )

    con = duckdb.connect(database=str(path), read_only=True)

    sql = """
    WITH domestic AS (
        SELECT
            cm."POLIZA_SUMINISTRO"::VARCHAR AS meter_id,
            CAST(cm.DATA_INST_COMP AS DATE) AS installation_date,
            CAST(cm.DIAM_COMP AS DOUBLE) AS diameter,
            CAST(cm.MARCA_COMP AS VARCHAR) AS marca_comp,
            CAST(cm.CODI_MODEL AS VARCHAR) AS codi_model,
            CAST(cd.FECHA AS DATE) AS fecha,
            cd.CONSUMO_REAL
        FROM counter_metadata cm
        JOIN consumption_data cd
            ON cm."POLIZA_SUMINISTRO" = cd."POLIZA_SUMINISTRO"
        WHERE cm.US_AIGUA_GEST = 'D'
    ),
    metadata AS (
        SELECT
            meter_id,
            MIN(installation_date) AS installation_date,
            MIN(diameter) AS diameter,
            MIN(marca_comp) AS marca_comp,
            MIN(codi_model) AS codi_model
        FROM domestic
        GROUP BY meter_id
    ),
    yearly AS (
        SELECT
            meter_id,
            EXTRACT(YEAR FROM fecha) AS year,
            AVG(CONSUMO_REAL) AS avg_consumption
        FROM domestic
        GROUP BY meter_id, year
    ),
    avg_yearly AS (
        SELECT
            meter_id,
            AVG(avg_consumption) AS avg_yearly
        FROM yearly
        GROUP BY meter_id
    ),
    median_yearly AS (
        SELECT
            meter_id,
            MEDIAN(avg_consumption) AS median_yearly
        FROM yearly
        GROUP BY meter_id
    )
    SELECT
        m.meter_id,
        m.installation_date,
        m.diameter,
        m.marca_comp,
        m.codi_model,
        COALESCE(a.avg_yearly, 0) AS avg_yearly,
        COALESCE(md.median_yearly, 0) AS median_yearly
    FROM metadata m
    LEFT JOIN avg_yearly a USING (meter_id)
    LEFT JOIN median_yearly md USING (meter_id)
    """

    df = con.execute(sql).df()
    con.close()

    if df.empty:
        raise ValueError("No domestic meters found with the specified filter.")

    df["installation_date"] = pd.to_datetime(df["installation_date"], errors="coerce")

    reference_date = pd.Timestamp(year=current_year, month=12, day=31)
    days_since_install = (reference_date - df["installation_date"]).dt.days
    df["age"] = (days_since_install / 365.25).clip(lower=0)
    df["diameter"] = df["diameter"].astype(float)

    df["canya"] = df["median_yearly"].fillna(0) * df["age"]

    df["marca_comp"] = df["marca_comp"].astype(str).str.strip()
    df["codi_model"] = df["codi_model"].astype(str).str.strip()
    df["brand_model"] = (
        df["marca_comp"].fillna("UNK") + "::" + df["codi_model"].fillna("UNK")
    )

    final_columns: Iterable[str] = [
        "meter_id",
        "age",
        "diameter",
        "canya",
        "brand_model",
        "avg_yearly",
        "median_yearly",
    ]

    df = df.loc[:, final_columns]

    return df


def build_stage1_feature_matrix(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    current_year: int = CURRENT_YEAR,
) -> Tuple[pd.DataFrame, MinMaxScaler, StandardScaler, OneHotEncoder]:
    """
    Construct the normalized + one-hot encoded feature matrix for Stage I.
    
    Uses min-max scaling for age and diameter, z-score (standardization) for canya.

    Returns
    -------
    tuple
        (features_df, fitted_minmax_scaler, fitted_standard_scaler, fitted_onehot_encoder)
    """

    raw_features = compute_physical_features(db_path=db_path, current_year=current_year)

    # Min-max scaling for age and diameter
    minmax_scaler = MinMaxScaler()
    age_diameter_scaled = minmax_scaler.fit_transform(raw_features[["age", "diameter"]])
    age_diameter_df = pd.DataFrame(
        age_diameter_scaled, 
        columns=["age", "diameter"], 
        index=raw_features.index
    )
    
    # Z-score (standardization) for canya
    standard_scaler = StandardScaler()
    canya_scaled = standard_scaler.fit_transform(raw_features[["canya"]])
    canya_df = pd.DataFrame(
        canya_scaled,
        columns=["canya"],
        index=raw_features.index
    )
    
    # Combine scaled numeric features
    scaled_df = pd.concat([age_diameter_df, canya_df], axis=1)

    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    brand_encoded = encoder.fit_transform(raw_features[["brand_model"]])
    brand_columns = [f"brand_model__{cat}" for cat in encoder.categories_[0]]
    brand_df = pd.DataFrame(brand_encoded, columns=brand_columns, index=raw_features.index)

    features = pd.concat(
        [
            raw_features[["meter_id"]],
            scaled_df,
            brand_df,
        ],
        axis=1,
    )

    return features, minmax_scaler, standard_scaler, encoder


def perform_stage1_kmeans(
    *,
    k: int | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    random_state: int = 42,
    n_init: int = 10,
    max_iter: int = 300,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, KMeans]:
    """
    Perform KMeans clustering on physical features and return cluster labels.
    
    This function performs the final Stage I KMeans clustering on normalized
    physical features. The cluster labels can then be used as an additional
    feature in the autoencoder input.
    
    Parameters
    ----------
    k:
        Number of clusters. If None, will use find_optimal_k() to determine
        the optimal k based on silhouette score.
    db_path:
        Path to DuckDB database.
    random_state:
        Random seed for reproducibility.
    n_init:
        Number of KMeans initializations.
    max_iter:
        Maximum iterations for KMeans.
    verbose:
        If True, print progress information.
    
    Returns
    -------
    tuple
        (cluster_labels_df, fitted_kmeans_model)
        - cluster_labels_df: DataFrame with columns ['meter_id', 'cluster_label']
        - fitted_kmeans_model: The fitted KMeans model
    """
    from .silhouette_optimizer import find_optimal_k
    
    # Build feature matrix
    if verbose:
        print("Building feature matrix...")
    features, _, _, _ = build_stage1_feature_matrix(db_path=db_path)
    
    # Extract feature columns (exclude meter_id)
    feature_cols = [col for col in features.columns if col != "meter_id"]
    X = features[feature_cols].values
    
    # Determine k if not provided
    if k is None:
        if verbose:
            print("Finding optimal k using silhouette score...")
        optimal_k, _, _ = find_optimal_k(
            db_path=db_path,
            random_state=random_state,
            n_init=n_init,
            max_iter=max_iter,
            verbose=verbose,
        )
        k = optimal_k
        if verbose:
            print(f"Using optimal k = {k}")
    
    # Perform KMeans clustering
    if verbose:
        print(f"Performing KMeans clustering with k={k}...")
    kmeans = KMeans(
        n_clusters=k,
        random_state=random_state,
        n_init=n_init,
        max_iter=max_iter,
        n_jobs=-1,
    )
    cluster_labels = kmeans.fit_predict(X)
    
    # Create DataFrame with meter_id and cluster_label
    cluster_labels_df = pd.DataFrame({
        "meter_id": features["meter_id"].values,
        "cluster_label": cluster_labels,
    })
    
    if verbose:
        print(f"Clustering complete. Cluster distribution:")
        print(cluster_labels_df["cluster_label"].value_counts().sort_index())
    
    return cluster_labels_df, kmeans


def _summarize_feature_matrix(features: pd.DataFrame) -> str:
    """Return a short summary string with shape and column info."""
    num_brand_cols = sum(col.startswith("brand_model__") for col in features.columns)
    return (
        f"Feature matrix shape: {features.shape}\n"
        f"Numeric columns: {NUMERIC_FEATURES}\n"
        f"Brand model OHE columns: {num_brand_cols}"
    )


if __name__ == "__main__":
    features, minmax_scaler, standard_scaler, encoder = build_stage1_feature_matrix()
    print(_summarize_feature_matrix(features))
    print("\nPreview:")
    print(features.head())