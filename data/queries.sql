SHOW TABLES;

-- ============================================================================
-- QUERY 1: Unique values COUNT for each column (all in one query)
-- ============================================================================
-- Note: All metadata columns are now in counter_metadata table
SELECT 'SECCIO_CENSAL' AS column_name, COUNT(DISTINCT "SECCIO_CENSAL") AS unique_count
FROM counter_metadata
UNION ALL
SELECT 'POLIZA_SUMINISTRO', COUNT(DISTINCT "POLIZA_SUMINISTRO")
FROM counter_metadata
UNION ALL
SELECT 'US_AIGUA_GEST', COUNT(DISTINCT "US_AIGUA_GEST")
FROM counter_metadata
UNION ALL
SELECT 'NUM_MUN_SGAB', COUNT(DISTINCT "NUM_MUN_SGAB")
FROM counter_metadata
UNION ALL
SELECT 'NUM_DTE_MUNI', COUNT(DISTINCT "NUM_DTE_MUNI")
FROM counter_metadata
UNION ALL
SELECT 'NUM_COMPLET', COUNT(DISTINCT "NUM_COMPLET")
FROM counter_metadata
UNION ALL
SELECT 'DATA_INST_COMP', COUNT(DISTINCT "DATA_INST_COMP")
FROM counter_metadata
UNION ALL
SELECT 'MARCA_COMP', COUNT(DISTINCT "MARCA_COMP")
FROM counter_metadata
UNION ALL
SELECT 'CODI_MODEL', COUNT(DISTINCT "CODI_MODEL")
FROM counter_metadata
UNION ALL
SELECT 'DIAM_COMP', COUNT(DISTINCT "DIAM_COMP")
FROM counter_metadata;


-- ============================================================================
-- QUERY 2: Unique values for US_AIGUA_GEST with the distribution
-- ============================================================================
-- Note: Since each counter has one US_AIGUA_GEST value, we count counters, not rows
SELECT
  "US_AIGUA_GEST",
  COUNT(*) AS count_counters,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_counters
FROM counter_metadata
GROUP BY 1
ORDER BY count_counters DESC;


-- ============================================================================
-- QUERY 3: Percentage of consumption values that are zero
-- ============================================================================
-- Using consumption_data view
SELECT 
    ROUND(
        COUNT(*) * 100.0 / (SELECT COUNT(*) FROM consumption_data),
        2
    ) AS pct_zero_consumption
FROM consumption_data
WHERE CONSUMO_REAL = 0;


-- ============================================================================
-- QUERY 4: POLIZA_SUMINISTRO with consecutive zero consumption values
-- ============================================================================
-- Using consumption_data view
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
    FROM consumption_data
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


-- ============================================================================
-- QUERY 5: Count of rows with zero consumption
-- ============================================================================
-- Using consumption_data view
SELECT COUNT(*) AS total_zero_consumption_rows
FROM consumption_data
WHERE CONSUMO_REAL = 0;


-- ============================================================================
-- QUERY 6: Count distinct SECCIO_CENSAL per POLIZA_SUMINISTRO
-- ============================================================================
-- Since each counter should have one SECCIO_CENSAL, this should mostly be 1
-- But we'll check in case there are any duplicates
SELECT 
    "POLIZA_SUMINISTRO", 
    COUNT(DISTINCT "SECCIO_CENSAL") AS distinct_seccio_censal_count
FROM counter_metadata
GROUP BY "POLIZA_SUMINISTRO"
HAVING COUNT(DISTINCT "SECCIO_CENSAL") > 1
ORDER BY distinct_seccio_censal_count DESC;


-- ============================================================================
-- ADDITIONAL USEFUL QUERIES FOR NEW STRUCTURE
-- ============================================================================

-- Get consumption for a specific counter on specific dates (using consumption_data view)
SELECT 
    "POLIZA_SUMINISTRO",
    FECHA,
    CONSUMO_REAL
FROM consumption_data
WHERE "POLIZA_SUMINISTRO" = 'YOUR_COUNTER_ID_HERE'
  AND FECHA IN ('2024-01-01', '2024-06-15', '2024-12-31')
ORDER BY FECHA;

-- Get consumption time series for a specific counter
SELECT 
    "POLIZA_SUMINISTRO",
    FECHA,
    CONSUMO_REAL
FROM consumption_data
WHERE "POLIZA_SUMINISTRO" = 'YOUR_COUNTER_ID_HERE'
ORDER BY FECHA
LIMIT 100;

-- Join consumption and metadata
SELECT 
    cd."POLIZA_SUMINISTRO",
    cm.US_AIGUA_GEST,
    cm.NUM_MUN_SGAB,
    cm.SECCIO_CENSAL,
    cd.FECHA,
    cd.CONSUMO_REAL
