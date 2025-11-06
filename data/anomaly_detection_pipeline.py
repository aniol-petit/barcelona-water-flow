"""
Unsupervised Anomaly Detection Pipeline for Domestic Water Meters
Using Isolation Forest on consumption behavior features.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime

print("=" * 80)
print("WATER CONSUMPTION ANOMALY DETECTION PIPELINE")
print("=" * 80)

# ============================================================================
# STEP 0 & 1: Load and filter domestic meters
# ============================================================================
print("\nStep 0-1: Loading and filtering data...")
print("-" * 80)

df = pd.read_parquet('Dades_Comptadors_anonymized.parquet')
print(f"Total rows loaded: {len(df):,}")

# Filter only domestic meters
df_domestic = df[df['US_AIGUA_GEST'] == 'D'].copy()
print(f"Domestic meters rows: {len(df_domestic):,}")
print(f"Unique domestic meters: {df_domestic['POLIZA_SUMINISTRO'].nunique():,}")

# Keep only relevant columns
df_domestic = df_domestic[['POLIZA_SUMINISTRO', 'FECHA', 'CONSUMO_REAL']].copy()

# Rename for consistency with naming convention
df_domestic.columns = ['POLIZA_SUBM', 'FECHA', 'CONSUMO_REAL']

# Convert FECHA to datetime
df_domestic['FECHA'] = pd.to_datetime(df_domestic['FECHA'])

print(f"Date range: {df_domestic['FECHA'].min()} to {df_domestic['FECHA'].max()}")

# ============================================================================
# STEP 0: Create pivoted matrix (meters × dates)
# ============================================================================
print("\nStep 0: Creating pivoted matrix (counters x dates)...")
print("-" * 80)

# Create pivot table
pivot_df = df_domestic.pivot_table(
    index='POLIZA_SUBM',
    columns='FECHA',
    values='CONSUMO_REAL',
    aggfunc='sum'  # In case of duplicates
)

print(f"Pivot matrix shape: {pivot_df.shape} (meters x dates)")
print(f"Memory usage: {pivot_df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

# Save pivoted matrix
output_pivot_path = 'domestic_consumption_matrix.csv'
print(f"Saving pivoted matrix to: {output_pivot_path}")
pivot_df.to_csv(output_pivot_path)
print(">>> Pivoted matrix saved!")

# ============================================================================
# STEP 2: Compute z_ij and r_ij per meter-day
# ============================================================================
print("\nStep 2: Computing z_ij and r_ij features...")
print("-" * 80)

# Compute per-meter statistics
meter_stats = df_domestic.groupby('POLIZA_SUBM')['CONSUMO_REAL'].agg([
    ('mean', 'mean'),
    ('std', 'std')
]).reset_index()

print(f"Computed statistics for {len(meter_stats):,} meters")

# Merge stats back to the main dataframe
df_features = df_domestic.merge(meter_stats, on='POLIZA_SUBM', how='left')

# Compute z_ij: Z-score (standardized consumption)
# Handle cases where std = 0 (constant consumption)
df_features['z_ij'] = np.where(
    df_features['std'] > 0,
    (df_features['CONSUMO_REAL'] - df_features['mean']) / df_features['std'],
    0  # If no variation, z-score is 0
)

# Compute r_ij: Ratio to mean (normalized consumption)
# Handle cases where mean = 0
df_features['r_ij'] = np.where(
    df_features['mean'] > 0,
    df_features['CONSUMO_REAL'] / df_features['mean'],
    0  # If mean is 0, ratio is 0
)

# Keep only required columns
df_daily_features = df_features[['POLIZA_SUBM', 'FECHA', 'CONSUMO_REAL', 'z_ij', 'r_ij']].copy()

# Save daily features
output_daily_path = 'domestic_daily_features.csv'
print(f"Saving daily features to: {output_daily_path}")
df_daily_features.to_csv(output_daily_path, index=False)
print(">>> Daily features saved!")

# Display sample statistics
print("\nDaily features statistics:")
print(df_daily_features[['CONSUMO_REAL', 'z_ij', 'r_ij']].describe())

# ============================================================================
# STEP 3: Aggregate features per meter
# ============================================================================
print("\nStep 3: Aggregating features per meter...")
print("-" * 80)

# Aggregate z_ij and r_ij per meter
aggregated_features = df_daily_features.groupby('POLIZA_SUBM').agg({
    'z_ij': ['mean', 'std', 'max', 'min'],
    'r_ij': ['mean', 'std', 'max', 'min'],
    'CONSUMO_REAL': ['mean', 'std', 'count']  # Additional context
}).reset_index()

# Flatten column names
aggregated_features.columns = ['_'.join(col).strip('_') if col[1] else col[0] 
                                for col in aggregated_features.columns.values]

# Rename for clarity
aggregated_features.rename(columns={
    'CONSUMO_REAL_mean': 'consumo_mean',
    'CONSUMO_REAL_std': 'consumo_std',
    'CONSUMO_REAL_count': 'num_days'
}, inplace=True)

print(f"Aggregated features for {len(aggregated_features):,} meters")
print("\nAggregated features columns:")
print(aggregated_features.columns.tolist())

# Handle any NaN or infinite values that might cause issues
aggregated_features = aggregated_features.replace([np.inf, -np.inf], np.nan)
aggregated_features = aggregated_features.fillna(0)

print("\nAggregated features statistics:")
print(aggregated_features.describe())

# ============================================================================
# STEP 4: Train Isolation Forest
# ============================================================================
print("\nStep 4: Training Isolation Forest model...")
print("-" * 80)

# Select features for the model
feature_cols = [
    'z_ij_mean', 'z_ij_std', 'z_ij_max', 'z_ij_min',
    'r_ij_mean', 'r_ij_std', 'r_ij_max', 'r_ij_min',
    'consumo_mean', 'consumo_std'
]

X = aggregated_features[feature_cols].values

print(f"Training on {X.shape[0]:,} meters with {X.shape[1]} features")
print(f"Features: {feature_cols}")

# Train Isolation Forest
# contamination: expected proportion of outliers (default 0.1 = 10%)
# random_state: for reproducibility
iso_forest = IsolationForest(
    contamination=0.1,
    random_state=42,
    n_estimators=100,
    max_samples='auto',
    n_jobs=-1,  # Use all available cores
    verbose=1
)

print("\nTraining model...")
iso_forest.fit(X)

# ============================================================================
# STEP 5: Generate anomaly scores
# ============================================================================
print("\nStep 5: Generating anomaly scores...")
print("-" * 80)

# Predict anomaly labels (-1 for outliers, 1 for inliers)
anomaly_labels = iso_forest.predict(X)

# Get anomaly scores (lower = more anomalous)
anomaly_scores = iso_forest.decision_function(X)

# Add results to dataframe
aggregated_features['anomaly_label'] = anomaly_labels
aggregated_features['anomaly_score'] = anomaly_scores

# Create a more intuitive anomaly score (higher = more anomalous)
# Normalize to 0-100 scale
min_score = anomaly_scores.min()
max_score = anomaly_scores.max()
aggregated_features['anomaly_score_normalized'] = (
    100 * (1 - (anomaly_scores - min_score) / (max_score - min_score))
)

# Sort by anomaly score (most anomalous first)
aggregated_features = aggregated_features.sort_values('anomaly_score', ascending=True)

print(f"\nAnomalies detected: {(anomaly_labels == -1).sum():,} meters ({100*(anomaly_labels == -1).mean():.2f}%)")
print(f"Normal meters: {(anomaly_labels == 1).sum():,} meters ({100*(anomaly_labels == 1).mean():.2f}%)")

# ============================================================================
# STEP 6: Export results
# ============================================================================
print("\nStep 6: Exporting results...")
print("-" * 80)

# Save full results with anomaly scores
output_scores_path = 'domestic_meter_anomaly_scores.csv'
print(f"Saving anomaly scores to: {output_scores_path}")
aggregated_features.to_csv(output_scores_path, index=False)
print(">>> Anomaly scores saved!")

# Save top anomalies (most suspicious meters)
top_n = 100
top_anomalies = aggregated_features[aggregated_features['anomaly_label'] == -1].head(top_n)
output_top_path = 'top_100_anomalous_meters.csv'
print(f"\nSaving top {top_n} anomalous meters to: {output_top_path}")
top_anomalies.to_csv(output_top_path, index=False)
print(">>> Top anomalies saved!")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("PIPELINE SUMMARY")
print("=" * 80)
print(f"Total domestic meter-days processed: {len(df_domestic):,}")
print(f"Unique meters analyzed: {len(aggregated_features):,}")
print(f"Date range: {df_domestic['FECHA'].min().date()} to {df_domestic['FECHA'].max().date()}")
print(f"\nAnomalies detected: {(anomaly_labels == -1).sum():,} meters")
print(f"Anomaly rate: {100*(anomaly_labels == -1).mean():.2f}%")

print("\nOutput files generated:")
print(f"  1. {output_pivot_path} - Pivoted consumption matrix")
print(f"  2. {output_daily_path} - Daily features (z_ij, r_ij)")
print(f"  3. {output_scores_path} - Anomaly scores per meter")
print(f"  4. {output_top_path} - Top {top_n} anomalous meters")

print("\nTop 10 most anomalous meters:")
print(aggregated_features[['POLIZA_SUBM', 'anomaly_score_normalized', 'anomaly_label', 
                           'consumo_mean', 'z_ij_max', 'r_ij_max']].head(10).to_string(index=False))

print("\n" + "=" * 80)
print("PIPELINE COMPLETED SUCCESSFULLY!")
print("=" * 80)

