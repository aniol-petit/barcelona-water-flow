# Predictive Water Intelligence - Barcelona Water Flow

A comprehensive predictive maintenance system for detecting potential subcounting behavior in smart water meters across Barcelona. This project implements a multi-stage unsupervised learning pipeline that identifies high-risk meters requiring inspection or maintenance.

## 🎯 Project Overview

This application helps Aigües de Barcelona monitor and maintain their water meter infrastructure by:

- **Identifying anomalous meters**: Detecting meters that exhibit unusual consumption patterns
- **Risk scoring**: Assigning a failure risk probability (0-100%) to each meter
- **Interactive visualization**: Providing an intuitive map-based interface to explore meter health
- **Actionable insights**: Generating detailed reports on the top 20 highest-risk meters

### Key Features

- 🗺️ **Interactive Map**: Visualize all water meters with color-coded risk levels across Barcelona
- 📊 **Risk Dashboard**: Filter and search meters by status (Normal, Warning, Alert)
- 🔍 **Insights Panel**: Detailed explanations for the top 20 highest-risk meters
- 📈 **Multi-Stage ML Pipeline**: Unsupervised learning approach combining KMeans clustering and autoencoders
- 🎯 **Behavioral Profiling**: Identifies meter clusters based on consumption patterns and physical characteristics

## 🏗️ Architecture Overview

The system follows a **two-stage synergic methodology** combining unsupervised machine learning techniques:

1. **Stage I**: KMeans clustering on physical features → generates pseudo-labels
2. **Stage II**: Autoencoder training → learns non-linear consumption patterns
3. **Stage III**: Latent space clustering → refines behavioral profiles
4. **Stage IV**: Risk probability scoring → assigns failure risk to each meter

### Data Flow

```
Raw Data (DuckDB)
    ↓
Stage I: Physical Features → KMeans → Pseudo-labels
    ↓
Stage II: Monthly Consumption + Features → Autoencoder → Latent Representations (Z)
    ↓
Stage III: Latent Space → KMeans/DBSCAN → Refined Clusters
    ↓
Stage IV: Risk Scoring → Risk Percentages (0-100)
    ↓
Visualization: Interactive Map + Dashboard
```

## 📊 Stage-by-Stage Implementation

### Stage I: Label Generation (KMeans on Physical Features)

**Purpose**: Create initial pseudo-clusters based on physical meter characteristics.

**Input Features**:
- `age`: Years since installation (2024 - installation year)
- `diameter`: Physical diameter of the meter (DIAM_COMP)
- `canya`: Accumulated consumption proxy = median yearly average × age
- `brand_model`: Joint categorical feature (MARCA_COMP + CODI_MODEL, one-hot encoded, 27 categories)

**Process**:
1. Query DuckDB to extract physical features for all domestic meters (US_AIGUA_GEST == 'D')
2. Normalize features:
   - `age` and `diameter`: Min-max scaling [0, 1]
   - `canya`: Z-score standardization (mean=0, std=1)
   - `brand_model`: One-hot encoding (27 categories)
3. Find optimal k using silhouette score (tests k from 2-20)
4. Perform KMeans clustering on normalized features
5. Output cluster labels to be used as features in Stage II

**Output**: `stage1_outputs/stage1_physical_features_with_clusters.csv`

**Key Files**:
- `data/stage1_kmeans/kmeans_physical.py`: Feature computation and clustering
- `data/stage1_kmeans/silhouette_optimizer.py`: K optimization
- `data/stage1_kmeans/run_stage1.py`: Pipeline execution

---

### Stage II: Autoencoder Training

**Purpose**: Learn compressed representations of consumption patterns while incorporating physical features.

**Input Features**:
- **48 monthly average consumption values**: One per month for 4 years (2021-2024)
- **Normalized physical features**: age, diameter, canya (from Stage I)
- **Pseudo-label from Stage I**: Cluster ID as integer feature (not one-hot)

