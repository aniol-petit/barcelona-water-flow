"""
Prepare map data for visualization.

Joins risk scores with geographic information (SECCIO_CENSAL) and generates
GeoJSON files for the frontend application using actual geometries from
BarcelonaCiutat_SeccionsCensals.csv.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely import wkt


def load_risk_data(risk_csv_path: str | Path) -> pd.DataFrame:
    """Load risk scores from CSV."""
    df = pd.read_csv(risk_csv_path)
    
    # Ensure subcount_percent column exists (even if all zeros)
    if "subcount_percent" not in df.columns:
        print("  WARNING: subcount_percent column not found in CSV. Adding with default value 0.0")
        print("  This usually means Stage 4 was run with --disable-subcounting")
        df["subcount_percent"] = 0.0
    
    # Ensure risk_percent_base column exists
    if "risk_percent_base" not in df.columns:
        print("  WARNING: risk_percent_base column not found in CSV. Using risk_percent as fallback")
        df["risk_percent_base"] = df.get("risk_percent", 0.0)
    
    return df


def load_census_sections(csv_path: str | Path) -> tuple[dict[str, Polygon | MultiPolygon], dict[str, str]]:
    """
    Load census sections from CSV and parse geometries.
    
    Returns:
        - Dictionary mapping seccio_censal (in our format: 8019XXYYY) to Shapely Polygon or MultiPolygon objects
        - Dictionary mapping seccio_censal to nom_barri (neighborhood name)
    """
    print(f"Loading census sections from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    geometries = {}
    barrio_names = {}
    
    for _, row in df.iterrows():
        codi_districte = str(row["codi_districte"]).zfill(2)  # Ensure 2 digits
        codi_seccio_censal = str(row["codi_seccio_censal"]).zfill(3)  # Ensure 3 digits
        
        # Build our format: 8019XXYYY
        our_format = f"8019{codi_districte}{codi_seccio_censal}"
        
        # Store barrio name
        nom_barri = str(row["nom_barri"]) if pd.notna(row["nom_barri"]) else ""
        barrio_names[our_format] = nom_barri
        
        # Parse the WGS84 geometry (POLYGON string)
        geom_wgs84 = row["geometria_wgs84"]
        if pd.notna(geom_wgs84) and geom_wgs84.strip():
            try:
                # Parse WKT POLYGON string to Shapely Polygon
                polygon = wkt.loads(str(geom_wgs84))
                geometries[our_format] = polygon
            except Exception as e:
                print(f"  Warning: Could not parse geometry for {our_format}: {e}")
                continue
    
    print(f"  Loaded {len(geometries)} census section geometries")
    print(f"  Loaded {len(barrio_names)} barrio name mappings")
    return geometries, barrio_names


def generate_random_point_in_polygon(polygon: Polygon | MultiPolygon, seed: int | None = None) -> tuple[float, float]:
    """
    Generate a random point inside a polygon or multipolygon using rejection sampling.
    
    Returns (lng, lat) coordinates.
    """
    if seed is not None:
        np.random.seed(seed)
    
    # If MultiPolygon, use the largest polygon by area
    if isinstance(polygon, MultiPolygon):
        polygon = max(polygon.geoms, key=lambda p: p.area)
    
    # Get bounding box
    bounds = polygon.bounds  # (minx, miny, maxx, maxy)
    
    max_attempts = 1000
    for _ in range(max_attempts):
        # Generate random point in bounding box
        lng = np.random.uniform(bounds[0], bounds[2])
        lat = np.random.uniform(bounds[1], bounds[3])
        
        point = Point(lng, lat)
        
        # Check if point is inside polygon
        if polygon.contains(point):
            return (float(lng), float(lat))
    
    # If we couldn't find a point after max_attempts, use centroid as fallback
    centroid = polygon.centroid
    return (float(centroid.x), float(centroid.y))


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




def prepare_meter_points(
    df_risk: pd.DataFrame,
    df_metadata: pd.DataFrame,
    geometries: dict[str, Polygon | MultiPolygon],
    barrio_names: dict[str, str],
) -> list[dict]:
    """
    Prepare individual meter points as GeoJSON features.
    
    Only includes meters from Barcelona (seccio_censal starting with 8019).
    Places meters randomly within their corresponding census section polygon.
    """
    # Merge risk scores with metadata
    df_merged = df_risk.merge(
        df_metadata,
        on="meter_id",
        how="inner"
    )
    
    # Filter to only Barcelona meters (seccio_censal starting with 8019)
    df_merged = df_merged[df_merged["SECCIO_CENSAL"].astype(str).str.startswith("8019")].copy()
    print(f"  Filtered to {len(df_merged)} Barcelona meters (seccio_censal starting with 8019)")
    
    features = []
    meters_without_geometry = 0
    
    for meter_index, (_, row) in enumerate(df_merged.iterrows()):
        seccio_censal = str(row["SECCIO_CENSAL"]).strip()
        
        # Get geometry for this census section
        polygon = geometries.get(seccio_censal)
        
        if polygon is None:
            meters_without_geometry += 1
            continue
        
        # Get barrio name
        nom_barri = barrio_names.get(seccio_censal, "")
        
        # Generate random point inside polygon
        # Use meter_id hash as seed for consistency
        seed = hash(row["meter_id"]) % (2**31)
        coords = generate_random_point_in_polygon(polygon, seed=seed)
        
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
                "risk_percent_base": float(row["risk_percent_base"]) if "risk_percent_base" in row and pd.notna(row["risk_percent_base"]) else None,
                "subcount_percent": float(row["subcount_percent"]) if "subcount_percent" in row and pd.notna(row["subcount_percent"]) else (0.0 if "subcount_percent" in row else None),
                "cluster_id": int(row["cluster_id"]),
                "anomaly_score": float(row["anomaly_score"]),
                "cluster_degradation": float(row["cluster_degradation"]),
                "seccio_censal": str(row["SECCIO_CENSAL"]) if pd.notna(row["SECCIO_CENSAL"]) else None,
                "nom_barri": nom_barri,
                "num_mun_sgab": int(row["NUM_MUN_SGAB"]) if pd.notna(row["NUM_MUN_SGAB"]) else None,
                "age": float(row["age"]) if pd.notna(row["age"]) else None,
                "canya": float(row["canya"]) if pd.notna(row["canya"]) else None,
                "last_month_consumption": float(row["last_month_consumption"]) if pd.notna(row["last_month_consumption"]) else None,
            }
        }
        features.append(feature)
    
    if meters_without_geometry > 0:
        print(f"  Warning: {meters_without_geometry} meters were skipped (no geometry found)")
    
    return features


def generate_section_color(seccio_censal: str, index: int) -> str:
    """
    Generate a distinct color for each section using a hash-based approach.
    
    Returns a hex color code.
    """
    # Use a color palette with many distinct colors
    # Palette inspired by ColorBrewer qualitative palettes
    color_palette = [
        '#8dd3c7', '#ffffb3', '#bebada', '#fb8072', '#80b1d3',
        '#fdb462', '#b3de69', '#fccde5', '#d9d9d9', '#bc80bd',
        '#ccebc5', '#ffed6f', '#a6cee3', '#1f78b4', '#b2df8a',
        '#33a02c', '#fb9a99', '#e31a1c', '#fdbf6f', '#ff7f00',
        '#cab2d6', '#6a3d9a', '#ffff99', '#b15928', '#a6cee3',
        '#1f78b4', '#b2df8a', '#33a02c', '#fb9a99', '#e31a1c',
        '#fdbf6f', '#ff7f00', '#cab2d6', '#6a3d9a', '#ffff99',
        '#e6f598', '#abdda4', '#66c2a5', '#3288bd', '#5e4fa2',
        '#fee08b', '#fdae61', '#f46d43', '#d53e4f', '#9e0142',
        '#ffffbf', '#d0efb1', '#b3e5fc', '#81d4fa', '#4fc3f7',
        '#29b6f6', '#03a9f4', '#0288d1', '#0277bd', '#01579b',
        '#fff9c4', '#fce4ec', '#f8bbd0', '#f48fb1', '#f06292',
        '#ec407a', '#e91e63', '#c2185b', '#ad1457', '#880e4f',
    ]
    
    # Use hash of seccio_censal to consistently assign colors
    hash_value = hash(seccio_censal)
    color_index = abs(hash_value) % len(color_palette)
    return color_palette[color_index]


def prepare_census_sections(
    df_risk: pd.DataFrame,
    df_metadata: pd.DataFrame,
    geometries: dict[str, Polygon | MultiPolygon],
    barrio_names: dict[str, str],
) -> list[dict]:
    """
    Prepare ALL census sections as GeoJSON features using actual geometries.
    
    Includes all sections from Barcelona (seccio_censal starting with 8019),
    not just those with meters. Each section gets a distinct color.
    """
    # Create a set of sections that have meters (for statistics)
    df_merged = df_risk.merge(
        df_metadata,
        on="meter_id",
        how="inner"
    )
    
    # Filter to only Barcelona (seccio_censal starting with 8019)
    df_merged = df_merged[
        df_merged["SECCIO_CENSAL"].notna() & 
        df_merged["SECCIO_CENSAL"].astype(str).str.startswith("8019")
    ].copy()
    
    # Aggregate by census section for sections that have meters
    if len(df_merged) > 0:
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
        
        # Create a dictionary for quick lookup of stats
        stats_dict = {}
        for _, row in agg_data.iterrows():
            stats_dict[str(row["SECCIO_CENSAL"]).strip()] = {
                "meter_count": int(row["meter_count"]),
                "avg_risk": float(row["avg_risk"]),
                "min_risk": float(row["min_risk"]),
                "max_risk": float(row["max_risk"]),
                "std_risk": float(row["std_risk"]) if pd.notna(row["std_risk"]) else 0.0,
                "num_mun_sgab": int(row["num_mun_sgab"]) if pd.notna(row["num_mun_sgab"]) else None,
                "num_dte_muni": int(row["num_dte_muni"]) if pd.notna(row["num_dte_muni"]) else None,
            }
    else:
        stats_dict = {}
    
    # Generate features for ALL sections from geometries
    features = []
    sections_without_geometry = 0
    
    # Sort sections for consistent ordering
    sorted_sections = sorted(geometries.keys())
    
    for index, seccio_censal in enumerate(sorted_sections):
        polygon = geometries[seccio_censal]
        
        if polygon is None:
            sections_without_geometry += 1
            continue
        
        # Get barrio name
        nom_barri = barrio_names.get(seccio_censal, "")
        
        # Get stats if available
        stats = stats_dict.get(seccio_censal, {
            "meter_count": 0,
            "avg_risk": 0.0,
            "min_risk": 0.0,
            "max_risk": 0.0,
            "std_risk": 0.0,
            "num_mun_sgab": None,
            "num_dte_muni": None,
        })
        
        # Generate distinct color for this section
        section_color = generate_section_color(seccio_censal, index)
        
        # Convert Shapely polygon/multipolygon to GeoJSON coordinates
        if isinstance(polygon, MultiPolygon):
            # For MultiPolygon, use the largest polygon by area
            largest_poly = max(polygon.geoms, key=lambda p: p.area)
            coords = [[float(x), float(y)] for x, y in largest_poly.exterior.coords]
        else:
            # Regular Polygon
            coords = [[float(x), float(y)] for x, y in polygon.exterior.coords]
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            },
            "properties": {
                "seccio_censal": seccio_censal,
                "nom_barri": nom_barri,
                "section_color": section_color,
                "meter_count": stats["meter_count"],
                "avg_risk": stats["avg_risk"],
                "min_risk": stats["min_risk"],
                "max_risk": stats["max_risk"],
                "std_risk": stats["std_risk"],
                "num_mun_sgab": stats["num_mun_sgab"],
                "num_dte_muni": stats["num_dte_muni"],
            }
        }
        features.append(feature)
    
    if sections_without_geometry > 0:
        print(f"  Warning: {sections_without_geometry} sections were skipped (no geometry found)")
    
    return features


def main():
    """Main execution function."""
    # Paths
    data_dir = Path(__file__).parent
    db_path = data_dir / "analytics.duckdb"
    risk_csv = data_dir / "stage4_outputs" / "meter_failure_risk.csv"
    census_sections_csv = data_dir / "data" / "BarcelonaCiutat_SeccionsCensals.csv"
    output_dir = data_dir.parent / "public" / "data"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading census section geometries...")
    geometries, barrio_names = load_census_sections(census_sections_csv)
    
    print("\nLoading risk data...")
    df_risk = load_risk_data(risk_csv)
    print(f"  Loaded {len(df_risk):,} meters with risk scores")
    
    print("\nLoading metadata...")
    df_metadata = load_metadata_with_coordinates(db_path)
    print(f"  Loaded {len(df_metadata):,} meters with metadata")
    
    print("\nPreparing meter points...")
    meter_features = prepare_meter_points(df_risk, df_metadata, geometries, barrio_names)
    print(f"  Generated {len(meter_features):,} meter point features")
    
    print("\nPreparing census sections...")
    section_features = prepare_census_sections(df_risk, df_metadata, geometries, barrio_names)
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

