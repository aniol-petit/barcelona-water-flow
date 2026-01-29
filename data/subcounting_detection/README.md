## Subcounting Detection Module

This module computes a **per-meter subcounting score** that quantifies how strongly
the consumption time series suggests **under-registration over time** (subcounting).
The score is designed to be **modular** and **interpretable**, and to plug directly
into Stage 4 risk probability computation.

---

### 1. Design Goals

- **Robustness to noise**: Daily consumption is noisy. We work on **aggregated
  monthly (or weekly)** consumption and smooth implicitly through aggregation.
- **Control for global effects**: We normalise each meter's consumption by a
  **peer/cluster median per period**, so global changes (seasonality, city-wide
  events) do not look like subcounting for a single meter.
- **Multiple redundant indicators**: We do not rely on a single metric. Instead
  we compute three complementary indicators and combine them:
  - Long-term **drop ratio** (recent vs baseline consumption).
  - **Trend slope** on the peer-normalised series.
  - **Change in slope** between the first and second half of the series.
- **Interpretability**: All intermediate quantities (ratios, slopes, scores)
  are exposed in a DataFrame for debugging and expert review.

---

### 2. Data Source and Aggregation

We reuse the DuckDB database created in `data/create_database.py`, specifically:

- `consumption_data` view: (POLIZA_SUMINISTRO, FECHA, CONSUMO_REAL)
- `counter_metadata` view: used only to filter **domestic** meters (`US_AIGUA_GEST = 'D'`).

The high-level loading step is:

```python
df_daily = load_consumption_data(db_path="data/analytics.duckdb")
```

This produces:

- `meter_id`: string (POLIZA_SUMINISTRO)
- `date`: daily timestamp
- `consumo_real`: daily consumption

#### 2.1 Monthly aggregation

To reduce noise and make trends easier to detect, we aggregate to **monthly
consumption per meter**:

- Define `period = date.to_period(freq).to_timestamp()`, where `freq="M"` by
  default (can be changed to `"W"` for weekly).
- For each `(meter_id, period)` we sum daily consumption:

```text
meter_id, period, consumo = SUM(consumo_real over that month)
```

The helper `_aggregate_monthly_consumption` implements this.

We then require a **minimum number of periods** (`min_months`, default 12) to
compute stable metrics. Meters with fewer periods are still included but will
tend to get neutral/low subcounting scores.

---

### 3. Peer Normalisation

Raw consumption levels are not directly comparable across meters. Subcounting
is a **relative** concept: *does this meter start to consume less than what
would be expected for its peers?*

We therefore compute, per period, a **peer median** and a **normalised series**
for each meter:

```text
peer_median(period) = median(consumo over all relevant meters at that period)

x_norm(meter, period) = consumo(meter, period) / (peer_median(period) + eps)
```

Two modes are supported:

- **Global peers** (default): median across all domestic meters per period.
- **Cluster peers**: if `cluster_labels` (meter_id, cluster_label) are passed
  and `config.use_cluster_peers=True`, the peer median is computed **within each
  cluster** (from Stage 3 latent clustering).

The function `_compute_peer_normalisation` handles this and returns a DataFrame:

- `meter_id`
- `period`
- `consumo` (aggregated value)
- `peer_median`
- `x_norm` (peer-normalised consumption)

This step removes seasonality and city-wide shifts, focusing on **relative
behaviour within similar meters**.

---

### 4. Subcounting Indicators

We compute three indicators per meter using the **peer-normalised** series
`x_norm` (one point per month).

#### 4.1 Long-term Drop Ratio (R)

Let the last `recent_window` periods (default 6) be the **recent window**, and
the preceding `baseline_window` periods (default 12) be the **baseline**.

For each meter:

- `recent = last recent_window values of x_norm`
- `baseline = previous baseline_window values`
- Drop ratio:

```text
R = mean(recent) / mean(baseline)
```

If there is not enough data, or baseline mean is 0, we set `R = 1.0` (no drop).

**Interpretation**:

- `R ≈ 1`: stable behaviour vs peers.
- `R < 1`: recent consumption is lower than baseline, relative to peers.
- `R << 1`: strong relative drop (strong subcounting signal).

We map R to a sub-score `s_R ∈ [0, 1]`:

- `R ≤ 0.5   → s_R = 1.0` (very strong drop)
- `0.5 < R < 0.8 → s_R` decreases linearly from 1 to 0
- `R ≥ 0.8  → s_R = 0.0` (no meaningful drop)

This mapping is implemented in `_score_from_ratio`.

#### 4.2 Trend Slope (slope)

We fit a simple **linear regression in time** on the normalised series:

- Let `t = 0, 1, ..., n-1` (one per period)
- Fit: `x_norm(t) = β0 + β1 t + ε`
- We estimate the slope `β1` analytically (least squares) in `_compute_trend_slope`.

To make this slope scale-invariant, we normalise it by the **median level** of
`x_norm`:

```text
median_level = median(x_norm)
rel_slope = slope / median_level
```

We then map `rel_slope` to a sub-score `s_T ∈ [0, 1]` with heuristic thresholds:

- `rel_slope ≥ 0     → s_T = 0.0` (no negative trend)
- `rel_slope ≤ -0.05 → s_T = 1.0` (strong negative trend: ≥ 5% drop per period)
- Between `0` and `-0.05`: `s_T` interpolates linearly from 0 to 1.

These numbers can be tuned; they are chosen to detect **consistent downward
trends** while ignoring small fluctuations.

#### 4.3 Slope Change (delta_s)

Subcounting may start only after a certain point in time (e.g. meter starts
degrading mid-year). To capture this, we compare **slopes in the first and
second half** of the series:

- Split `x_norm` into two halves: `first` and `second`.
- Compute `s_first = slope(first)`, `s_second = slope(second)`.
- If `s_first` is ~0, we treat the ratio as neutral (`delta_s = 1`).
- Otherwise:

```text
delta_s = s_second / s_first
```

Interpretation:

- `delta_s < 1`: second half grows more slowly (or decreases more) than first.
- `delta_s << 1`: strong slowdown (suspect subcounting).

We map `delta_s` to `s_delta ∈ [0, 1]`:

- `delta_s ≤ 0.5 → s_delta = 1.0` (strong slowdown)
- `0.5 < delta_s < 0.8 → s_delta` decreases linearly from 1 to 0
- `delta_s ≥ 0.8 → s_delta = 0.0` (no relevant slowdown)

This is implemented in `_score_from_slope_change`.

---

### 5. Combining Indicators into a Subcounting Score

For each meter we have:

- `s_R`: sub-score from long-term drop ratio.
- `s_T`: sub-score from trend slope.
- `s_delta`: sub-score from slope change.

We combine them with configurable weights `(w_ratio, w_trend, w_slope_change)`:

```text
subcount_score_raw = w_ratio * s_R + w_trend * s_T + w_slope_change * s_delta
```

Default weights (in `SubcountingConfig`) are:

- `w_ratio = 0.4`
- `w_trend = 0.3`
- `w_slope_change = 0.3`

Additionally, we apply a simple **logical reinforcement**:

- Count how many of `(s_R, s_T, s_delta)` are **strong** (`> 0.7`).
- If at least **two** indicators are strong, we enforce a minimum:

```text
subcount_score_raw = max(subcount_score_raw, 0.7)
```

Finally, to improve comparability across meters, we **normalise the raw score**
to [0, 1] across all meters:

```text
subcount_score = (subcount_score_raw - min) / (max - min)
```

The function `compute_subcounting_metrics` returns a DataFrame with:

- `meter_id`
- `n_periods`
- `R`
- `slope`
- `delta_s`
- `s_R`, `s_T`, `s_delta`
- `subcount_score_raw`
- `subcount_score` (normalised to [0, 1])

For convenience, `compute_subcounting_scores` orchestrates the full pipeline:

```python
from subcounting_detection import compute_subcounting_scores

df_sub = compute_subcounting_scores(
    db_path="data/analytics.duckdb",
    cluster_labels=df_clusters,         # optional
    config=SubcountingConfig(
        freq="M",
        min_months=12,
        baseline_window=12,
        recent_window=6,
        use_cluster_peers=False,
    ),
)
```

---

### 6. Integration with Final Failure Probabilities (Option A)

Stage 4 currently computes a **cluster-based failure risk** per meter:

- `risk_percent ∈ [0, 100]`

We interpret:

- `p_cluster = risk_percent / 100` as the **base probability** of failure.
- `subcount_score ∈ [0, 1]` as an **independent subcounting failure signal**.

Using **Option A (post-hoc combination)**, we define the final probability:

```text
p_sub = gamma * subcount_score
p_final = 1 - (1 - p_cluster) * (1 - p_sub)
```

Where:

- `gamma ∈ [0, 1]` (default 0.8) caps the **maximum additional risk** subcounting
  can introduce (even if `subcount_score = 1`).
- `p_final` is always ≥ `p_cluster`.

We then map `p_final` back to a percentage:

```text
risk_percent_final = 100 * p_final
```

This has several nice properties:

- If base risk is low but subcounting is strong, `p_final` becomes dominated
  by the subcounting component (`p_sub`).
- If both are high, they combine multiplicatively (less than naive sum, more
  than either alone).
- If subcounting is negligible (`subcount_score ≈ 0`), `p_final ≈ p_cluster`.

In the risk scoring code, the integration therefore consists of:

1. Computing `df_sub` with `compute_subcounting_scores`.
2. Merging `df_sub[["meter_id", "subcount_score"]]` into Stage 4 results
   (`df_results`).
3. Applying the combination formula with a configurable `gamma`.

The final `meter_failure_risk.csv` then includes **both**:

- `risk_percent_base`: base cluster-based risk.
- `subcount_score`: subcounting intensity.
- `risk_percent`: final combined probability (0–100).

---

### 7. Configuration and Extensibility

The `SubcountingConfig` dataclass centralises tunable parameters:

- `freq`: aggregation frequency (`"M"` or `"W"`).
- `min_months`: minimum number of periods required to consider long-term
  comparisons reliable.
- `baseline_window`, `recent_window`: define how much history is used for
  the ratio `R`.
- `use_cluster_peers`: whether to use cluster-wise or global peer medians.
- `w_ratio`, `w_trend`, `w_slope_change`: indicator weights.
- `gamma`: maximum additional risk contributed by subcounting when combined
  with base risk.

You can experiment with different configurations (e.g. weekly aggregation,
different windows) without changing the core logic.

---

### 8. Limitations and Future Improvements

- **Low-usage meters**: For meters with very low absolute consumption, ratios
  and slopes can be noisy. A future improvement would be to apply explicit
  filters (e.g. minimum average consumption) or Bayesian shrinkage.
- **Explicit change-point detection**: The current slope change heuristic
  approximates a single change point via first/second half. Libraries such as
  `ruptures` could provide more sophisticated change-point analysis if needed.
- **Occupancy and events**: If additional metadata (e.g. occupancy, meter
  replacement, disconnection) becomes available, we should mask or reset
  the time series at these events to avoid misinterpreting legitimate
  consumption changes as subcounting.

Despite these limitations, the current implementation provides a **practical,
transparent, and fully integrated** subcounting signal that can already
enhance the prioritisation of meters for inspection and maintenance.