**Architecture**:
- **Encoder**: Input → Hidden layers → Latent space (Z) with dimensionality ~8 (tunable)
- **Decoder**: Latent space (Z) → Hidden layers → Reconstruction
- **Loss**: Mean Squared Error (MSE) between input and reconstruction

**Training Process**:
1. Build feature vectors: concatenate 48 monthly averages + normalized physical features + cluster label
2. Split data: 80% training, 20% validation
3. Train autoencoder to minimize reconstruction loss
4. Extract latent representation (Z) for each meter
5. Save model and latent vectors

**Hyperparameters** (tunable):
- `latent_dim`: Latent space dimensionality (default: 8)
- `hidden_dims`: Hidden layer dimensions (default: [64, 32])
- `num_epochs`: Training epochs (default: 100)
- `batch_size`: Batch size (default: 64)
- `learning_rate`: Learning rate (default: 0.001)

**Output**: 
- `stage2_outputs/latent_representations.csv`: Latent vectors (num_meters × latent_dim)
- `models/stage2_autoencoder.pth`: Trained model

**Key Files**:
- `data/stage2_autoencoder/model.py`: Autoencoder architecture (PyTorch)
- `data/stage2_autoencoder/trainer.py`: Training loop
- `data/stage2_autoencoder/run_stage2.py`: Pipeline execution

---

### Stage III: Latent Space Clustering

**Purpose**: Identify refined behavioral profiles by clustering meters in the compressed latent space.

**Input**: Latent representations (Z) from Stage II

**Process**:
1. Load latent vectors (shape: [num_meters, latent_dim])
2. Apply clustering algorithm:
   - **KMeans**: Finds k clusters (optimal k determined via silhouette score)
   - **DBSCAN**: Density-based clustering (optional, for non-spherical clusters)
3. Analyze clusters:
   - Statistical summary (mean, median, std for age, canya, diameter)
   - Brand/model distribution per cluster
   - Subcounting risk assessment per cluster
   - Statistical tests (ANOVA, Chi-square) to validate cluster differences

**Output**: 
- `stage3_outputs/cluster_labels.csv`: Final cluster assignments
- `stage3_outputs/cluster_analysis_*.csv`: Detailed cluster statistics
- `models/stage3_kmeans_clustering.joblib`: Saved clustering model

**Key Files**:
- `data/stage3_clustering/latent_clustering.py`: Clustering algorithms
- `data/stage3_clustering/cluster_analysis.py`: Statistical analysis
- `data/stage3_clustering/run_stage3.py`: Pipeline execution

---

### Stage IV: Risk Probability Scoring

**Purpose**: Assign a failure risk score (0-100) to each meter based on behavioral anomaly and cluster degradation.

**Input**:
- Latent representations (Z) from Stage II
- Cluster labels from Stage III
- Physical features (age, canya) from Stage I

**Risk Calculation**:

#### Step 1: Intra-cluster Anomaly Score (s_i)
- Compute Euclidean (or Mahalanobis) distance from each meter to its cluster centroid in latent space
- Normalize distances to [0, 1] across all meters
- **Higher score = more atypical behavior within cluster**

#### Step 2: Cluster-level Degradation (D_k)
- For each cluster, compute mean normalized age and canya
- Degradation index: `D_k = α × norm(age) + β × norm(canya)`
- Default weights: α = 0.6, β = 0.4
- Normalized to [0, 1] across clusters
- **Higher degradation = older meters with higher accumulated consumption**

#### Step 3: Combined Risk Score (R_i)
- Final risk: `R_i = w1 × s_i + w2 × D_k(i)`
- Default weights: w1 = 0.5, w2 = 0.5
- Normalized to [0, 1] then scaled to percentage (0-100)

