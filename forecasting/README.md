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

Verified working end to end on 2026-07-22 (Windows). From this repo's root:

```bash
python forecasting/generate_synthetic_sample.py
```

Then from `AIML-ML-Multi-Forecast-Engine`'s own root, wherever it's checked out (it
may be nested inside this repo, e.g. `Macro_data/AIML-ML-Multi-Forecast-Engine/`, or a
true sibling directory -- the `--config` path works either way since it's an absolute
path):

```bash
cd AIML-ML-Multi-Forecast-Engine
uv sync   # first time only
PYTHONIOENCODING=utf-8 uv run horizons run --mode smoke --config /absolute/path/to/forecasting/configs/market_data_assets_smoke.yaml
```

`data_sources.modeling_base.path` inside the smoke config is an absolute path (not
relative to cwd) since the two repos aren't guaranteed to be laid out as siblings.

**Windows gotcha:** without `PYTHONIOENCODING=utf-8`, the run completes successfully
(all artifacts are written) but then crashes with `UnicodeEncodeError: 'charmap'
codec can't encode characters...` while printing the final leaderboard to the
console -- the legacy Windows terminal's `cp1252` encoding can't render a character
`rich` writes. This is cosmetic (every output file is already on disk by that point)
but the env var avoids it entirely and gets a clean exit code 0.

A successful smoke run does **not** write `output.predictions.path` (that's a
production/inference-mode artifact) -- in `smoke`/`experiment` mode the real outputs
land under `artifacts/market_data_assets_smoke/_smoke/`: `leaderboard.parquet`,
`test_eval.parquet` (aggregate CV metrics), `champions_manifest.json`, per-horizon
feature caches in `_horizon_cache/`, and diagnostic plots in `viz/` -- including
`error_by_catalog_id.png` and `error_by_domain_table.png`, which is direct
confirmation the `item`/`location` grain mapping below was picked up correctly (all
15 synthetic `catalog_id`s across all 3 `domain_table` values flowed through feature
engineering, CV, and evaluation). The predictions themselves are meaningless
(synthetic random-walk data), not a real forecast -- this run validates the
`dataset`/`keys`/`horizon` mapping, nothing more.

## Known limitation: the item x location grain

The engine's grain model is a fixed two-level `item` x `location` pair (see its
`GrainKeys` config). `market_data` assets only have one natural identifier
(`catalog_id`), so this maps `item: catalog_id`, `location: domain_table`
(`fx_rates` / `commodity_futures` / `bars_ohlcv`). Each `catalog_id` has exactly
one `domain_table` value, so `location` never varies independently the way it
would for a real item x store panel -- an accepted limitation, not a bug.
