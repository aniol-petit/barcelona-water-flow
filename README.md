# FlowGuard - Predictive Water Intelligence System

**🏆 1st Prize Winner Aigües de Barcelona Data Challenge - 6,000€ Award**

A predictive maintenance system for detecting potential undercounting behaviors in smart water meters across Barcelona. This project implements a multi-stage unsupervised learning pipeline that identifies high-risk meters requiring inspection or maintenance.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technologies](#technologies)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Methodology](#methodology)
- [Results](#results)

---

## 🎯 Overview

FlowGuard is an intelligent water meter monitoring system developed for Aigües de Barcelona. The system leverages advanced machine learning techniques to:

- **Identify anomalous meters**: Detect water meters showing unusual consumption patterns
- **Risk scoring**: Assign a failure probability (0-100%) to each meter
- **Interactive visualization**: Map-based interface to explore meter health status
- **Actionable insights**: Generate detailed reports on the top 20 highest-risk meters

The solution combines unsupervised learning, deep learning (autoencoders), and clustering techniques to create a comprehensive risk assessment framework for water infrastructure management.

---

## Features

- **Multi-stage ML Pipeline**: 
  - Physical feature extraction and clustering
  - Autoencoder-based latent representation learning
  - Behavioral clustering analysis
  - Risk probability calculation

- **Interactive Web Dashboard**:
  - Real-time map visualization of meter locations
  - Color-coded risk indicators (Normal, Warning, Alert)
  - Census section aggregation views
  - Detailed meter information on click
  - Top 20 high-risk meters insights panel

- **Comprehensive Risk Assessment**:
  - Anomaly detection within clusters
  - Degradation modeling (age + pipe characteristics)
  - Subcounting probability calculation
  - Combined risk scoring

---

## Technologies

### Backend / Data Processing
- **Python 3.x**
- **PyTorch** - Deep learning framework for autoencoder
- **scikit-learn** - Clustering algorithms (KMeans, DBSCAN)
- **DuckDB** - Analytical database for efficient data processing
- **pandas, numpy** - Data manipulation
- **scipy** - Statistical analysis

### Frontend
- **React** - Web application framework
- **TypeScript** - Type-safe development
- **Mapbox GL JS** - Interactive map visualization
- **GeoJSON** - Geographic data format

### Data Storage
- **Parquet** - Columnar data format for efficient storage
- **DuckDB** - In-memory analytical database

---

## 📁 Project Structure

```
barcelona-water-flow/
├── data/
│   ├── data/                          # Raw dataset location
│   │   └── Dades_Comptadors_anonymized_v2.parquet
│   ├── stage1_kmeans/                 # Physical features & KMeans clustering
│   ├── stage2_autoencoder/            # Autoencoder training
│   ├── stage3_clustering/             # Latent space clustering
│   ├── stage4_risk_probabilities/     # Risk calculation
│   ├── stage1_outputs/                # Stage 1 outputs
│   ├── stage2_outputs/                # Stage 2 outputs
│   ├── stage3_outputs/                # Stage 3 outputs
│   ├── stage4_outputs/                # Stage 4 outputs
│   ├── models/                        # Trained models
│   ├── analytics.duckdb               # DuckDB database
│   ├── create_database.py             # Database initialization
│   ├── prepare_map_data.py            # GeoJSON generation
│   └── requirements.txt               # Python dependencies
├── public/
│   └── data/                          # GeoJSON files for frontend
│       ├── water_meters.geojson
│       ├── census_sections.geojson
│       └── risk_summary.json
└── src/                               # Frontend React application
```

---

## Installation

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd barcelona-water-flow
```

### Step 2: Install Python Dependencies

```bash
cd data
pip install -r requirements.txt
```

This installs:
- pandas, numpy, scipy
- scikit-learn
- torch (PyTorch)
- duckdb
- matplotlib, seaborn
- pyarrow
- joblib
- shapely

### Step 3: Install Frontend Dependencies

```bash
# From project root
npm install
```

### Step 4: Prepare Dataset

Place your dataset file in `data/data/` with one of these names:
- `Dades_Comptadors_anonymized_v2.csv` (CSV format)
- `Dades_Comptadors_anonymized_v2.parquet` (Parquet format - **recommended**)

**Expected dataset structure:**

The dataset should contain the following columns:
- `POLIZA_SUMINISTRO`: Unique meter identifier
- `FECHA`: Record date (YYYY-MM-DD format)
- `CONSUMO_REAL`: Real water consumption (liters/day)
- `SECCIO_CENSAL`: Census section code
- `US_AIGUA_GEST`: Usage type ('D'=domestic, 'C'=commercial, 'I'=industrial, 'A'=other)
- `NUM_MUN_SGAB`: Municipality code
- `NUM_DTE_MUNI`: District code
- `NUM_COMPLET`: Complete meter identifier
- `DATA_INST_COMP`: Meter installation date
- `MARCA_COMP`: Meter brand
- `CODI_MODEL`: Model code
- `DIAM_COMP`: Meter diameter (mm)

**Convert CSV to Parquet (if needed):**

```python
import pandas as pd
from pathlib import Path

# Read CSV
csv_path = Path("data/data/Dades_Comptadors_anonymized_v2.csv")
df = pd.read_csv(csv_path)

# Save as Parquet
parquet_path = Path("data/data/Dades_Comptadors_anonymized_v2.parquet")
df.to_parquet(parquet_path, index=False, engine='pyarrow')

print(f"✓ Dataset converted to: {parquet_path}")
```

### Step 5: Create DuckDB Database

```bash
cd data
python create_database.py
```

This script:
- Reads the Parquet file from `data/data/Dades_Comptadors_anonymized_v2.parquet`
- Creates the `analytics.duckdb` database with two views:
  - `counter_metadata`: Meter metadata (physical characteristics)
  - `consumption_data`: Daily consumption data

**Expected output:**
```
Creating database with views...
Views created:
  - counter_metadata: [number] rows
  - consumption_data: [number] rows
[OK] Database created: data/analytics.duckdb
```

---

## Usage

### Running the Complete Pipeline

Execute the stages in sequential order. Each stage generates outputs that serve as input for the next stage.

#### Stage 0: Exploratory Data Analysis (Optional)

```bash
cd data
jupyter notebook eda_full_dataset.ipynb
```

This notebook analyzes data quality and distribution before modeling.

#### Stage I: Physical Features & KMeans Clustering

```bash
cd data
python -m stage1_kmeans.run_stage1
```

**What it does:**
- Extracts physical features (age, diameter, pipe, brand/model)
- Normalizes features
- Finds optimal k using silhouette score (tests k from 2 to 20)
- Applies KMeans to generate pseudo-labels

**Outputs:**
- `stage1_outputs/stage1_physical_features_with_clusters.csv`
- KMeans model (if configured)

**Estimated time:** 2-5 minutes

#### Stage II: Autoencoder Training

```bash
cd data
python -m stage2_autoencoder.run_stage2
```

**What it does:**
- Builds input vectors with 48 monthly consumption values + physical features + cluster label
- Trains an autoencoder to learn latent representations
- Extracts latent vectors Z for all meters

**Outputs:**
- `stage2_outputs/latent_representations.csv` (matrix [num_meters × latent_dimension])
- `models/stage2_autoencoder.pth` (trained model)

**Estimated time:** 10-30 minutes (depends on GPU availability)

#### Stage III: Latent Space Clustering

```bash
cd data
python -m stage3_clustering.run_stage3
```

**What it does:**
- Applies KMeans (or DBSCAN) on latent vectors from Stage II
- Generates behavioral profile clusters
- Performs statistical analysis to identify risk clusters

**Outputs:**
- `stage3_outputs/cluster_labels.csv`
- `stage3_outputs/cluster_analysis_*.csv` (analysis by age, pipe, diameter, brand/model)
- `stage3_outputs/cluster_analysis_subcounting_risk.csv` (clusters ordered by risk)
- `stage3_outputs/visualizations/*.png` (analysis charts)
- `models/stage3_kmeans_clustering.joblib` (clustering model)

**Estimated time:** 3-8 minutes

#### Stage IV: Risk Probability Calculation

```bash
cd data
python -m stage4_risk_probabilities.run_stage4
```

**What it does:**
- Calculates intra-cluster anomaly score (distance to centroid)
- Calculates cluster-level degradation (age + pipe)
- Combines these components to get base risk
- Calculates subcounting probability from time series
- Combines base risk and subcounting for final risk score

**Outputs:**
- `stage4_outputs/meter_failure_risk.csv` (risk for each meter)
- `stage4_outputs/risk_summary_by_cluster.csv` (statistics per cluster)
- `stage4_outputs/visualizations/*.png` (risk distributions)

**Estimated time:** 5-15 minutes

**Optional parameters:**
```bash
python -m stage4_risk_probabilities.run_stage4 \
    --w1 0.5 \              # Weight for anomaly score
    --w2 0.5 \              # Weight for cluster degradation
    --alpha 0.6 \           # Weight for age in degradation
    --beta 0.4 \            # Weight for pipe in degradation
    --subcount-gamma 0.8 \  # Maximum weight for subcounting
    --disable-subcounting   # Disable subcounting calculation
```

#### Step 5: Prepare Map Data

```bash
cd data
python prepare_map_data.py
```

**What it does:**
- Reads Stage IV results (`stage4_outputs/meter_failure_risk.csv`)
- Merges with geographic metadata from database
- Generates GeoJSON files for frontend:
  - `public/data/water_meters.geojson` (meter points with risk)
  - `public/data/census_sections.geojson` (aggregated census sections)
  - `public/data/risk_summary.json` (statistical summary)

**Expected output:**
```
Loading risk data...
  Loaded [number] meters with risk scores
Loading metadata...
  Loaded [number] meters with metadata
Preparing meter points...
  Generated [number] meter point features
Preparing census sections...
  Generated [number] census section features
Saving GeoJSON files...
  ✓ public/data/water_meters.geojson
  ✓ public/data/census_sections.geojson
  ✓ public/data/risk_summary.json
```

**Estimated time:** 1-3 minutes

#### Step 6: Run Web Application

**Configure Mapbox (if needed):**

The application uses Mapbox GL JS. If you don't have a Mapbox token configured, you'll need to add it to environment variables or modify the `WaterMeterMap.tsx` component code.

**Start Development Server:**

```bash
# From project root
npm run dev
```

The application will be available at `http://localhost:8080` (or the port shown in the terminal).

**Application Features:**

- **Interactive map**: Visualize all meters with color-coded risk levels
- **Filters**: Normal (<50%), Warning (50-80%), Alert (≥80%)
- **Census section view**: Aggregated visualization by geographic areas
- **Dashboard**: Table with all meters, sorted by risk
- **Insights panel**: Details of the top 20 highest-risk meters
- **Map popups**: Click on a meter to see details (final risk, subcounting, cluster, etc.)

### Quick Start Summary

```bash
# 1. Preparation
cd data
# Place dataset at data/data/Dades_Comptadors_anonymized_v2.parquet
# (or convert CSV to Parquet)

# 2. Installation
pip install -r requirements.txt
cd ..
npm install

# 3. Create database
cd data
python create_database.py

# 4. ML Pipeline (in order)
python -m stage1_kmeans.run_stage1
python -m stage2_autoencoder.run_stage2
python -m stage3_clustering.run_stage3
python -m stage4_risk_probabilities.run_stage4

# 5. Prepare map data
python prepare_map_data.py

# 6. Run web application
cd ..
npm run dev
```

---

## Methodology

### Multi-Stage Unsupervised Learning Pipeline

1. **Physical Feature Extraction & Clustering (Stage I)**
   - Extract meter characteristics (age, diameter, pipe type, brand/model)
   - Normalize features and apply KMeans clustering
   - Generate initial meter groupings based on physical attributes

2. **Latent Representation Learning (Stage II)**
   - Construct feature vectors combining:
     - 48 monthly consumption values
     - Physical features
     - Cluster labels from Stage I
   - Train autoencoder to learn compressed representations
   - Extract latent vectors capturing behavioral patterns

3. **Behavioral Clustering (Stage III)**
   - Apply clustering on latent space representations
   - Identify behavioral profiles and consumption patterns
   - Statistical analysis to determine risk clusters

4. **Risk Assessment (Stage IV)**
   - **Anomaly Score**: Distance to cluster centroid
   - **Degradation Score**: Age and pipe characteristics
   - **Subcounting Probability**: Time series analysis
   - **Final Risk**: Weighted combination of all factors

### Risk Scoring Formula

The final risk score combines:
- **Base Risk** = w₁ × Anomaly Score + w₂ × Degradation Score
- **Final Risk** = Base Risk + γ × Subcounting Probability

Where:
- w₁, w₂: Weights for anomaly and degradation (default: 0.5 each)
- α, β: Weights for age and pipe in degradation (default: 0.6, 0.4)
- γ: Maximum weight for subcounting (default: 0.8)

---

## Results

After executing the complete pipeline, you'll have:

```
data/
├── analytics.duckdb                    # Created database
├── stage1_outputs/
│   └── stage1_physical_features_with_clusters.csv
├── stage2_outputs/
│   └── latent_representations.csv
├── stage3_outputs/
│   ├── cluster_labels.csv
│   ├── cluster_analysis_*.csv
│   └── visualizations/*.png
├── stage4_outputs/
│   ├── meter_failure_risk.csv
│   ├── risk_summary_by_cluster.csv
│   └── visualizations/*.png
├── models/
│   ├── stage2_autoencoder.pth
│   └── stage3_kmeans_clustering.joblib

public/data/
├── water_meters.geojson
├── census_sections.geojson
└── risk_summary.json
```

With this structure, the web application can load and visualize all results.