FROM consumption_data cd
JOIN counter_metadata cm ON cd."POLIZA_SUMINISTRO" = cm."POLIZA_SUMINISTRO"
WHERE cm.US_AIGUA_GEST = 'D'  -- Domestic only
LIMIT 10;

-- Count total rows in consumption data (for reference)
SELECT COUNT(*) AS total_rows_in_consumption_data
FROM consumption_data;


-- Count rows where SECCIO_CENSAL has exactly 10 digits (when converted to string)
-- Find SECCIO_CENSAL values containing '08190' (cast to string for LIKE)
SELECT "SECCIO_CENSAL" 
FROM counter_metadata 
WHERE CAST("SECCIO_CENSAL" AS VARCHAR) LIKE '%801901050%';


select distinct("NUM_MUN_SGAB") from counter_metadata;
select COUNT(*) from counter_metadata where "NUM_MUN_SGAB" = 0 ;


SELECT COUNT(DISTINCT("DIAM_COMP"))FROM counter_metadata;

-- ============================================================================
-- PHYSICAL FEATURES QUERY (Stage I reference)
-- Stores output as a table: physical_features_stage1
-- ============================================================================
CREATE OR REPLACE TABLE physical_features_stage1 AS
WITH domestic AS (
    SELECT
        cm."POLIZA_SUMINISTRO"::VARCHAR AS meter_id,
        CAST(cm.DATA_INST_COMP AS DATE) AS installation_date,
        CAST(cm.DIAM_COMP AS DOUBLE) AS diameter,
        CAST(cm.MARCA_COMP AS VARCHAR) AS marca_comp,
        CAST(cm.CODI_MODEL AS VARCHAR) AS codi_model,
        CAST(cd.FECHA AS DATE) AS fecha,
        cd.CONSUMO_REAL
    FROM counter_metadata cm
    JOIN consumption_data cd
        ON cm."POLIZA_SUMINISTRO" = cd."POLIZA_SUMINISTRO"
    WHERE cm.US_AIGUA_GEST = 'D'
),
metadata AS (
    SELECT
        meter_id,
        MIN(installation_date) AS installation_date,
        MIN(diameter) AS diameter,
        MIN(marca_comp) AS marca_comp,
        MIN(codi_model) AS codi_model
    FROM domestic
    GROUP BY meter_id
),
yearly AS (
    SELECT
        meter_id,
        EXTRACT(YEAR FROM fecha) AS year,
        AVG(CONSUMO_REAL) AS avg_consumption
    FROM domestic
    GROUP BY meter_id, year
),
avg_yearly AS (
    SELECT
        meter_id,
        AVG(avg_consumption) AS avg_yearly
    FROM yearly
    GROUP BY meter_id
),
median_yearly AS (
    SELECT
        meter_id,
        MEDIAN(avg_consumption) AS median_yearly
    FROM yearly
    GROUP BY meter_id
)
SELECT
    m.meter_id,
    m.installation_date,
    m.diameter,
    m.marca_comp,
    m.codi_model,
    COALESCE(a.avg_yearly, 0) AS avg_yearly,
    COALESCE(md.median_yearly, 0) AS median_yearly,
    COALESCE(a.avg_yearly, 0) - COALESCE(md.median_yearly, 0) AS mean_minus_median_yearly
FROM metadata m
LEFT JOIN avg_yearly a USING (meter_id)
LEFT JOIN median_yearly md USING (meter_id);

SELECT count(distinct("DIAM_COMP")) FROM counter_metadata;
SELECT COUNT(*) AS total_combinations_between_marca_and_model
FROM (
    SELECT DISTINCT "MARCA_COMP", "CODI_MODEL"
    FROM counter_metadata
);


SELECT DISTINCT "DIAM_COMP", count(*) FROM counter_metadata group by "DIAM_COMP";

SELECT DISTINCT "US_AIGUA_GEST", COUNT(*) FROM counter_metadata group by "US_AIGUA_GEST";

SELECT DISTINCT "MARCA_COMP", "CODI_MODEL", COUNT(*) FROM counter_metadata WHERE "US_AIGUA_GEST" = 'D' group by "MARCA_COMP", "CODI_MODEL" ;

SELECT * FROM counter_metadata WHERE "US_AIGUA_GEST" = 'D';

SELECT seccio_censal
FROM counter_metadata
WHERE "US_AIGUA_GEST" = 'D'
  AND "NUM_MUN_SGAB" = 0
  AND CAST("seccio_censal" AS VARCHAR) LIKE '%801903523%'
GROUP BY seccio_censal;