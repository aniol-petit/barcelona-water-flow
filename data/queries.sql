-- DuckDB SQL snippets for the Barcelona water dataset
-- Usage from Python:
--   import duckdb
--   con = duckdb.connect()
--   con.execute(open('data/queries.sql').read()).df()  -- for a single statement

-- 1) Preview a sample
SELECT * FROM readings LIMIT 10;
-- 2) Date range of FECHA
SELECT MIN(FECHA) AS min_fecha, MAX(FECHA) AS max_fecha
FROM readings;

-- 3) Basic numeric summary (example numeric columns; adjust as needed)
-- Replace CONSUMO_REAL with other numeric fields if available
SELECT
  COUNT(*) AS num_rows,
  AVG(CONSUMO_REAL) AS avg_consumo,
  MIN(CONSUMO_REAL) AS min_consumo,
  MAX(CONSUMO_REAL) AS max_consumo
FROM readings;

-- 4) Daily aggregates
SELECT
  FECHA,
  SUM(CONSUMO_REAL) AS total_consumo,
  AVG(CONSUMO_REAL) AS avg_consumo
FROM readings
GROUP BY FECHA
ORDER BY FECHA
LIMIT 1000;

-- 5) Unique values COUNT for each column (all in one query)
SELECT 'SECCIO_CENSAL' AS column_name, COUNT(DISTINCT "SECCIO_CENSAL") AS unique_count
FROM readings
UNION ALL
SELECT 'POLIZA_SUMINISTRO', COUNT(DISTINCT "POLIZA_SUMINISTRO")
FROM readings
UNION ALL
SELECT 'US_AIGUA_GEST', COUNT(DISTINCT "US_AIGUA_GEST")
FROM readings
UNION ALL
SELECT 'NUM_MUN_SGAB', COUNT(DISTINCT "NUM_MUN_SGAB")
FROM readings
UNION ALL
SELECT 'NUM_DTE_MUNI', COUNT(DISTINCT "NUM_DTE_MUNI")
FROM readings
UNION ALL
SELECT 'NUM_COMPLET', COUNT(DISTINCT "NUM_COMPLET")
FROM readings
UNION ALL
SELECT 'DATA_INST_COMP', COUNT(DISTINCT "DATA_INST_COMP")
FROM readings
UNION ALL
SELECT 'MARCA_COMP', COUNT(DISTINCT "MARCA_COMP")
FROM readings
UNION ALL
SELECT 'CODI_MODEL', COUNT(DISTINCT "CODI_MODEL")
FROM readings
UNION ALL
SELECT 'DIAM_COMP', COUNT(DISTINCT "DIAM_COMP")
FROM readings;

# Unique values for x
SELECT COUNT(DISTINCT ("SECCIO_CENSAL")) AS unique_seccion_censal
FROM readings
where "NUM_MUN_SGAB" == '10';


SELECT
  "NUM_MUN_SGAB",
  COUNT(*) AS count_rows,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_rows
FROM readings
GROUP BY 1
ORDER BY count_rows DESC;

SELECT COUNT(*) FROM readings WHERE "US_AIGUA_GEST" IS not null;

