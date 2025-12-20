# Predictive Water Intelligence - Barcelona Water Flow

Sistema de manteniment predictiu per detectar possibles comportaments de subcomptatge en comptadors d'aigua intel·ligents a Barcelona. Aquest projecte implementa un pipeline d'aprenentatge no supervisat multi-etapa que identifica comptadors d'alt risc que requereixen inspecció o manteniment.

## 🎯 Visió General del Projecte

Aquesta aplicació ajuda Aigües de Barcelona a monitoritzar i mantenir la seva infraestructura de comptadors d'aigua mitjançant:

- **Identificació de comptadors anòmals**: Detecció de comptadors que mostren patrons de consum inusuals
- **Puntuació de risc**: Assignació d'una probabilitat de fallada (0-100%) a cada comptador
- **Visualització interactiva**: Interfície basada en mapa per explorar l'estat de salut dels comptadors
- **Insights accionables**: Generació de informes detallats sobre els 20 comptadors amb major risc

---

# 📋 Guia Completa d'Execució del Projecte

Aquesta guia explica pas a pas com executar tot el codi del projecte des de zero.

## Pas 1: Preparació del Dataset

### 1.1. Col·locar el Dataset Original

Col·loca el fitxer del dataset original a la carpeta `data/data/` amb un d'aquests noms:
- `Dades_Comptadors_anonymized_v2.csv` (format CSV)
- `Dades_Comptadors_anonymized_v2.parquet` (format Parquet - **recomanat**)

**Estructura esperada del dataset:**

El dataset ha de contenir les següents columnes:
- `POLIZA_SUMINISTRO`: Identificador únic del comptador
- `FECHA`: Data del registre (format YYYY-MM-DD)
- `CONSUMO_REAL`: Consum real d'aigua (litres/dia)
- `SECCIO_CENSAL`: Codi de secció censal
- `US_AIGUA_GEST`: Tipus d'ús ('D'=domèstic, 'C'=comercial, 'I'=industrial, 'A'=altres)
- `NUM_MUN_SGAB`: Codi de municipi
- `NUM_DTE_MUNI`: Codi de districte
- `NUM_COMPLET`: Identificador complet del comptador
- `DATA_INST_COMP`: Data d'instal·lació del comptador
- `MARCA_COMP`: Marca del comptador
- `CODI_MODEL`: Codi del model
- `DIAM_COMP`: Diàmetre del comptador (mm)

### 1.2. Convertir CSV a Parquet (si cal)

Si tens el dataset en format CSV, converteix-lo a Parquet per millor rendiment:

```python
import pandas as pd
from pathlib import Path

# Llegeix el CSV
csv_path = Path("data/data/Dades_Comptadors_anonymized_v2.csv")
df = pd.read_csv(csv_path)

# Guarda com a Parquet
parquet_path = Path("data/data/Dades_Comptadors_anonymized_v2.parquet")
df.to_parquet(parquet_path, index=False, engine='pyarrow')

print(f"✓ Dataset convertit a: {parquet_path}")
```

---

## Pas 2: Instal·lació de Dependències

### 2.1. Dependències Python

```bash
cd data
pip install -r requirements.txt
```

Això instal·larà:
- pandas, numpy, scipy
- scikit-learn
- torch (PyTorch)
- duckdb
- matplotlib, seaborn
- pyarrow (per llegir/escrivir Parquet)
- joblib (per guardar models)
- shapely (per dades geogràfiques)

### 2.2. Dependències del Frontend

```bash
# Des de l'arrel del projecte
npm install
```

---

## Pas 3: Creació de la Base de Dades DuckDB

Abans d'executar les etapes, cal crear la base de dades DuckDB que utilitzaran les etapes:

```bash
cd data
python create_database.py
```

Aquest script:
- Llegeix el fitxer Parquet de `data/data/Dades_Comptadors_anonymized_v2.parquet`
- Crea la base de dades `analytics.duckdb` amb dues vistes:
  - `counter_metadata`: Metadades dels comptadors (característiques físiques)
  - `consumption_data`: Dades de consum diari

**Sortida esperada:**
```
Creating database with views...
Views created:
  - counter_metadata: [número] rows
  - consumption_data: [número] rows
[OK] Database created: data/analytics.duckdb
```

---

