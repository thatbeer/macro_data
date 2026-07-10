# Macro Data Store

Collects economics data (FX rates, commodities, indices, macro indicators)
from FRED, Yahoo Finance, World Bank, and Bank of Thailand into plain CSV
files under `data/`, one file per series.

## Setup

```bash
uv venv
uv pip install -e ".[dev,notebook]"   # dev = pytest, notebook = matplotlib/jupyter for the demo notebook
copy .env.example .env                # then fill in FRED_API_KEY / BOT_CLIENT_ID (optional)
```

## Usage

```python
from macro_data import update_all, update, load, list_series

update_all()          # fetch everything in catalog.yaml (incremental)
update("yahoo")       # or just one source

df = load("usd_thb")  # date-indexed pandas DataFrame with a 'value' column
```

Each run only fetches rows newer than what is already stored. Failing
series are reported as `"failed: ..."` in the returned summary and never
block other series.

See [`notebooks/data_gathering_demo.ipynb`](notebooks/data_gathering_demo.ipynb)
for a walkthrough: inspecting the catalog, fetching from each source, loading
and plotting series, and re-running updates incrementally.

For USD/THB trend analysis (moving averages, 52-week range, volatility)
alongside the US Dollar Index and an equal-weighted Baht Strength Index
proxy, see
[`notebooks/usd_thb_trend_and_indices.ipynb`](notebooks/usd_thb_trend_and_indices.ipynb).

For the US Treasury yield curve (including the 10Y-3M spread, a classic
recession indicator) and a US-vs-Thailand comparison across GDP, inflation,
unemployment, government debt, and current account balance, see
[`notebooks/bonds_and_economic_indicators.ipynb`](notebooks/bonds_and_economic_indicators.ipynb).

For full OHLCV (open/high/low/close/volume) bars — which don't fit the
single-`value` canonical schema above — see
[`notebooks/fx_ohlcv_query.ipynb`](notebooks/fx_ohlcv_query.ipynb). It queries
Yahoo Finance directly for spot FX and currency futures, contrasts spot FX's
always-zero volume (OTC, no consolidated tape) against real futures volume,
and renders a candlestick + volume chart.

## Adding a series

Add an entry to `catalog.yaml` — no code needed:

```yaml
  - id: my_series
    source: yahoo          # yahoo | fred | worldbank | bot
    ticker: "CL=F"         # source-specific params
    name: "WTI crude futures"
```

## Adding a source

1. Create `macro_data/sources/<name>.py` with a `BaseSource` subclass whose
   `fetch(cfg, start)` returns a DataFrame via `schema.normalize()`.
2. Register the class in `SOURCES` in `macro_data/pipeline.py`.
3. Add mocked-API tests in `tests/test_<name>.py`.

## Data format

`data/<source>/<series_id>.csv` with columns `date,value` (ISO dates).
Series metadata (name, tickers, units) lives in `catalog.yaml`.
