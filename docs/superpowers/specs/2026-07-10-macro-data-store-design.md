# Macro Data Store — Design

**Date:** 2026-07-10
**Status:** Approved

## Purpose

A Python package that collects economics data (FX rates, commodities, economic
indices, macro indicators) from external sources into a local store of CSV
files, for consumption from Python/pandas.

## Requirements

- Sources in v1: FRED, Yahoo Finance (via `yfinance`), World Bank, Bank of
  Thailand. Adding a new source later must be cheap (one module).
- Storage: plain CSV files under `data/`, one file per series.
- Consumption: Python API — `load("usd_thb")` returns a date-indexed
  pandas DataFrame.
- Trigger: importable, modular Python functions (`update_all()`,
  `update(source)`); no scheduler or daemon. A CLI/scheduler can wrap these
  later.
- Series selection is declarative via `catalog.yaml`, not code.

## Architecture

```
Macro_data/
├── macro_data/
│   ├── __init__.py          # public API: update_all(), update(), load(), list_series()
│   ├── schema.py            # canonical schema + normalization/validation helpers
│   ├── store.py             # CSV read/write: data/<source>/<series_id>.csv
│   ├── catalog.py           # parse catalog.yaml into SeriesConfig objects
│   ├── pipeline.py          # update orchestration, incremental logic, error isolation
│   └── sources/
│       ├── base.py          # BaseSource ABC: fetch(cfg, start) -> DataFrame
│       ├── fred.py          # fredapi; needs FRED_API_KEY
│       ├── yahoo.py         # yfinance; no key
│       ├── worldbank.py     # World Bank API v2 via requests; no key
│       └── bot.py           # Bank of Thailand API via requests; needs BOT_CLIENT_ID
├── catalog.yaml             # which series to fetch, per source
├── data/                    # output CSVs (gitignored except .gitkeep)
├── tests/                   # mocked-API unit tests + store round-trip tests
├── .env.example             # FRED_API_KEY=, BOT_CLIENT_ID=
└── pyproject.toml
```

## Canonical schema

Every fetcher returns a DataFrame with:

- index: `date` (`datetime64[ns]`, naive, ascending, unique)
- column: `value` (`float64`)

The store writes CSV as two columns `date,value` (ISO dates). Metadata
(source, series id, friendly name, units) lives in the catalog, not in the
data files.

## Catalog format

```yaml
series:
  - id: usd_thb            # unique key; also the filename
    source: yahoo
    ticker: "THB=X"
    name: "USD/THB exchange rate"
  - id: us_cpi
    source: fred
    series: CPIAUCSL
    name: "US CPI (all urban consumers)"
  - id: th_gdp_usd
    source: worldbank
    indicator: NY.GDP.MKTP.CD
    country: THA
    name: "Thailand GDP (current US$)"
```

Unknown per-source keys (`ticker`, `series`, `indicator`, `country`) are
passed through to the source fetcher as a params dict.

## Data flow

1. `update_all()` loads the catalog and groups series by source.
2. For each series, `pipeline` asks `store` for the last stored date.
3. The source's `fetch(cfg, start=last_date + 1 day)` returns new rows in the
   canonical schema (first run: full history, `start=None`).
4. `store.append()` merges new rows with existing (dedup on date, last write
   wins — sources may revise recent values), sorts, writes CSV atomically
   (write temp file, then replace).

## Error handling

- A failing series logs a warning and is skipped; other series and sources
  continue. `update_all()` returns a summary dict
  (`{series_id: "updated (n rows)" | "up-to-date" | "failed: <err>"}`).
- Missing API keys raise a clear error naming the env var, only when that
  source is actually used.
- Fetchers validate/normalize output through `schema.normalize()` so bad
  source data fails loudly at the boundary, not in the store.

## Configuration

API keys via environment variables, loaded from `.env` with `python-dotenv`
(`FRED_API_KEY`, `BOT_CLIENT_ID`). `.env` is gitignored; `.env.example`
documents the names.

## Testing

- Unit tests per fetcher with mocked HTTP/library responses (no network).
- Store tests: round-trip, incremental append with overlap dedup, atomic write.
- Pipeline tests: error isolation (one failing source doesn't stop others),
  incremental start-date computation.

## Out of scope (v1)

CLI, scheduling, revision/point-in-time tracking, non-CSV backends,
dashboards. The store module is the seam where a database backend could be
swapped in later.