## Pas 4: Execució de les Etapes del Pipeline

Executa les etapes en ordre seqüencial. Cada etapa genera sortides que són entrada per l'etapa següent.

### Etapa 0: Anàlisi Exploratòria (Opcional)

```bash
cd data
# Obre el notebook Jupyter
jupyter notebook eda_full_dataset.ipynb
```

Aquest notebook analitza la qualitat i distribució de les dades abans de la modelització.

### Etapa I: Característiques Físiques i KMeans

```bash
cd data
python -m stage1_kmeans.run_stage1
```

**Què fa:**
- Extreu característiques físiques (edat, diàmetre, canya, marca/model)
- Normalitza les característiques
- Troba el k òptim mitjançant silueta (prova k de 2 a 20)
- Aplica KMeans per generar pseudo-etiquetes de cluster

**Sortides:**
- `stage1_outputs/stage1_physical_features_with_clusters.csv`
- Model KMeans guardat (si s'ha configurat)

**Temps estimat:** 2-5 minuts

### Etapa II: Entrenament de l'Autoencoder

```bash
cd data
python -m stage2_autoencoder.run_stage2
```

**Què fa:**
- Construeix vectors d'entrada amb 48 valors de consum mensual + característiques físiques + etiqueta de cluster
- Entrena un autoencoder per aprendre representacions latents
- Extreu els vectors latents Z per a tots els comptadors

**Sortides:**
- `stage2_outputs/latent_representations.csv` (matriu [num_comptadors × dimensió_latent])
- `models/stage2_autoencoder.pth` (model entrenat)

**Temps estimat:** 10-30 minuts (depèn de la GPU)

### Etapa III: Clustering de l'Espai Latent

```bash
cd data
python -m stage3_clustering.run_stage3
```

**Què fa:**
- Aplica KMeans (o DBSCAN) sobre els vectors latents de l'Etapa II
- Genera clusters de perfils comportamentals
- Realitza anàlisi estadística per identificar clusters de risc

**Sortides:**
- `stage3_outputs/cluster_labels.csv`
- `stage3_outputs/cluster_analysis_*.csv` (anàlisis per edat, canya, diàmetre, marca/model)
- `stage3_outputs/cluster_analysis_subcounting_risk.csv` (clusters ordenats per risc)
- `stage3_outputs/visualizations/*.png` (gràfics d'anàlisi)
- `models/stage3_kmeans_clustering.joblib` (model de clustering)

**Temps estimat:** 3-8 minuts

### Etapa IV: Càlcul de Probabilitats de Risc

```bash
cd data
python -m stage4_risk_probabilities.run_stage4
```

**Què fa:**
- Calcula la puntuació d'anomalia intra-cluster (distància al centroide)
- Calcula la degradació a nivell de cluster (edat + canya)
- Combina aquests components per obtenir el risc base
- Calcula la probabilitat de subcomptatge a partir de les sèries temporals
- Combina risc base i subcomptatge per obtenir el risc final

**Sortides:**
- `stage4_outputs/meter_failure_risk.csv` (risc per a cada comptador)
- `stage4_outputs/risk_summary_by_cluster.csv` (estadístiques per cluster)
- `stage4_outputs/visualizations/*.png` (distribucions de risc)

**Temps estimat:** 5-15 minuts

**Paràmetres opcionals:**
```bash
python -m stage4_risk_probabilities.run_stage4 \
    --w1 0.5 \              # Pes per puntuació d'anomalia
    --w2 0.5 \              # Pes per degradació de cluster
    --alpha 0.6 \           # Pes per edat en degradació
    --beta 0.4 \            # Pes per canya en degradació
    --subcount-gamma 0.8 \  # Pes màxim per subcomptatge
    --disable-subcounting   # Desactivar càlcul de subcomptatge
```

### Pas 5: Preparació de Dades per al Mapa

```bash
cd data
python prepare_map_data.py
```

**Què fa:**
- Llegeix els resultats de l'Etapa IV (`stage4_outputs/meter_failure_risk.csv`)
- Fusiona amb metadades geogràfiques de la base de dades
- Genera fitxers GeoJSON per al frontend:
  - `public/data/water_meters.geojson` (punts dels comptadors amb risc)
  - `public/data/census_sections.geojson` (seccions censals agregades)
  - `public/data/risk_summary.json` (resum estadístic)

**Sortida esperada:**
```
Loading risk data...
  Loaded [número] meters with risk scores
Loading metadata...
  Loaded [número] meters with metadata
Preparing meter points...
  Generated [número] meter point features
Preparing census sections...
  Generated [número] census section features
Saving GeoJSON files...
  ✓ public/data/water_meters.geojson
  ✓ public/data/census_sections.geojson
  ✓ public/data/risk_summary.json
```

**Temps estimat:** 1-3 minuts

---

## Pas 6: Execució de l'Aplicació Web

### 6.1. Configurar Mapbox (si cal)

L'aplicació utilitza Mapbox GL JS. Si no tens un token de Mapbox configurat, hauràs d'afegir-lo a les variables d'entorn o modificar el codi del component `WaterMeterMap.tsx`.

### 6.2. Iniciar el Servidor de Desenvolupament

```bash
# Des de l'arrel del projecte
npm run dev
```

L'aplicació estarà disponible a `http://localhost:8080` (o el port que mostri el terminal).

### 6.3. Funcionalitats de l'Aplicació

- **Mapa interactiu**: Visualitza tots els comptadors amb codi de colors segons el risc
- **Filtres**: Normal (<50%), Warning (50-80%), Alert (≥80%)
- **Vista de seccions censals**: Visualització agregada per àrees geogràfiques
- **Dashboard**: Taula amb tots els comptadors, ordenats per risc
- **Panell d'insights**: Detalls dels 20 comptadors amb major risc
- **Popups al mapa**: Clic sobre un comptador per veure detalls (risc final, subcomptatge, cluster, etc.)

---

## Resum de l'Ordre d'Execució

```bash
# 1. Preparació
cd data
# Col·loca el dataset a data/data/Dades_Comptadors_anonymized_v2.parquet
# (o converteix CSV a Parquet)

# 2. Instal·lació
pip install -r requirements.txt
cd ..
npm install

# 3. Creació de base de dades
cd data
python create_database.py

# 4. Pipeline ML (en ordre)
python -m stage1_kmeans.run_stage1
python -m stage2_autoencoder.run_stage2
python -m stage3_clustering.run_stage3
python -m stage4_risk_probabilities.run_stage4

# 5. Preparació de dades per al mapa
python prepare_map_data.py

# 6. Executar aplicació web
cd ..
npm run dev
```

---

## Solució de Problemes

### Error: "DuckDB database not found"
- Assegura't d'haver executat `python create_database.py` abans de les etapes.

### Error: "Parquet file not found"
- Verifica que el fitxer estigui a `data/data/Dades_Comptadors_anonymized_v2.parquet`
- Si tens CSV, converteix-lo a Parquet abans.

### Error: "Module not found"
- Assegura't d'haver instal·lat les dependències: `pip install -r requirements.txt`
- Executa les etapes des de la carpeta `data/`.

### Error: "CUDA out of memory" (PyTorch)
- L'autoencoder s'entrena per defecte a CPU. Si tens GPU i vols utilitzar-la, modifica `run_stage2.py` per especificar el device.

### Els resultats no apareixen al mapa
- Assegura't d'haver executat `prepare_map_data.py` després de l'Etapa IV
- Verifica que els fitxers GeoJSON estiguin a `public/data/`
- Refresca el navegador després de regenerar els fitxers

---

## Estructura de Sortides Esperada

Després d'executar tot el pipeline, hauràs de tenir:

```
data/
├── analytics.duckdb                    # Base de dades creada
├── stage1_outputs/
│   └── stage1_physical_features_with_clusters.csv
├── stage2_outputs/
│   └── latent_representations.csv
├── stage3_outputs/
│   ├── cluster_labels.csv
│   ├── cluster_analysis_*.csv
│   └── visualizations/*.png
├── stage4_outputs/
│   ├── meter_failure_risk.csv
│   ├── risk_summary_by_cluster.csv
│   └── visualizations/*.png
├── models/
│   ├── stage2_autoencoder.pth
│   └── stage3_kmeans_clustering.joblib

public/data/
├── water_meters.geojson
├── census_sections.geojson
└── risk_summary.json
```

Amb aquesta estructura, l'aplicació web podrà carregar i visualitzar tots els resultats.

---

