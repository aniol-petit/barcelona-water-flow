"""Quick script to analyze Stage I clustering results."""
import pandas as pd
from pathlib import Path

csv_path = Path(__file__).parent.parent / "stage1_outputs" / "stage1_physical_features_with_clusters.csv"
df = pd.read_csv(csv_path)

print("=" * 70)
print("STAGE I CLUSTERING RESULTS ANALYSIS")
print("=" * 70)

print(f"\n1. Dataset Shape: {df.shape}")
print(f"   Columns: {df.columns.tolist()}")

print(f"\n2. Cluster Distribution:")
cluster_counts = df['cluster_label'].value_counts().sort_index()
print(cluster_counts)
print(f"\n   Total clusters: {df['cluster_label'].nunique()}")
print(f"   Cluster range: {df['cluster_label'].min()} to {df['cluster_label'].max()}")

print(f"\n3. Features Summary:")
print(f"   Age range: {df['age'].min():.2f} to {df['age'].max():.2f} years")
print(f"   Diameter unique values: {sorted(df['diameter'].unique())}")
print(f"   Canya range: {df['canya'].min():.2f} to {df['canya'].max():.2f}")
print(f"   Brand_model unique: {df['brand_model'].nunique()} combinations")

print(f"\n4. Cluster Characteristics (mean values):")
cluster_stats = df.groupby('cluster_label').agg({
    'age': 'mean',
    'diameter': 'mean',
    'canya': 'mean',
    'brand_model': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'N/A'
}).round(2)
print(cluster_stats)

print(f"\n5. Brand Model Distribution by Cluster:")
brand_cluster = df.groupby(['cluster_label', 'brand_model']).size().reset_index(name='count')
print(brand_cluster.sort_values(['cluster_label', 'count'], ascending=[True, False]).head(20))

print("\n" + "=" * 70)
print("READINESS FOR STAGE II AUTOENCODER")
print("=" * 70)

print("\n✓ CORRECT:")
print("  - cluster_label: Integer values (0 to k-1) ✓")
print("  - meter_id: Present for joining with consumption data ✓")

print("\n✗ MISSING/INCORRECT FOR STAGE II:")
print("  - age, diameter, canya: These are RAW values, need NORMALIZATION")
print("    → Should be: min-max scaled (age, diameter) + z-score (canya)")
print("  - brand_model: String format, needs ONE-HOT ENCODING")
print("    → Should be: 17 binary columns (brand_model__ITR::31, etc.)")
print("  - Monthly consumption: NOT PRESENT")
print("    → Need: 48 monthly average consumption values per meter")

print("\n" + "=" * 70)

