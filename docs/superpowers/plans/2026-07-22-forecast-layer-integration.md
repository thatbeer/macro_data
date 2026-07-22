# Forecast Layer Integration (Smoke Pass) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `AIML-ML-Multi-Forecast-Engine` (a separate, already-existing forecasting engine) to `market_data` via a unifying BigQuery view and a forecast config, validated end-to-end with a synthetic sample since `market_data` has no real rows yet.

**Architecture:** A new `forecasting/` directory in `macro_data` holds a pure-Python synthetic data generator (pytest-covered), a BigQuery view SQL file, two config YAMLs (one smoke-runnable against synthetic parquet, one BigQuery-backed for later real use), and a README. Nothing inside `AIML-ML-Multi-Forecast-Engine` is modified — its CLI is invoked with `--config` pointing at the macro_data-owned file.

**Tech Stack:** pandas, numpy, pyarrow (already available via the `notebook` extra's parquet support / new `forecasting` extra), pytest. No new BigQuery or ML dependencies added to `macro_data` itself.

## Global Constraints

- New top-level directory: `forecasting/` at the repo root (sibling to `macro_data/`, `scripts/`, `notebooks/`).
- `AIML-ML-Multi-Forecast-Engine` (`../AIML-ML-Multi-Forecast-Engine` relative to this repo's root, actually vendored as a subdirectory at `AIML-ML-Multi-Forecast-Engine/` in this checkout) is never modified — no commits inside it, no files added to its tree.
- The view targets a new BigQuery view `your-gcp-project.market_data.forecast_assets`, not a new table — same `your-gcp-project` placeholder convention as `market_data_schema.sql`.
- Config `dataset.keys.item: catalog_id`, `dataset.keys.location: domain_table` — the engine's `GrainKeys` model requires both fields; do not omit `location`.
- `validation.runway_days` must stay ≥ `max(horizon.horizons)` (engine's own `runway_covers_horizon` validator enforces this) — horizons are `[1, 7, 30]`, so `runway_days: 30` is a hard floor, not tunable down.
- The smoke config's `data_sources.modeling_base.path` and `output.predictions.path` are resolved relative to the CLI's cwd at invocation time (inside `AIML-ML-Multi-Forecast-Engine/`), not relative to the config file's own location.

---

### Task 1: Synthetic sample generator

**Files:**
- Create: `forecasting/generate_synthetic_sample.py`
- Create: `forecasting/__init__.py` (empty — makes the directory importable)
- Modify: `tests/conftest.py`
- Test: `tests/test_generate_synthetic_sample.py`

**Interfaces:**
- Produces: `generate_synthetic_assets(n_assets_per_domain: int = 5, start: str = "2023-01-01", end: str = "2026-07-22", seed: int = 42) -> pd.DataFrame` with columns `catalog_id` (str), `date` (datetime64), `value` (float64), `domain_table` (str, one of `"fx_rates"`, `"commodity_futures"`, `"bars_ohlcv"`). Consumed by Task 3's `main()` invocation, no other task depends on its internals.

- [ ] **Step 1: Write the failing test**

Create `tests/test_generate_synthetic_sample.py`:

```python
import pandas as pd

from generate_synthetic_sample import generate_synthetic_assets


def test_generate_synthetic_assets_shape():
    df = generate_synthetic_assets(n_assets_per_domain=3, start="2024-01-01", end="2024-01-31", seed=1)

    assert list(df.columns) == ["catalog_id", "date", "value", "domain_table"]
    assert df["catalog_id"].nunique() == 9  # 3 domains * 3 assets
    assert set(df["domain_table"].unique()) == {"fx_rates", "commodity_futures", "bars_ohlcv"}
    assert df["value"].notna().all()
    assert (df["value"] > 0).all()
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_generate_synthetic_assets_deterministic():
    df1 = generate_synthetic_assets(seed=7)
    df2 = generate_synthetic_assets(seed=7)
    pd.testing.assert_frame_equal(df1, df2)


def test_generate_synthetic_assets_date_range():
    df = generate_synthetic_assets(n_assets_per_domain=1, start="2024-01-01", end="2024-01-05", seed=1)
    one_series = df[df["catalog_id"] == "fx_rates_synth_00"]
    assert len(one_series) == 5
    assert one_series["date"].min() == pd.Timestamp("2024-01-01")
    assert one_series["date"].max() == pd.Timestamp("2024-01-05")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_generate_synthetic_sample.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generate_synthetic_sample'`

- [ ] **Step 3: Add `forecasting/` to the test import path**

Modify `tests/conftest.py` — current content is:

```python
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

Replace with:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
FORECASTING = ROOT / "forecasting"
for path in (SRC, FORECASTING):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
```

- [ ] **Step 4: Create the empty package marker**

Create `forecasting/__init__.py` (empty file).

- [ ] **Step 5: Write the generator**

Create `forecasting/generate_synthetic_sample.py`:

```python
"""Synthetic sample shaped like the forecast_assets BigQuery view (see
forecasting/market_data_forecast_view.sql), for smoke-testing the forecast
config's dataset/keys mapping without live BigQuery data."""

from pathlib import Path

import numpy as np
import pandas as pd

DOMAIN_BASE_PRICE_RANGE = {
    "fx_rates": (1.0, 40.0),
    "commodity_futures": (20.0, 2000.0),
    "bars_ohlcv": (50.0, 5000.0),
}


def generate_synthetic_assets(
    n_assets_per_domain: int = 5,
    start: str = "2023-01-01",
    end: str = "2026-07-22",
    seed: int = 42,
) -> pd.DataFrame:
    """Returns a DataFrame with columns (catalog_id, date, value, domain_table) --
    one random-walk price series per synthetic asset, one row per domain per asset
    per date."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start, end=end, freq="D")

    frames = []
    for domain, (low, high) in DOMAIN_BASE_PRICE_RANGE.items():
        for i in range(n_assets_per_domain):
            base_price = rng.uniform(low, high)
            daily_returns = rng.normal(loc=0.0002, scale=0.01, size=len(dates))
            prices = base_price * np.cumprod(1 + daily_returns)
            frames.append(
                pd.DataFrame(
                    {
                        "catalog_id": f"{domain}_synth_{i:02d}",
                        "date": dates,
                        "value": prices,
                        "domain_table": domain,
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    df = generate_synthetic_assets()
    out_path = Path(__file__).parent / "data" / "synthetic_forecast_assets.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"wrote {len(df)} rows ({df['catalog_id'].nunique()} assets) to {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python -m pytest tests/test_generate_synthetic_sample.py -v`
Expected: 3 passed

- [ ] **Step 7: Run the full suite to confirm no regressions**

Run: `python -m pytest -q`
Expected: all tests pass (previous count + 3)

- [ ] **Step 8: Commit**

```bash
git add forecasting/__init__.py forecasting/generate_synthetic_sample.py tests/conftest.py tests/test_generate_synthetic_sample.py
git commit -m "$(cat <<'EOF'
Add synthetic sample generator for the forecast layer smoke test

Pure pandas/numpy generator producing data shaped like the
forecast_assets BigQuery view, so the forecast config can be
smoke-tested without live market_data rows.
EOF
)"
```

---

### Task 2: View SQL and config files

**Files:**
- Create: `forecasting/market_data_forecast_view.sql`
- Create: `forecasting/configs/market_data_assets_smoke.yaml`
- Create: `forecasting/configs/market_data_assets_bigquery.yaml`
- Create: `forecasting/README.md`

**Interfaces:**
- Produces: `forecasting/configs/market_data_assets_smoke.yaml`, consumed directly by Task 3 (no other task reads it).

- [ ] **Step 1: Write the view SQL**

Create `forecasting/market_data_forecast_view.sql`:

```sql
-- forecast_assets: unifies every daily, price-like asset in market_data onto one
-- shape for AIML-ML-Multi-Forecast-Engine. See
-- docs/superpowers/specs/2026-07-22-forecast-layer-integration-design.md.
--
-- Replace `your-gcp-project` with your actual GCP project id, matching
-- market_data_schema.sql. Not applied by any script in this repo -- run by
-- hand (bq query / BigQuery console) once market_data_schema.sql has been
-- applied to a real project.

CREATE VIEW `your-gcp-project.market_data.forecast_assets` AS

SELECT
  catalog_id,
  rate_date AS date,
  rate AS value,
  'fx_rates' AS domain_table
FROM `your-gcp-project.market_data.fx_rates`

UNION ALL

SELECT
  catalog_id,
  trade_date AS date,
  close AS value,
  'commodity_futures' AS domain_table
FROM `your-gcp-project.market_data.commodity_futures`

UNION ALL

SELECT
  s.catalog_id,
  DATE(b.bar_start_ts) AS date,
  b.close AS value,
  'bars_ohlcv' AS domain_table
FROM `your-gcp-project.market_data.bars_ohlcv` AS b
INNER JOIN `your-gcp-project.market_data.symbols` AS s
  ON b.symbol_id = s.symbol_id
WHERE b.`interval` = 'daily';
```

- [ ] **Step 2: Write the smoke config**

Create `forecasting/configs/market_data_assets_smoke.yaml`:

```yaml
# Smoke-tests the market_data -> forecast_assets -> AIML-ML-Multi-Forecast-Engine
# mapping against synthetic data (forecasting/generate_synthetic_sample.py) --
# market_data has no real rows yet. See
# docs/superpowers/specs/2026-07-22-forecast-layer-integration-design.md.
#
# Run from inside AIML-ML-Multi-Forecast-Engine:
#   uv run horizons run --mode smoke --config ../Macro_data/forecasting/configs/market_data_assets_smoke.yaml

mode: experiment

experiment_name: market_data_assets_smoke
artifacts_dir: artifacts/market_data_assets_smoke

dataset:
  target: value
  date: date
  freq: "D"
  keys:
    item: catalog_id
    location: domain_table

data_sources:
  modeling_base:
    type: parquet
    # Relative to the CLI's cwd at invocation time (AIML-ML-Multi-Forecast-Engine/),
    # not relative to this file. Generate it first with:
    #   python forecasting/generate_synthetic_sample.py
    path: ../Macro_data/forecasting/data/synthetic_forecast_assets.parquet

preprocessing:
  densify_grid: true
  detrend:
    mode: normal
    window: 28
  normalize:
    enabled: false
  postprocessing:
    clip_negative: true
    round_to_integer: false

features:
  calendar:
    enabled: true
  events:
    enabled: false
  hierarchical:
    enabled: false
  matrix_features:
    enabled: true
    lags:
      target: [1, 7, 14, 30]
    rolling_means: [7, 30]
    ewma_alphas: [0.1]
  cyclical:
    enabled: false
  volatility:
    enabled: false
  external: []

horizon:
  horizons: [1, 7, 30]
  unit: days
  architectures: [direct]

validation:
  strategy: expanding_window
  n_folds: 1
  window_size_days: 90
  test_days: 30
  runway_days: 30

tuning:
  enabled: false

models:
  selection_metric: mae
  lightgbm:
    enabled: true
    num_boost_round: 50
    early_stopping_rounds: 10
    base_params:
      boosting_type: gbdt
      learning_rate: 0.05
      random_state: 42
      verbose: -1
      n_jobs: -1
      feature_pre_filter: false
    variants:
      - name: lgb_l1
  xgboost:
    enabled: false
  baseline:
    enabled: false

output:
  predictions:
    type: parquet
    path: artifacts/market_data_assets_smoke/predictions.parquet

interpretability:
  shap:
    enabled: false

memory:
  budget_gb: 8.0
  warn_at_fraction: 0.75
  abort_at_fraction: 0.90
  warn_only: true

cache:
  enabled: false
  post_horizon_path: null
  overwrite: false

smoke:
  sample_n_series: 15
  n_folds: 1
  n_trials: 1
  horizons: [1, 7, 30]
  architectures: [direct]
```

- [ ] **Step 3: Write the BigQuery-backed variant (documented, not run this pass)**

Create `forecasting/configs/market_data_assets_bigquery.yaml` — identical to the smoke
config except the data source, for later use once `market_data` has real rows:

```yaml
# Real BigQuery-backed variant of market_data_assets_smoke.yaml -- NOT runnable
# yet, since market_data.forecast_assets has no rows until a real ingestion
# pipeline exists (see project_design.md §9 / the market-data-schema spec's
# non-goals). Kept here so the mapping is ready the moment real data lands.
#
# Run from inside AIML-ML-Multi-Forecast-Engine (once market_data has data):
#   uv run horizons run --mode smoke --config ../Macro_data/forecasting/configs/market_data_assets_bigquery.yaml

mode: experiment

experiment_name: market_data_assets_bigquery
artifacts_dir: artifacts/market_data_assets_bigquery

dataset:
  target: value
  date: date
  freq: "D"
  keys:
    item: catalog_id
    location: domain_table

data_sources:
  modeling_base:
    type: bigquery
    project: your-gcp-project
    dataset: market_data
    table: forecast_assets

preprocessing:
  densify_grid: true
  detrend:
    mode: normal
    window: 28
  normalize:
    enabled: false
  postprocessing:
    clip_negative: true
    round_to_integer: false

features:
  calendar:
    enabled: true
  events:
    enabled: false
  hierarchical:
    enabled: false
  matrix_features:
    enabled: true
    lags:
      target: [1, 7, 14, 30]
    rolling_means: [7, 30]
    ewma_alphas: [0.1]
  cyclical:
    enabled: false
  volatility:
    enabled: false
  external: []

horizon:
  horizons: [1, 7, 30]
  unit: days
  architectures: [direct]

validation:
  strategy: expanding_window
  n_folds: 1
  window_size_days: 90
  test_days: 30
  runway_days: 30

tuning:
  enabled: false

models:
  selection_metric: mae
  lightgbm:
    enabled: true
    num_boost_round: 50
    early_stopping_rounds: 10
    base_params:
      boosting_type: gbdt
      learning_rate: 0.05
      random_state: 42
      verbose: -1
      n_jobs: -1
      feature_pre_filter: false
    variants:
      - name: lgb_l1
  xgboost:
    enabled: false
  baseline:
    enabled: false

output:
  predictions:
    type: parquet
    path: artifacts/market_data_assets_bigquery/predictions.parquet

interpretability:
  shap:
    enabled: false

memory:
  budget_gb: 8.0
  warn_at_fraction: 0.75
  abort_at_fraction: 0.90
  warn_only: true

cache:
  enabled: false
  post_horizon_path: null
  overwrite: false

smoke:
  sample_n_series: 15
  n_folds: 1
  n_trials: 1
  horizons: [1, 7, 30]
  architectures: [direct]
```

- [ ] **Step 4: Write the README**

Create `forecasting/README.md`:

```markdown
# forecasting/

The first slice of a prediction layer over `market_data`: a BigQuery view unifying
every daily, price-like asset onto one shape, and a config wiring that view into
`AIML-ML-Multi-Forecast-Engine` (a separate, already-existing forecasting engine
checked out alongside this repo). See
`docs/superpowers/specs/2026-07-22-forecast-layer-integration-design.md` for the
full design and its non-goals.

## Files

- `market_data_forecast_view.sql` -- `CREATE VIEW market_data.forecast_assets`,
  unioning `fx_rates`, `commodity_futures`, and `bars_ohlcv` (daily interval only)
  onto `(catalog_id, date, value, domain_table)`. Apply by hand against a real GCP
  project (`your-gcp-project` placeholder, same convention as `market_data_schema.sql`)
  -- not run by any script here.
- `generate_synthetic_sample.py` -- generates a local parquet file shaped like the
  view's output, since `market_data` has no real rows yet.
- `configs/market_data_assets_smoke.yaml` -- runnable now, against the synthetic
  sample.
- `configs/market_data_assets_bigquery.yaml` -- the real BigQuery-backed variant,
  for once `market_data` has actual data (not runnable yet).

## Running the smoke test

```bash
# 1. From this repo's root, generate the synthetic sample:
python forecasting/generate_synthetic_sample.py

# 2. From AIML-ML-Multi-Forecast-Engine's own root (checked out as a sibling
#    directory -- paths inside the config are resolved relative to this cwd):
cd AIML-ML-Multi-Forecast-Engine
uv run horizons run --mode smoke --config ../Macro_data/forecasting/configs/market_data_assets_smoke.yaml
```

A successful run writes `AIML-ML-Multi-Forecast-Engine/artifacts/market_data_assets_smoke/predictions.parquet`
and prints a leaderboard summary. This validates the `dataset`/`keys`/`horizon`
mapping end to end -- the predictions themselves are meaningless (synthetic
random-walk data), not a real forecast.

## Known limitation: the item x location grain

The engine's grain model is a fixed two-level `item` x `location` pair (see its
`GrainKeys` config). `market_data` assets only have one natural identifier
(`catalog_id`), so this maps `item: catalog_id`, `location: domain_table`
(`fx_rates` / `commodity_futures` / `bars_ohlcv`). Each `catalog_id` has exactly
one `domain_table` value, so `location` never varies independently the way it
would for a real item x store panel -- an accepted limitation, not a bug.
```

- [ ] **Step 5: Commit**

```bash
git add forecasting/market_data_forecast_view.sql forecasting/configs/market_data_assets_smoke.yaml forecasting/configs/market_data_assets_bigquery.yaml forecasting/README.md
git commit -m "$(cat <<'EOF'
Add the forecast_assets view SQL and forecast engine configs

Unifies market_data's daily price-like domains (fx_rates,
commodity_futures, bars_ohlcv) onto one shape for
AIML-ML-Multi-Forecast-Engine. Smoke config runs against synthetic
data; the BigQuery-backed variant is documented for once market_data
has real rows.
EOF
)"
```

---

### Task 3: Run the smoke test end to end

**Files:**
- None created — this task generates data and runs an external CLI, verifying Task 1
  and Task 2's outputs actually work together.

**Interfaces:**
- Consumes: `generate_synthetic_assets()` from Task 1, `forecasting/configs/market_data_assets_smoke.yaml` from Task 2.
- Produces: nothing new in `macro_data` — the smoke run's artifacts land inside `AIML-ML-Multi-Forecast-Engine/artifacts/market_data_assets_smoke/` (see Global Constraints), which is that repo's own concern, not committed here.

- [ ] **Step 1: Generate the synthetic sample**

Run from this repo's root:

```bash
python forecasting/generate_synthetic_sample.py
```

Expected: prints `wrote <N> rows (15 assets) to .../forecasting/data/synthetic_forecast_assets.parquet` and the file exists.

- [ ] **Step 2: Confirm AIML-ML-Multi-Forecast-Engine's own environment is set up**

Run:

```bash
cd AIML-ML-Multi-Forecast-Engine
uv sync
```

Expected: completes without error (installs/verifies that repo's own dependencies — this does not touch `macro_data`'s venv).

- [ ] **Step 3: Run the smoke test**

Run (from inside `AIML-ML-Multi-Forecast-Engine/`):

```bash
uv run horizons run --mode smoke --config ../Macro_data/forecasting/configs/market_data_assets_smoke.yaml
```

Expected: exits 0 and prints a leaderboard/summary. If it instead raises a Pydantic
`ValidationError` naming a specific config field, that field's value in
`forecasting/configs/market_data_assets_smoke.yaml` is wrong or missing — cross-check
it against `pipelines/demand_forecast/src/config/schema.py` and
`pipelines/demand_forecast/configs/REFERENCE.yaml` in the engine repo, fix the exact
field named in the error, and re-run this step. Do not change `dataset.keys` away
from `catalog_id`/`domain_table` to work around an error — if those specifically are
rejected, stop and report back rather than guessing a workaround, since that mapping
is a deliberate design decision (see the spec's "Grain mapping" section), not an
arbitrary placeholder.

- [ ] **Step 4: Verify the output**

Run (from inside `AIML-ML-Multi-Forecast-Engine/`):

```bash
python -c "import pandas as pd; df = pd.read_parquet('artifacts/market_data_assets_smoke/predictions.parquet'); print(df.shape); print(df.head())"
```

Expected: a non-empty DataFrame with prediction rows (exact columns depend on the
engine's output contract — at minimum one row per `(catalog_id, horizon)` combination
forecast in the smoke run).

- [ ] **Step 5: Run macro_data's own test suite once more to confirm no regressions**

Run (from this repo's root):

```bash
python -m pytest -q
```

Expected: all tests pass — this task didn't change any `macro_data` source, so this is
a final sanity check, not expected to catch anything new.

---

## Self-Review Notes

- **Spec coverage:** the view SQL (with the `bars_ohlcv` join through `symbols`), the
  synthetic generator, both config variants, the `item`/`location` grain mapping, the
  cwd-relative path gotcha, and the README are all present across Tasks 1-2; Task 3
  is the spec's "Testing" section made concrete (actually running the smoke test, not
  just describing that it should be run).
- **Placeholder scan:** no TBD/TODO. `your-gcp-project` is the same intentional,
  documented placeholder convention as `market_data_schema.sql`. Task 3 Step 3's
  "if validation fails" guidance is deliberately procedural (check the exact field
  against the engine's own schema/reference files) rather than a vague "handle errors"
  placeholder, since the exact Pydantic error can't be predicted without running it.
- **Type consistency:** `generate_synthetic_assets()`'s signature and column names
  (`catalog_id`, `date`, `value`, `domain_table`) match exactly between Task 1's
  implementation, its test, the smoke config's `dataset.target`/`date`/`keys` in
  Task 2, and the view SQL's output columns — all four were written from the same
  source-of-truth shape defined in the spec.
