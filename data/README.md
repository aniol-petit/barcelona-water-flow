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
  **00 — Barcelona**, **10 — L’Hospitalet de Llobregat**, **25 — Viladecans**, **47 — Santa Coloma de Gramenet**.  
- El camp **US_AIGUA_GEST** la majoria són D (domèstic, 5.57M). 2.22M comercials (C) i 5.8k municipal  
- El període temporal abasta **de l’1 de gener al 31 de desembre de 2024**.  
- De totes les poliçes que hi ha (11797) només tenim la ubi de 3999.
- No hi ha null values en les columnes poliza, fecha, consum

---