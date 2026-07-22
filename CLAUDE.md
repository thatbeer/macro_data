# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python package (`macro_data`) that fetches economics data — FX rates, commodities, market indices, macro indicators, Treasury yields — from FRED, Yahoo Finance, World Bank, and Bank of Thailand into plain CSV files under `data/`, one file per series. Series to fetch are declared in `catalog.yaml`, not code.

## Commands

```bash
# Setup (uv-managed venv)
uv venv
uv pip install -e ".[dev,notebook]"   # dev = pytest; notebook = matplotlib/ipykernel/nbconvert/mplfinance
copy .env.example .env                # then fill in FRED_API_KEY / BOT_CLIENT_ID (optional)

# Tests
python -m pytest                       # full suite (or: .venv/Scripts/python.exe -m pytest)
python -m pytest tests/test_fred.py -v # single file
python -m pytest tests/test_fred.py::test_fetch_parses_observations -v  # single test

# Execute a notebook end-to-end (verifies it actually runs, not just parses)
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/<name>.ipynb --ExecutePreprocessor.timeout=180
```

There is no lint/format command configured. Tests are the only CI-equivalent check; run the full suite before committing package changes.

**Jupyter kernel:** notebooks are pinned to a dedicated kernel (`macro-data-venv`, display name "macro-data (.venv)") registered against this project's `.venv`, not the ambient `python3` kernel. If notebook execution fails with `ModuleNotFoundError` for a dependency that's clearly installed, the kernel likely isn't registered — fix with:
```bash
.venv/Scripts/python.exe -m ipykernel install --user --name macro-data-venv --display-name "macro-data (.venv)"
```

## Architecture

**Data flow:** `catalog.yaml` → `pipeline.py` orchestrates → a `BaseSource` fetcher (one per data provider) → `schema.normalize()` → `store.py` writes/merges CSV.

- **`macro_data/schema.py`** — the canonical series shape every fetcher must produce: a DataFrame indexed by `date` (naive datetime, ascending, deduped) with a single `value` column (float64). `normalize()` is the boundary — it coerces raw API output into this shape (drops non-numeric rows, strips timezones, keeps the last row on duplicate dates) so bad source data fails loudly at the fetcher, not downstream in the store.
- **`macro_data/store.py`** — CSV persistence at `data/<source>/<series_id>.csv`. `append()` merges new rows into existing ones (incoming values win on duplicate dates — sources revise recent data), then writes atomically (`.tmp` file + `os.replace`).
- **`macro_data/catalog.py`** — parses `catalog.yaml` into `SeriesConfig(id, source, name, params)`. Any YAML key besides `id`/`source`/`name` is source-specific and passed through as `params` untouched (e.g. `ticker` for yahoo, `series` for fred, `indicator`/`country` for worldbank, `url`/`value_field`/`query` for bot).
- **`macro_data/sources/*.py`** — one `BaseSource` subclass per provider, each implementing `fetch(cfg, start=None) -> DataFrame`. `start=None` means full history; otherwise fetch only rows from `start` onward. A source with a required API key raises `MissingKeyError(env_var)` rather than crashing — this becomes a per-series `"failed: ..."` status, not a hard stop.
- **`macro_data/pipeline.py`** — orchestration. `update_all()` / `update(source_name)` iterate `SeriesConfig`s, compute each series' `start` from `store.last_date() + 1 day` (skipping the fetch entirely and returning `"up-to-date"` if that start is already in the future — some APIs error on a future date range), call the source's `fetch()`, and `store.append()` the result. **Every series is wrapped in its own try/except** — one failing series (bad ticker, missing key, network error) never blocks the others; its status becomes `"failed: <exception>"` in the returned dict. This error-isolation contract is load-bearing: don't let an exception propagate out of `_run()`.
- **`macro_data/__init__.py`** — the only public surface: `update_all`, `update`, `load`, `list_series`. Notebooks and scripts should import from here, not reach into submodules.

**Adding a series:** edit `catalog.yaml` only — no code.

**Adding a source:** create `macro_data/sources/<name>.py` with a `BaseSource` subclass whose `fetch()` returns a frame through `schema.normalize()`, register the class in `SOURCES` in `pipeline.py`, add mocked-API tests (no real network calls — mock `requests.get` / `yfinance.download`) in `tests/test_<name>.py`.

**Deliberate scope boundary — OHLCV:** the canonical schema is single-value only (`date`, `value`). Full OHLCV bars (open/high/low/close/volume) don't fit it and are *not* stored through `macro_data`/`catalog.yaml` — `notebooks/fx_ohlcv_query.ipynb` queries `yfinance` directly and persists to a separate `data/yahoo_ohlcv/` folder outside the package's store. Don't try to force multi-column data into the schema; follow that notebook's pattern instead.

**Design docs:** `docs/superpowers/specs/` and `docs/superpowers/plans/` hold the original design spec and implementation plan, useful for the reasoning behind schema/store/pipeline decisions.

## Notebooks

Each notebook in `notebooks/` is executed end-to-end before being committed (via `nbconvert --execute --inplace`), so their saved outputs reflect real runs, not just source code:

- `data_gathering_demo.ipynb` — catalog inspection, fetching from all four sources, loading/plotting, incremental re-run behavior.
- `usd_thb_trend_and_indices.ipynb` — USD/THB trend (moving averages, 52-week range, volatility), US Dollar Index, and an equal-weighted "Baht Strength Index" proxy (Bank of Thailand's official NEER needs API credentials not configured here).
- `bonds_and_economic_indicators.ipynb` — US Treasury yield curve, the 10Y-3M spread (recession indicator), and US-vs-Thailand indicator comparisons.
- `fx_ohlcv_query.ipynb` — OHLCV bars queried directly via `yfinance` (see scope boundary above).

## Keyless vs. keyed sources

`yahoo` and `worldbank` need no credentials and work out of the box. `fred` (`FRED_API_KEY`) and `bot` (`BOT_CLIENT_ID`) need free API keys in `.env` (see `.env.example`) — until configured, their series report `"failed: environment variable ... is not set"` rather than erroring, which is expected behavior, not a bug to fix.

## BigQuery loader (optional)

`scripts/load_to_bigquery.py` is a separate, opt-in path that fetches BOT/Yahoo/FRED
series directly from their APIs and loads them into per-category BigQuery staging
tables (`fx`, `commodities`, `rates`, `equities`, `macro`), truncating and reloading
each table on every run. It's independent of the CSV pipeline above — it does not
read or write `data/`, and World Bank series are out of scope (not fetched by this
script).

Requires the `bigquery` extra (`uv pip install -e ".[bigquery]"`) and `GCP_PROJECT` /
`BQ_DATASET` in `.env` (see `.env.example`). Run with:

```bash
python scripts/load_to_bigquery.py
```

Series-to-category mapping lives in `scripts/bigquery_categories.py`; a catalog
series with `source: bot|yahoo|fred` and no entry there raises immediately rather
than silently being skipped.
