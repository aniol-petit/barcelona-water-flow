# Stage 3: Latent Space Clustering and Analysis

This module performs clustering on the latent representations from Stage 2 and provides deep cluster analysis to identify potential subcounting patterns.

## Overview

Stage 3 consists of two main steps:

1. **Clustering**: Apply KMeans or DBSCAN on the latent vectors (Z) from the autoencoder
2. **Analysis**: Deep analysis of clusters to understand their characteristics and identify subcounting patterns

## Usage

### Quick Start

Run Stage 3 with default settings (KMeans with auto-optimized k):

```bash
cd data
python -m stage3_clustering.run_stage3
```

### Command Line Options

```bash
python -m stage3_clustering.run_stage3 \
    --latent-path data/stage2_outputs/latent_representations.csv \
    --method kmeans \
    --n-clusters 8 \
    --k-range 2-20 \
    --output-dir data/stage3_outputs \
    --random-state 42
```

**Clustering Parameters:**
- `--latent-path`: Path to latent_representations.csv from Stage 2 (default: `data/stage2_outputs/latent_representations.csv`)
- `--method`: Clustering method - `kmeans` or `dbscan` (default: `kmeans`)
- `--n-clusters`: Number of clusters for KMeans (if not set, will auto-optimize)
- `--no-auto-optimize`: Disable automatic k optimization
- `--k-range`: Range of k values to test, e.g., `2-20` (default: `2-20`)
- `--dbscan-eps`: Epsilon parameter for DBSCAN (default: 0.5)
- `--dbscan-min-samples`: Min samples parameter for DBSCAN (default: 5)
- `--random-state`: Random seed for reproducibility (default: 42)

**Analysis Parameters:**
- `--db-path`: Path to DuckDB database (default: `data/analytics.duckdb`)
- `--output-dir`: Directory to save results (default: `data/stage3_outputs`)
- `--no-save-model`: Don't save the clustering model

### Programmatic Usage

```python
from pathlib import Path
from stage3_clustering.latent_clustering import cluster_latent_space
from stage3_clustering.cluster_analysis import generate_cluster_report

# Step 1: Perform clustering
cluster_labels_df, model = cluster_latent_space(
    latent_path="data/stage2_outputs/latent_representations.csv",
    method="kmeans",
    n_clusters=8,
    auto_optimize_k=True,
    k_range=range(2, 21),
    save_model=True,
)

# Step 2: Generate analysis report
report = generate_cluster_report(
    cluster_labels=cluster_labels_df,
    db_path="data/analytics.duckdb",
    output_dir="data/stage3_outputs",
)
```

## Output Files

The pipeline generates the following outputs in `stage3_outputs/`:

### Clustering Results
- `cluster_labels.csv`: Meter IDs with their assigned cluster labels

### Analysis Results
- `cluster_analysis_summary.csv`: Overall cluster statistics
- `cluster_analysis_age_analysis.csv`: Age distribution per cluster
- `cluster_analysis_canya_analysis.csv`: Canya distribution per cluster
- `cluster_analysis_diameter_analysis.csv`: Diameter distribution per cluster
- `cluster_analysis_brand_model_analysis.csv`: Brand/model distribution per cluster
- `cluster_analysis_detailed_stats.csv`: Detailed statistics per cluster
- `cluster_analysis_subcounting_risk.csv`: Clusters ranked by subcounting risk
- `statistical_tests.txt`: Results of statistical tests (ANOVA, Chi-square)

### Saved Models
- `models/stage3_kmeans_clustering.joblib` or `models/stage3_dbscan_clustering.joblib`: Saved clustering model

## Cluster Analysis Features

### 1. Statistical Summary
- Cluster sizes and percentages
- Mean, median, std, min, max for age and canya per cluster
- Mode and distribution for diameter and brand/model

### 2. Subcounting Risk Assessment
Clusters are ranked by a risk score based on:
- **High age**: Older meters are more likely to malfunction
- **Low canya**: Unexpectedly low consumption for age
- **Cluster size**: Smaller clusters might indicate anomalies

### 3. Statistical Tests
- **ANOVA**: Tests if age and canya differ significantly across clusters
- **Chi-square**: Tests if diameter and brand/model distributions differ across clusters

### 4. Visualization
Use the visualization utilities to create plots:

```python
from utils.visualization import create_comprehensive_visualization_report
import numpy as np
import pandas as pd

# Load data
latent_df = pd.read_csv("data/stage2_outputs/latent_representations.csv")
cluster_labels = pd.read_csv("data/stage3_outputs/cluster_labels.csv")
physical_features = ...  # Load from database

latent_vectors = latent_df[[f"z_{i}" for i in range(1, 9)]].values
subcounting_risk = pd.read_csv("data/stage3_outputs/cluster_analysis_subcounting_risk.csv")

# Generate all visualizations
create_comprehensive_visualization_report(
    cluster_labels=cluster_labels,
    latent_vectors=latent_vectors,
    physical_features=physical_features,
    subcounting_risk_df=subcounting_risk,
    output_dir="data/stage3_outputs/visualizations",
)
```

## Interpreting Results

### High-Risk Clusters
Look for clusters with:
- **High risk score**: Combination of high age and low canya
- **Significant differences**: Statistical tests show significant differences from other clusters
- **Specific brand/model concentration**: Certain models may be more prone to subcounting

### Example Interpretation
```
Cluster 5:
  - Risk Score: 0.85 (high)
  - Avg Age: 12.5 years (old)
  - Avg Canya: 45.2 (low for age)
  - Top Brand/Model: IBE::66 (60% of cluster)
  → This cluster likely contains meters with subcounting issues
```

## Dependencies

Required packages (see `requirements.txt`):
- pandas
- numpy
- scikit-learn
- scipy
- matplotlib
- seaborn
- duckdb
- joblib






