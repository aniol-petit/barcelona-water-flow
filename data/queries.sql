#Unique values COUNT for each column (all in one query)
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


#  Unique values for x column with the distribution of the unique values
SELECT
  "NUM_MUN_SGAB",
  COUNT(*) AS count_rows,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_rows
FROM readings
GROUP BY 1
ORDER BY count_rows DESC;


-- Percentage of rows with zero consumption values
SELECT ROUND(COUNT(*)/(SELECT COUNT(*) FROM readings) * 100, 2) FROM readings WHERE "CONSUMO_REAL" = 0;



-- This query identifies POLIZA_SUMINISTRO that have consecutive zero consumption values
WITH ordered_readings AS (
    SELECT 
        "POLIZA_SUMINISTRO",
        FECHA,
        CONSUMO_REAL,
        -- Mark rows where CONSUMO_REAL is 0
        CASE WHEN CONSUMO_REAL = 0 THEN 1 ELSE 0 END AS is_zero,
        -- Create groups for consecutive zeros using running sum
        SUM(CASE WHEN CONSUMO_REAL = 0 THEN 0 ELSE 1 END) 
            OVER (PARTITION BY "POLIZA_SUMINISTRO" ORDER BY FECHA) AS zero_group
    FROM readings
),
consecutive_zeros AS (
    SELECT 
        "POLIZA_SUMINISTRO",
        zero_group,
        COUNT(*) AS consecutive_zero_count,
        MIN(FECHA) AS first_zero_date,
        MAX(FECHA) AS last_zero_date
    FROM ordered_readings
    WHERE is_zero = 1
    GROUP BY "POLIZA_SUMINISTRO", zero_group
    HAVING COUNT(*) >= 2
)
SELECT 
    "POLIZA_SUMINISTRO",
    consecutive_zero_count,
    first_zero_date,
    last_zero_date
FROM consecutive_zeros
ORDER BY consecutive_zero_count DESC, "POLIZA_SUMINISTRO", first_zero_date;