**Risk Interpretation**:
- **0-50% (Normal)**: Typical behavior in low-degradation clusters
- **50-80% (Warning)**: Some atypical behavior or moderate degradation
- **80-100% (Alert)**: Highly atypical behavior in high-degradation clusters → **Requires immediate inspection**

**Output**: 
- `stage4_outputs/meter_failure_risk.csv`: Risk scores for all meters
- `stage4_outputs/risk_summary_by_cluster.csv`: Cluster-level risk statistics
- `stage4_outputs/visualizations/`: Risk distribution plots

**Key Files**:
- `data/stage4_risk_probabilities/risk_scoring.py`: Risk calculation logic
- `data/stage4_risk_probabilities/visualization.py`: Risk plots
- `data/stage4_risk_probabilities/run_stage4.py`: Pipeline execution

---

## 🗺️ Visualization & User Interface

### Interactive Map Component

The frontend application (`src/`) provides an interactive visualization built with:
- **React + TypeScript**: Component-based UI
- **Mapbox GL JS**: Interactive map rendering
- **Tailwind CSS + shadcn-ui**: Modern, responsive design

**Features**:
1. **Meter View**: Color-coded dots representing individual meters
   - 🔵 Blue: Normal risk (< 50%)
   - 🟡 Yellow: Warning risk (50-80%)
   - 🔴 Red: Alert risk (≥ 80%)
2. **Section View**: Aggregated risk by census section (SECCIO_CENSAL)
3. **Filter Controls**: Toggle visibility of Normal/Warning/Alert meters
4. **Interactive Popups**: Click meters to view details (risk %, cluster ID, etc.)

### Dashboard Component

Comprehensive meter management interface:
- **Search Functionality**: Filter meters by ID, location, or name
- **Status Tabs**: View meters by status (Normal, Warning, Alert)
- **Meter Cards**: Display key metrics:
  - Last month consumption
  - Average yearly consumption
  - Meter age
  - Canya (accumulated consumption proxy)
  - Risk percentage

### Insights Sheet

Detailed analysis for top 20 highest-risk meters:
- **Risk Breakdown**: Individual anomaly scores and cluster degradation
- **Physical Characteristics**: Age, canya, consumption data
- **Actionable Recommendations**: What is happening, what could be done, what usually happens
- **Voice Explanation**: Text-to-speech support for accessibility

**Data Preparation**:
- `data/prepare_map_data.py`: Joins risk scores with geographic metadata and generates GeoJSON files
- Outputs: `public/data/water_meters.geojson`, `public/data/census_sections.geojson`

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** with required packages (see `data/requirements.txt`)
- **Node.js & npm** for the frontend application
- **DuckDB database**: `data/analytics.duckdb` (created from raw data)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd barcelona-water-flow
```

2. **Install Python dependencies**:
```bash
cd data
pip install -r requirements.txt
```

3. **Install frontend dependencies**:
```bash
npm install
```

### Running the Pipeline

**Important**: Run stages in sequential order (I → II → III → IV).

#### Stage I: Physical Features & KMeans
```bash
cd data
python -m stage1_kmeans.run_stage1
```

#### Stage II: Autoencoder Training
```bash
python -m stage2_autoencoder.run_stage2
```

#### Stage III: Latent Space Clustering
```bash
python -m stage3_clustering.run_stage3
```

#### Stage IV: Risk Scoring
```bash
python -m stage4_risk_probabilities.run_stage4
```

#### Prepare Map Data
```bash
python prepare_map_data.py
```

### Running the Frontend Application

```bash
npm run dev
```

The application will be available at `http://localhost:5173` (or the port shown in terminal).

---

## 📁 Project Structure

