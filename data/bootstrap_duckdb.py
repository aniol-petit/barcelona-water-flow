import os
import sys
import duckdb


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, 'data')
    db_path = os.path.join(data_dir, 'analytics.duckdb')

    # Candidate Parquet filenames (with and without @ prefix)
    parquet_candidates = [
        os.path.join(data_dir, '@Dades_Comptadors_anonymized.parquet'),
        os.path.join(data_dir, 'Dades_Comptadors_anonymized.parquet'),
    ]
    parquet_path = next((p for p in parquet_candidates if os.path.exists(p)), None)
    if not parquet_path:
        print('Parquet file not found in data/. Expected one of:')
        for p in parquet_candidates:
            print(' -', os.path.basename(p))
        sys.exit(1)

    os.makedirs(data_dir, exist_ok=True)
    con = duckdb.connect(db_path)

    # Create a view pointing to the Parquet file (no copy, always fresh)
    # Parameter binding is not supported in this DDL context; inline with escaping
    escaped_path = parquet_path.replace("'", "''")
    con.execute(
        f"""
        CREATE VIEW IF NOT EXISTS readings AS
        SELECT * FROM parquet_scan('{escaped_path}');
        """
    )

    # Optional: helpful indices or pragmas could go here when materializing.

    # Verify connection and view
    res = con.execute("SELECT COUNT(*) AS n FROM readings").fetchdf()
    print(f"Connected to {db_path}")
    print(f"View 'readings' -> {os.path.basename(parquet_path)}")
    print(res)

    print("You can now run queries against the persistent DB, e.g.:")
    print("  duckdb data/analytics.duckdb")
    print("  -- then run: SELECT * FROM readings LIMIT 10;")


if __name__ == '__main__':
    main()


