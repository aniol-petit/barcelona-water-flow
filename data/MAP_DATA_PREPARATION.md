# Map Data Preparation

This document explains how to prepare geographic map data for visualizing water meter failure risk on the map interface.

## Overview

The map visualization requires GeoJSON data files that combine:
1. **Risk scores** from Stage 4 (`meter_failure_risk.csv`)
2. **Geographic information** from the database (SECCIO_CENSAL)
3. **Coordinate approximations** (since we don't have exact polygon boundaries)

## Quick Start

Run the data preparation script:

```bash
cd data
python prepare_map_data.py
```

This will generate:
- `public/data/water_meters.geojson` - Individual meter points
- `public/data/census_sections.geojson` - Aggregated census sections
- `public/data/risk_summary.json` - Summary statistics

## Files Generated

### 1. `water_meters.geojson`

GeoJSON FeatureCollection with point features for each water meter:
- **Properties:**
  - `id`: Meter ID (POLIZA_SUMINISTRO)
  - `status`: Risk level (`normal`, `warning`, `alert`)
  - `risk_percent`: Failure risk score (0-100)
  - `cluster_id`: Cluster assignment from Stage 3
  - `anomaly_score`: Intra-cluster anomaly score
  - `cluster_degradation`: Cluster degradation level
  - `seccio_censal`: Census section code
  - `num_mun_sgab`: Municipality code

### 2. `census_sections.geojson`

GeoJSON FeatureCollection with polygon features for each census section:
- **Properties:**
  - `seccio_censal`: Census section code
  - `meter_count`: Number of meters in section
  - `avg_risk`: Average risk score for section
  - `min_risk`: Minimum risk in section
  - `max_risk`: Maximum risk in section
  - `std_risk`: Standard deviation of risk
  - `num_mun_sgab`: Municipality code
  - `num_dte_muni`: District code

### 3. `risk_summary.json`

Summary statistics:
```json
{
  "total_meters": 10425,
  "total_sections": 1234,
  "risk_stats": {
    "min": 0.0,
    "max": 100.0,
    "mean": 10.96,
    "median": 10.95
  }
}
```

## Coordinate Approximation

Since we don't have actual polygon boundaries for census sections, the script uses approximate coordinates:

1. **Base location**: Barcelona center (2.1734°E, 41.3851°N)
2. **Municipality offsets**: Small adjustments based on `NUM_MUN_SGAB`
3. **Section randomization**: Uses SECCIO_CENSAL as seed for consistent positioning

**Note**: For production use, you should:
- Obtain actual polygon/centroid data from Barcelona's open data portal
- Or geocode SECCIO_CENSAL codes using an external service
- Or use a reverse geocoding API

## Frontend Integration

The GeoJSON files are automatically loaded by `WaterMeterMap.tsx` component:

```typescript
// Files are loaded from /data/ directory (public folder)
const metersResponse = await fetch('/data/water_meters.geojson');
const sectionsResponse = await fetch('/data/census_sections.geojson');
```

## View Modes

The map component supports three view modes:
1. **Meters**: Show individual meter points only
2. **Sections**: Show aggregated census sections only
3. **Both**: Overlay sections with meter points

Toggle between modes using the control panel in the top-left of the map.

## Updating Data

After running Stage 4 (risk scoring), regenerate the map data:

```bash
# 1. Run Stage 4 if not already done
python -m stage4_risk_probabilities.run_stage4

# 2. Prepare map data
python prepare_map_data.py

# 3. Refresh the web application
# The new GeoJSON files will be automatically loaded
```

## Troubleshooting

### No data appears on map
- Check that GeoJSON files exist in `public/data/`
- Verify file permissions are correct
- Check browser console for fetch errors

### Coordinates look wrong
- Update `derive_approximate_coordinates()` function with better logic
- Consider using actual polygon/centroid data sources

### Missing census sections
- Some meters might have NULL SECCIO_CENSAL values
- These are filtered out in the aggregation step
- Check database for missing geographic data