```
barcelona-water-flow/
├── data/                          # Data processing and ML pipeline
│   ├── analytics.duckdb          # DuckDB database with raw data
│   ├── stage1_kmeans/            # Stage I: Physical features & KMeans
│   ├── stage2_autoencoder/       # Stage II: Autoencoder training
│   ├── stage3_clustering/        # Stage III: Latent space clustering
│   ├── stage4_risk_probabilities/ # Stage IV: Risk scoring
│   ├── stage*_outputs/           # Output CSVs and visualizations
│   ├── models/                   # Saved ML models
│   ├── prepare_map_data.py       # Map data preparation
│   └── requirements.txt          # Python dependencies
├── src/                          # Frontend React application
│   ├── components/               # React components
│   │   ├── WaterMeterMap.tsx    # Main map component
│   │   ├── Dashboard.tsx        # Meter dashboard
│   │   ├── InsightsSheet.tsx    # Risk insights panel
│   │   └── ...
│   ├── pages/
│   │   └── Index.tsx            # Main application page
│   └── ...
├── public/
│   └── data/                     # GeoJSON files for map
│       ├── water_meters.geojson
│       └── census_sections.geojson
└── README.md                     # This file
```

---

## 📊 Data Requirements

The system expects a DuckDB database (`data/analytics.duckdb`) with the following views:

### `counter_metadata` View
Contains static meter information:
- `POLIZA_SUMINISTRO`: Meter ID
- `US_AIGUA_GEST`: Usage type (must be 'D' for domestic)
- `SECCIO_CENSAL`: Census section code
- `DATA_INST_COMP`: Installation date
- `DIAM_COMP`: Meter diameter
- `MARCA_COMP`: Brand
- `CODI_MODEL`: Model code

### `consumption_data` View
Contains daily consumption readings:
- `POLIZA_SUMINISTRO`: Meter ID
- `FECHA`: Date
- `CONSUMO_REAL`: Consumption value (liters)

See `data/README.md` for detailed database setup instructions.

---

## 🔧 Configuration & Customization

### Adjusting Risk Thresholds

Edit `data/prepare_map_data.py`:
```python
if risk >= 80:
    status = "alert"
elif risk >= 50:
    status = "warning"
else:
    status = "normal"
```

### Tuning Risk Score Weights

Edit `data/stage4_risk_probabilities/run_stage4.py`:
```bash
python -m stage4_risk_probabilities.run_stage4 \
    --w1 0.6 \      # Weight for anomaly score
    --w2 0.4 \      # Weight for cluster degradation
    --alpha 0.7 \   # Weight for age in degradation
    --beta 0.3      # Weight for canya in degradation
```

### Autoencoder Architecture

Edit `data/stage2_autoencoder/run_stage2.py`:
```python
python -m stage2_autoencoder.run_stage2 \
    --latent-dim 12 \          # Latent space size
    --hidden-dims 128 64 32 \  # Hidden layers
    --num-epochs 150 \         # Training epochs
    --learning-rate 0.0005     # Learning rate
```

---

## 📈 Performance Metrics

### Model Performance
- **Stage I**: Silhouette score used to determine optimal k
- **Stage II**: Reconstruction loss (MSE) on validation set
- **Stage III**: Silhouette score for latent space clusters
- **Stage IV**: Risk distribution statistics by cluster

### Current Results
- **Total Meters Analyzed**: ~10,427 domestic meters
- **High-Risk Meters (≥80%)**: ~10 meters requiring immediate attention
- **Warning Meters (50-80%)**: ~53 meters for monitoring

---

## 🤝 Contributing

This project was developed for Aigües de Barcelona as a predictive maintenance tool. For questions or contributions, please contact the development team.

---

## 📝 License

[Add license information here]

---

## 🙏 Acknowledgments

- **Aigües de Barcelona**: For providing the water meter dataset
- **Unsupervised Learning Methodology**: Based on synergic KMeans + Autoencoder approach

---

## 🔗 Related Documentation

- `data/README.md`: Detailed data processing documentation
- `data/stage3_clustering/README.md`: Stage III clustering details
- `data/stage4_risk_probabilities/README.md`: Stage IV risk scoring details
- `data/MAP_DATA_PREPARATION.md`: Map data preparation guide
