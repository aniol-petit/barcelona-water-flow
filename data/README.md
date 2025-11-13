### 1️⃣ Consum diari
Conté els registres de consum d’aigua de cada pòlissa per dia.

| Columna | Descripció |
|----------|-------------|
| **POLIZA_SUMINISTRO** | Identificador únic del contracte o subministrament d’aigua. |
| **FECHA** | Data del registre del consum (format YYYY-MM-DD). |
| **CONSUMO_REAL** | Quantitat d’aigua realment consumida aquell dia (L/dia).

---

### 2️⃣ Informació tècnica del comptador
Inclou dades fixes associades a cada pòlissa i al seu comptador instal·lat.

| Columna | Descripció |
|----------|-------------|
| **POLIZA_SUMINISTRO** | Identificador del subministrament, comú amb el fitxer de consum per unir amb la resta d’informació. |
| **SECCIO_CENSAL** | Codi de la secció censal on es troba el comptador (àrea geogràfica petita). |
| **US_AIGUA_GEST** | Tipus d’ús de l’aigua (domèstic, comercial, industrial, etc.). |
| **NUM_MUN_SGAB** | Codi del municipi segons Aigües de Barcelona: 00 Barcelona, 10 L’Hospitalet, 25 Viladecans, 47 Santa Coloma. |
| **NUM_DTE_MUNI** | Número del districte o zona administrativa dins del municipi. |
| **NUM_COMPLET** | Identificador únic complet del comptador intel·ligent. |
| **DATA_INST_COMP** | Data d’instal·lació del comptador. |
| **MARCA_COMP** | Marca o fabricant del comptador. |
| **CODI_MODEL** | Codi o model específic del comptador segons el fabricant. |
| **DIAM_COMP** | Diàmetre del comptador o de la canonada (en mil·límetres). |

---

## 🧭 Notes generals

- Les dades inclouen quatre municipis principals:  
  **00 — Barcelona**, **10 — L'Hospitalet de Llobregat**, **25 — Viladecans**, **47 — Santa Coloma de Gramenet**.  
- El camp **US_AIGUA_GEST** la majoria són D (domèstic, 5.57M). 2.22M comercials (C) i 5.8k municipal  
- El període temporal abasta **de l'1 de gener al 31 de desembre de 2024**.  
- De totes les poliçes que hi ha (11797) només tenim la ubi de 3999.
- No hi ha null values en les columnes poliza, fecha, consum

---

## Database Connection

### Step 1: Create the Database

The database file (`analytics.duckdb`) is not in the repository (it's in `.gitignore`), so you need to create it first:

```bash
cd data
python create_database.py
```

This will create `analytics.duckdb` with two views:
- `counter_metadata`: One row per counter with all metadata features
- `consumption_data`: Consumption data in long format (counter, date, consumption)

### Step 2: Connect with Your Database Tool

1. **Open your database management tool** (On the top left corner click the icon ^ and then database)

2. **Create a new connection:**
   - Click the "+" (plus) icon or "New Connection"
   - Select **"DuckDB"** as the server type (in others)

3. **Configure the connection:**
   - **Database Path**: Navigate to `data/analytics.duckdb` in your project directory
     - Full path example: `C:\path\to\barcelona-water-flow\data\analytics.duckdb`
     - Or use relative path: `data/analytics.duckdb` (relative to project root)
   - Make sure **Server Type** is set to **DuckDB** (not PostgreSQL, MySQL, etc.)

4. **Connect** and verify you can see:
   - `counter_metadata` view
   - `consumption_data` view

### Notes

- The database uses **VIEWS** that read directly from the parquet file, so the database file is minimal
- If you get a "serialization error", make sure you're connecting to DuckDB (not another database type)
- You can run queries from `queries.sql` once connected
- Create a 'file queries_prova.sql' to make queries that are not relevant (the file is in the gitignore)

---