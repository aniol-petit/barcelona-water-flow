"""
Prepare map data for visualization.

Joins risk scores with geographic information (SECCIO_CENSAL) and generates
GeoJSON files for the frontend application.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


def load_risk_data(risk_csv_path: str | Path) -> pd.DataFrame:
    """Load risk scores from CSV."""
    df = pd.read_csv(risk_csv_path)
    return df


def load_metadata_with_coordinates(db_path: str | Path) -> pd.DataFrame:
    """
    Load metadata including SECCIO_CENSAL, physical features (age, canya), and last month's consumption.
    """
    con = duckdb.connect(str(db_path))
    
    # Query metadata with physical features and last month's consumption
    # Last month is December 2024 (assuming data goes until Dec 2024)
    query = """
    WITH metadata AS (
        SELECT
            "POLIZA_SUMINISTRO"::VARCHAR AS meter_id,
            CAST(DATA_INST_COMP AS DATE) AS installation_date,
            CAST(DIAM_COMP AS DOUBLE) AS diameter,
            SECCIO_CENSAL,
            NUM_MUN_SGAB,
            NUM_DTE_MUNI
        FROM counter_metadata
        WHERE US_AIGUA_GEST = 'D'
    ),
    yearly_consumption AS (
        SELECT
            cd."POLIZA_SUMINISTRO"::VARCHAR AS meter_id,
            EXTRACT(YEAR FROM cd.FECHA) AS year,
            AVG(cd.CONSUMO_REAL) AS avg_consumption
        FROM consumption_data cd
        JOIN counter_metadata cm ON cd."POLIZA_SUMINISTRO" = cm."POLIZA_SUMINISTRO"
        WHERE cm.US_AIGUA_GEST = 'D'
          AND cd.CONSUMO_REAL IS NOT NULL
        GROUP BY meter_id, year
    ),
    median_yearly AS (
        SELECT
            meter_id,
            MEDIAN(avg_consumption) AS median_yearly
        FROM yearly_consumption
        GROUP BY meter_id
    ),
    last_month_consumption AS (
        SELECT
            cd."POLIZA_SUMINISTRO"::VARCHAR AS meter_id,
            AVG(cd.CONSUMO_REAL) AS last_month_avg
        FROM consumption_data cd
        JOIN counter_metadata cm ON cd."POLIZA_SUMINISTRO" = cm."POLIZA_SUMINISTRO"
        WHERE cm.US_AIGUA_GEST = 'D'
          AND EXTRACT(YEAR FROM cd.FECHA) = 2024
          AND EXTRACT(MONTH FROM cd.FECHA) = 12
          AND cd.CONSUMO_REAL IS NOT NULL
        GROUP BY meter_id
    )
    SELECT
        m.meter_id,
        m.SECCIO_CENSAL,
        m.NUM_MUN_SGAB,
        m.NUM_DTE_MUNI,
        m.diameter,
        m.installation_date,
        COALESCE(md.median_yearly, 0) AS median_yearly,
        COALESCE(lm.last_month_avg, 0) AS last_month_consumption
    FROM metadata m
    LEFT JOIN median_yearly md ON m.meter_id = md.meter_id
    LEFT JOIN last_month_consumption lm ON m.meter_id = lm.meter_id
    WHERE m.SECCIO_CENSAL IS NOT NULL
    """
    
    df = con.execute(query).df()
    con.close()
    
    # Calculate age and canya
    df["installation_date"] = pd.to_datetime(df["installation_date"], errors="coerce")
    reference_date = pd.Timestamp(year=2024, month=12, day=31)
    days_since_install = (reference_date - df["installation_date"]).dt.days
    df["age"] = (days_since_install / 365.25).clip(lower=0)
    df["canya"] = df["median_yearly"].fillna(0) * df["age"]
    
    return df


# Barcelona land zones - approximating the city's actual shape, excluding water
BARCELONA_LAND_ZONES = [
    # Central Barcelona (Eixample, Ciutat Vella)
    {"min_lng": 2.150, "max_lng": 2.190, "min_lat": 41.375, "max_lat": 41.405, "weight": 3.0},
    # Upper Barcelona (Gràcia, Sant Gervasi)
    {"min_lng": 2.135, "max_lng": 2.175, "min_lat": 41.395, "max_lat": 41.420, "weight": 2.0},
    # Eastern Barcelona (Sant Martí)
    {"min_lng": 2.180, "max_lng": 2.220, "min_lat": 41.390, "max_lat": 41.420, "weight": 2.0},
    # Western Barcelona (Les Corts, Sants)
    {"min_lng": 2.110, "max_lng": 2.155, "min_lat": 41.370, "max_lat": 41.395, "weight": 2.0},
    # Southern Barcelona (Sants-Montjuïc)
    {"min_lng": 2.140, "max_lng": 2.180, "min_lat": 41.355, "max_lat": 41.380, "weight": 2.0},
    # Northern Barcelona (Horta-Guinardó)
    {"min_lng": 2.150, "max_lng": 2.190, "min_lat": 41.410, "max_lat": 41.440, "weight": 1.5},
    # North-West (Sarrià-Sant Gervasi)
    {"min_lng": 2.105, "max_lng": 2.145, "min_lat": 41.390, "max_lat": 41.425, "weight": 1.5},
    # Far East (Sant Andreu, Nou Barris)
    {"min_lng": 2.165, "max_lng": 2.200, "min_lat": 41.420, "max_lat": 41.455, "weight": 1.0},
    # L'Hospitalet area
    {"min_lng": 2.100, "max_lng": 2.140, "min_lat": 41.350, "max_lat": 41.375, "weight": 1.5},
]


def generate_random_coordinate(meter_index: int) -> tuple[float, float]:
    """
    Generate a nicely distributed random coordinate in Barcelona area.
    
    Uses weighted zones to distribute meters realistically across the city,
    with central areas getting more meters.
    """
    # Use meter index as seed for consistency
    np.random.seed((meter_index * 17 + 42) % (2**31))
    
    # Calculate total weight
    total_weight = sum(zone["weight"] for zone in BARCELONA_LAND_ZONES)
    
    # Select zone based on weights
    rand = np.random.random() * total_weight
    selected_zone = None
    cumulative = 0
    
    for zone in BARCELONA_LAND_ZONES:
        cumulative += zone["weight"]
        if rand <= cumulative:
            selected_zone = zone
            break
    
    if selected_zone is None:
        selected_zone = BARCELONA_LAND_ZONES[0]
    
    # Generate coordinate within selected zone
    lng = np.random.uniform(selected_zone["min_lng"], selected_zone["max_lng"])
    lat = np.random.uniform(selected_zone["min_lat"], selected_zone["max_lat"])
    
    return (float(lng), float(lat))


def prepare_meter_points(
    df_risk: pd.DataFrame,
    df_metadata: pd.DataFrame,
) -> list[dict]:
    """Prepare individual meter points as GeoJSON features."""
    # Merge risk scores with metadata
    df_merged = df_risk.merge(
        df_metadata,
        on="meter_id",
        how="inner"
    )
    
    features = []
    
    # Generate coordinates for each meter (ignore SECCIO_CENSAL for location)
    for meter_index, (_, row) in enumerate(df_merged.iterrows()):
        # Generate random coordinate in Barcelona area
        coords = generate_random_coordinate(meter_index)
        
        # Determine status based on risk
        risk = row["risk_percent"]
        if risk >= 80:
            status = "alert"
        elif risk >= 50:
            status = "warning"
        else:
            status = "normal"
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": coords
            },
            "properties": {
                "id": row["meter_id"],
                "status": status,
                "risk_percent": float(risk),
                "cluster_id": int(row["cluster_id"]),
                "anomaly_score": float(row["anomaly_score"]),
                "cluster_degradation": float(row["cluster_degradation"]),
                "seccio_censal": str(row["SECCIO_CENSAL"]) if pd.notna(row["SECCIO_CENSAL"]) else None,
                "num_mun_sgab": int(row["NUM_MUN_SGAB"]) if pd.notna(row["NUM_MUN_SGAB"]) else None,
                "age": float(row["age"]) if pd.notna(row["age"]) else None,
                "canya": float(row["canya"]) if pd.notna(row["canya"]) else None,
                "last_month_consumption": float(row["last_month_consumption"]) if pd.notna(row["last_month_consumption"]) else None,
            }
        }
        features.append(feature)
    
    return features


def prepare_census_sections(
    df_risk: pd.DataFrame,
    df_metadata: pd.DataFrame,
) -> list[dict]:
    """Prepare aggregated census sections as GeoJSON features."""
    # Merge and aggregate by SECCIO_CENSAL
    df_merged = df_risk.merge(
        df_metadata,
        on="meter_id",
        how="inner"
    )
    
    # Filter out null SECCIO_CENSAL
    df_merged = df_merged[df_merged["SECCIO_CENSAL"].notna()].copy()
    
    # Aggregate by census section
    agg_data = df_merged.groupby("SECCIO_CENSAL").agg({
        "meter_id": "count",
        "risk_percent": ["mean", "min", "max", "std"],
        "NUM_MUN_SGAB": "first",
        "NUM_DTE_MUNI": "first",
    }).reset_index()
    
    # Flatten column names
    agg_data.columns = [
        "SECCIO_CENSAL",
        "meter_count",
        "avg_risk",
        "min_risk",
        "max_risk",
        "std_risk",
        "num_mun_sgab",
        "num_dte_muni",
    ]
    
    features = []
    
    for section_index, (_, row) in enumerate(agg_data.iterrows()):
        # Generate random coordinate for section centroid
        center_lng, center_lat = generate_random_coordinate(section_index + 100000)  # Offset to get different coordinates
        
        # Create a polygon around the centroid
        # Size based on number of meters in section (more meters = larger area)
        base_radius = 0.003  # Base ~300m radius
        meter_count = row["meter_count"]
        # Scale radius based on meter count (log scale to avoid huge areas)
        scale_factor = 1 + np.log1p(meter_count) * 0.5
        radius_degrees = base_radius * scale_factor
        
        # Create a simple square approximation (Mapbox can style it as needed)
        polygon_coords = [
            [center_lng - radius_degrees, center_lat - radius_degrees],
            [center_lng + radius_degrees, center_lat - radius_degrees],
            [center_lng + radius_degrees, center_lat + radius_degrees],
            [center_lng - radius_degrees, center_lat + radius_degrees],
            [center_lng - radius_degrees, center_lat - radius_degrees],
        ]
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_coords]
            },
            "properties": {
                "seccio_censal": str(row["SECCIO_CENSAL"]),
                "meter_count": int(row["meter_count"]),
                "avg_risk": float(row["avg_risk"]),
                "min_risk": float(row["min_risk"]),
                "max_risk": float(row["max_risk"]),
                "std_risk": float(row["std_risk"]) if pd.notna(row["std_risk"]) else 0.0,
                "num_mun_sgab": int(row["num_mun_sgab"]) if pd.notna(row["num_mun_sgab"]) else None,
                "num_dte_muni": int(row["num_dte_muni"]) if pd.notna(row["num_dte_muni"]) else None,
            }
        }
        features.append(feature)
    
    return features


def main():
    """Main execution function."""
    # Paths
    data_dir = Path(__file__).parent
    db_path = data_dir / "analytics.duckdb"
    risk_csv = data_dir / "stage4_outputs" / "meter_failure_risk.csv"
    output_dir = data_dir.parent / "public" / "data"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading risk data...")
    df_risk = load_risk_data(risk_csv)
    print(f"  Loaded {len(df_risk):,} meters with risk scores")
    
    print("\nLoading metadata...")
    df_metadata = load_metadata_with_coordinates(db_path)
    print(f"  Loaded {len(df_metadata):,} meters with metadata")
    
    print("\nPreparing meter points...")
    meter_features = prepare_meter_points(df_risk, df_metadata)
    print(f"  Generated {len(meter_features):,} meter point features")
    
    print("\nPreparing census sections...")
    section_features = prepare_census_sections(df_risk, df_metadata)
    print(f"  Generated {len(section_features):,} census section features")
    
    # Create GeoJSON FeatureCollections
    meters_geojson = {
        "type": "FeatureCollection",
        "features": meter_features
    }
    
    sections_geojson = {
        "type": "FeatureCollection",
        "features": section_features
    }
    
    # Save GeoJSON files
    meters_path = output_dir / "water_meters.geojson"
    sections_path = output_dir / "census_sections.geojson"
    
    print(f"\nSaving GeoJSON files...")
    with open(meters_path, "w", encoding="utf-8") as f:
        json.dump(meters_geojson, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {meters_path}")
    
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(sections_geojson, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {sections_path}")
    
    # Also create a summary JSON
    summary = {
        "total_meters": len(meter_features),
        "total_sections": len(section_features),
        "risk_stats": {
            "min": float(df_risk["risk_percent"].min()),
            "max": float(df_risk["risk_percent"].max()),
            "mean": float(df_risk["risk_percent"].mean()),
            "median": float(df_risk["risk_percent"].median()),
        }
    }
    
    summary_path = output_dir / "risk_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"  ✓ {summary_path}")
    
    print("\n" + "=" * 80)
    print("MAP DATA PREPARATION COMPLETE!")
    print("=" * 80)
    print(f"\nOutput files:")
    print(f"  1. {meters_path.relative_to(data_dir.parent)}")
    print(f"  2. {sections_path.relative_to(data_dir.parent)}")
    print(f"  3. {summary_path.relative_to(data_dir.parent)}")


if __name__ == "__main__":
    main()

