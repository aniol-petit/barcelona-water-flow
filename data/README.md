### Data tools

This folder contains lightweight utilities for local data preprocessing.

#### Python setup
- Create a virtual environment (recommended) and install requirements:

```bash
python -m venv .venv
./.venv/Scripts/activate  # Windows PowerShell/CMD
# source .venv/bin/activate  # WSL/Linux/macOS
python -m pip install -r requirements.txt
```

#### Convert Parquet to CSV

```bash
python convert_parquet_to_csv.py --input <path_or_url_to_parquet> --output <output_csv_path>
```

Options:
- `--columns`: comma-separated list of columns to select
- `--limit`: maximum number of rows to export (for sampling)

Examples:

```bash
# Local file
python convert_parquet_to_csv.py --input ./raw/data.parquet --output ./raw/data.csv

# Remote URL (downloads to a temp file first)
python convert_parquet_to_csv.py --input https://example.com/data.parquet --output ./raw/data.csv --columns id,timestamp,value --limit 100000
```

Notes:
- The script streams by Parquet row groups using `pyarrow` to reduce peak memory usage.
- For very large datasets, ensure sufficient disk space for the temporary download and output CSV.

