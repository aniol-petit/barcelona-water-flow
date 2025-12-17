# Stage 4: Risk Probability Scoring

This module computes failure risk scores (0-100) for each water meter based on:
1. **Intra-cluster anomaly distance**: How atypical a meter's behavior is within its cluster
2. **Cluster-level degradation**: Average degradation level of the cluster based on age and canya
3. **Subcounting probability**: Independent failure signal derived from consumption time series degradation (optional but enabled by default)

## Overview

The risk scoring system combines two main components, and optionally a third:

### Step 1: Intra-cluster Anomaly Score
- Computes Euclidean (or Mahalanobis) distance from each meter to its cluster centroid in latent space
- Normalizes distances to [0, 1] across all meters
- Higher score = more atypical behavior within cluster

### Step 2: Cluster-level Degradation
- For each cluster, computes mean normalized age and canya
- Degradation index: `D_k = α × norm(age) + β × norm(canya)`
- Default weights: α = 0.6, β = 0.4
- Normalized to [0, 1] across clusters

### Step 3: Base Risk Score
- Base risk (before subcounting): `R_i = w1 × s_i + w2 × D_k(i)`
- Default weights: w1 = 0.5, w2 = 0.5
- Normalized to [0, 1] then scaled to percentage (0-100) as `risk_percent_base`

### Step 4: Subcounting Integration (Option A)
- A separate module (`subcounting_detection`) computes a **subcounting score** per meter:
  - Uses monthly aggregated peer-normalized consumption.
  - Combines long-term drop ratio, trend slope, and slope change indicators.
  - Produces `subcount_score ∈ [0, 1]`.
- Interpret:
  - `p_cluster = risk_percent_base / 100`
  - `p_sub = γ × subcount_score` (γ ∈ [0, 1], default 0.8)
  - Final probability (Option A, independent combination):
    - `p_final = 1 - (1 - p_cluster) × (1 - p_sub)`
  - Final risk percent:
    - `risk_percent = 100 × p_final`

## Usage

### Command Line

```bash
cd data
python -m stage4_risk_probabilities.run_stage4
```

### With Custom Parameters

```bash
python -m stage4_risk_probabilities.run_stage4 \
    --latent-path stage2_outputs/latent_representations.csv \
    --cluster-path stage3_outputs/cluster_labels.csv \
    --physical-path stage1_outputs/stage1_physical_features_with_clusters.csv \
    --output-dir stage4_outputs \
    --w1 0.5 \
    --w2 0.5 \
    --alpha 0.6 \
    --beta 0.4 \
    --distance-metric euclidean \
    --top-percent 10.0 \
    --subcount-gamma 0.8 \
    --subcount-db-path data/analytics.duckdb
```

### Python API

```python
from stage4_risk_probabilities.risk_scoring import compute_risk_scores

df_results = compute_risk_scores(
    latent_path="stage2_outputs/latent_representations.csv",
    cluster_labels_path="stage3_outputs/cluster_labels.csv",
    physical_features_path="stage1_outputs/stage1_physical_features_with_clusters.csv",
    output_path="stage4_outputs/meter_failure_risk.csv",
    w1=0.5,
    w2=0.5,
    alpha=0.6,
    beta=0.4,
    distance_metric="euclidean",
    enable_subcounting=True,
    subcount_gamma=0.8,
    use_subcount_cluster_peers=False,
    subcount_db_path="analytics.duckdb",
)
```

## Parameters

- `--latent-path`: Path to latent representations CSV from Stage 2
- `--cluster-path`: Path to cluster labels CSV from Stage 3
- `--physical-path`: Path to physical features CSV (must contain `meter_id`, `age`, `canya`)
- `--output-dir`: Directory to save outputs (default: `stage4_outputs`)
- `--w1`: Weight for anomaly score component (default: 0.5)
- `--w2`: Weight for cluster degradation component (default: 0.5)
- `--alpha`: Weight for age in degradation calculation (default: 0.6)
- `--beta`: Weight for canya in degradation calculation (default: 0.4)
- `--distance-metric`: Distance metric for anomaly calculation (`euclidean` or `mahalanobis`, default: `euclidean`)
- `--disable-subcounting`: Disable subcounting integration (enabled by default)
- `--subcount-gamma`: Maximum additional independent failure probability contributed by subcounting (0–1, default: 0.8)
- `--subcount-use-cluster-peers`: Use cluster-wise peers for subcounting normalisation (instead of global peers)
- `--subcount-db-path`: Path to DuckDB analytics database used by subcounting module (default: `data/analytics.duckdb`)
- `--top-percent`: Percentage of top meters to highlight in visualizations (default: 10.0)
- `--no-viz`: Skip visualization generation

## Output Files

1. **meter_failure_risk.csv**: Full risk scores for all meters
   - Columns:
     - `meter_id`
     - `cluster_id`
     - `anomaly_score`
     - `cluster_degradation`
     - `subcount_score`
     - `risk_percent_base` (cluster-based risk before subcounting)
     - `risk_percent` (final combined risk)
   - Sorted by `risk_percent` (highest first)

2. **risk_summary_by_cluster.csv**: Summary statistics by cluster
   - Columns: `cluster_id`, `n_meters`, `risk_mean`, `risk_std`, `risk_min`, `risk_max`, `risk_median`, `anomaly_mean`, `anomaly_std`, `cluster_degradation`

3. **visualizations/**:
   - `risk_distribution_by_cluster.png`: Box and violin plots of risk distribution
   - `top_{percent}_percent_risk_meters.png`: Highlighted top risk meters
   - `risk_vs_features.png`: Scatter plots of risk vs age, canya, diameter

## Interpretation

- **High risk_percent (80-100)**: Meters with atypical behavior in high-degradation clusters and/or strong subcounting signal
- **Medium risk_percent (40-80)**: Meters with moderate anomaly or in moderate-degradation clusters, possibly with mild subcounting
- **Low risk_percent (0-40)**: Meters with typical behavior in low-degradation clusters and little to no subcounting evidence

The top 10% highest-risk meters (by `risk_percent`) should be prioritized for inspection/maintenance; `subcount_score` helps explain whether the risk is driven
more by behavioral anomalies, physical degradation, or clear subcounting patterns.

