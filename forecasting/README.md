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
