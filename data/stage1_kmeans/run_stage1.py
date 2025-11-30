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


def run_stage1_pipeline(k=None):
    physical_features = compute_physical_features()
    cluster_labels_df, _ = perform_stage1_kmeans(k=k, verbose=False)
    
    result = physical_features.merge(cluster_labels_df, on="meter_id")
    output_path = OUTPUT_DIR / "stage1_physical_features_with_clusters.csv"
    result.to_csv(output_path, index=False)
    
    return result


if __name__ == "__main__":
    run_stage1_pipeline()

