"""
Simple script to create a DuckDB database with VIEWS that read from parquet.
This avoids version compatibility issues because the database file is minimal.
"""

import duckdb
from pathlib import Path

def create_database():
    """Create a minimal DuckDB database with views pointing to parquet file."""
    
    # Paths
    script_dir = Path(__file__).parent
    db_path = script_dir / "analytics.duckdb"
    parquet_path = script_dir / "data" / "Dades_Comptadors_anonymized_v2.parquet"
    
    # Remove old database if exists
    if db_path.exists():
        db_path.unlink()
    wal_file = db_path.with_suffix('.duckdb.wal')
    if wal_file.exists():
        wal_file.unlink()
    
    print("Creating database with views...")
    print(f"Database: {db_path}")
    print(f"Parquet: {parquet_path}")
    
    # Connect and create views
    con = duckdb.connect(str(db_path))
    
    # Get absolute path for parquet (DuckDB needs absolute paths)
    abs_parquet = parquet_path.resolve().as_posix()
    
    # Create counter_metadata view
    print("\nCreating counter_metadata view...")
    con.execute(f"""
        CREATE VIEW counter_metadata AS
        SELECT DISTINCT
            "POLIZA_SUMINISTRO",
            SECCIO_CENSAL,
            US_AIGUA_GEST,
            NUM_MUN_SGAB,
            NUM_DTE_MUNI,
            NUM_COMPLET,
            DATA_INST_COMP,
            MARCA_COMP,
            CODI_MODEL,
            DIAM_COMP
        FROM '{abs_parquet}'
        ORDER BY "POLIZA_SUMINISTRO"
    """)
    
    # Create consumption_data view (long format)
    print("Creating consumption_data view...")
    con.execute(f"""
        CREATE VIEW consumption_data AS
        SELECT 
            "POLIZA_SUMINISTRO",
            CAST(FECHA AS DATE) AS FECHA,
            CONSUMO_REAL
        FROM '{abs_parquet}'
        ORDER BY "POLIZA_SUMINISTRO", FECHA
    """)
    
    # Finalize
    con.execute("CHECKPOINT")
    con.close()
    
    # Verify
    con = duckdb.connect(str(db_path))
    views = con.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_type = 'VIEW'
    """).df()
    
    print("\nViews created:")
    for view in views['table_name']:
        count = con.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
        print(f"  - {view}: {count:,} rows")
    
    con.close()
    print(f"\n[OK] Database created: {db_path}")
    print("\nNote: This database uses VIEWS that read from the parquet file.")
    print("The database file is minimal and should work with any DuckDB version!")

if __name__ == "__main__":
    create_database()

