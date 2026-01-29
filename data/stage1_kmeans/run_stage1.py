from pathlib import Path
import sys

# Handle both direct execution and module import
try:
    from .kmeans_physical import compute_physical_features, perform_stage1_kmeans
except ImportError:
    # When run directly, add parent directory to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stage1_kmeans.kmeans_physical import compute_physical_features, perform_stage1_kmeans

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "stage1_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def run_stage1_pipeline(k=None, verbose=True):
    if verbose:
        print("=" * 60)
        print("STAGE I: KMeans Clustering on Physical Features")
        print("=" * 60)
        print("\nStep 1: Computing physical features...")
    
    physical_features = compute_physical_features()
    
    if verbose:
        print(f"✓ Loaded {len(physical_features):,} domestic meters")
        print(f"  Features: age, diameter, canya, brand_model")
        print("\nStep 2: Performing KMeans clustering...")
    
    cluster_labels_df, kmeans_model = perform_stage1_kmeans(k=k, verbose=verbose)
    
    if verbose:
        print("\nStep 3: Merging results...")
    
    result = physical_features.merge(cluster_labels_df, on="meter_id")
    output_path = OUTPUT_DIR / "stage1_physical_features_with_clusters.csv"
    result.to_csv(output_path, index=False)
    
    if verbose:
        print(f"✓ Results saved to: {output_path}")
        print(f"\nCluster distribution:")
        print(cluster_labels_df["cluster_label"].value_counts().sort_index())
        print("\n" + "=" * 60)
        print("STAGE I COMPLETE!")
        print("=" * 60)
    
    return result


if __name__ == "__main__":
    run_stage1_pipeline()

