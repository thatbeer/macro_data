# BigQuery Loader — Design

**Date:** 2026-07-22
**Status:** Approved

## Purpose

The project currently stores every series as a per-file CSV under `data/`
(`macro_data/store.py`). We want a second, independent path that fetches the
same source data and lands it in BigQuery, matching the pipeline sketched in
the provided diagram:

```
Bank of Thailand API ─┐
Yahoo Finance API     ├─▶ Scheduled extractor ─▶ Validate and transform ─▶ BigQuery staging (per category) ─▶ BigQuery
FRED API              ─┘
```

This is a new, additive capability — it does not replace or modify the
existing CSV pipeline.

## Requirements

- Fetch series directly from the BOT, Yahoo Finance, and FRED sources
  (reusing the existing `BaseSource.fetch()` implementations), independent
  of the local CSV store.
- Transform each series' normalized `(date, value)` frame into a row shape
  suitable for a BigQuery table, tagged with series/category metadata.
- Group series into category-specific staging tables and load them into
  BigQuery, truncating and reloading each table on every run.
- One failing series (missing API key, network error, bad ticker) must not
  block any other series from being fetched and loaded — same
  error-isolation contract as `macro_data/pipeline.py`.
- One failing category load must not block any other category from
  loading.
- No hardcoded GCP project/dataset — configured via environment variables,
  consistent with the project's existing `.env` convention.
- Core `macro_data` package stays free of any BigQuery/GCP dependency; the
  loader is a separate, opt-in tool.

## Non-goals

- World Bank series are out of scope (not shown in the diagram's source
  boxes) — they remain CSV-only.
- No GCS "raw landing zone" and no scheduler — out of scope for this pass;
  may be added later as a separate design.
- No incremental/merge loads — every run does a full truncate-and-reload
  per category table. Row-level dedup/upsert is not implemented.
- No consolidation step beyond the category staging tables — the diagram's
  final "BigQuery" box is the dataset that contains the staging tables, not
  a further merge into one table.
- Doesn't touch `macro_data/store.py`'s CSV pipeline or `catalog.yaml`'s
  existing shape (no `category` field added to the catalog).

## Architecture

New standalone tree outside the `macro_data` package, mirroring its
existing `schema.py` / `store.py` / `pipeline.py` split (pure transform
logic separate from I/O, separate from orchestration):

```
scripts/
  bigquery_categories.py   # pure: series_id -> category lookup
  bigquery_transform.py    # pure: raw fetch DataFrame -> BigQuery-ready DataFrame
  bigquery_load.py         # I/O: BigQuery client wrapper (truncate + load)
  load_to_bigquery.py      # orchestration + CLI entrypoint
```

### Data flow

For each `SeriesConfig` in `catalog.yaml` whose `source` is `bot`, `yahoo`,
or `fred`:

1. Call that source's existing `fetch(cfg, start=None)` directly (full
   history each run; the CSV store is not read or written). This already
   performs the diagram's "validate" step: `BaseSource.fetch()` returns
   data through `schema.normalize()`, which drops non-numeric rows, dedups
   dates, and strips timezones — no separate validation code is needed here.
2. `bigquery_transform.annotate(cfg, category, raw_df)` adds `series_id`,
   `source`, `name`, `category`, `loaded_at` columns to the normalized
   `(date, value)` frame and resets the index so `date` is a plain column.
3. Per-series frames are grouped by category and concatenated.
4. `bigquery_load.load_category_table(project, dataset, category, df)`
   truncates and reloads that category's staging table.

### `bigquery_categories.py`

```python
CATEGORY_BY_SERIES = {
    "usd_thb": "fx", "eur_usd": "fx", "usd_dxy": "fx",
    "eur_thb": "fx", "jpy_thb": "fx", "gbp_thb": "fx", "usd_thb_bot": "fx",
    "gold_usd": "commodities", "brent_oil": "commodities", "wti_oil": "commodities",
    "silver_usd": "commodities", "copper_usd": "commodities", "natural_gas": "commodities",
    "us_3m_yield": "rates", "us_5y_yield": "rates", "us_10y_yield": "rates",
    "us_30y_yield": "rates",
    "fed_funds_rate": "macro", "us_cpi": "macro",
    "sp500": "equities", "set_index": "equities",
}


def category_for(series_id: str) -> str:
    """Raise KeyError if series_id has no category mapping (fail loud, not silent skip)."""
```

`category_for()` raising on an unmapped id is deliberate: a new catalog
series with `source: bot|yahoo|fred` and no entry here should be a visible
error at run time, not a series that silently never reaches BigQuery.

### `bigquery_transform.py`

```python
def annotate(cfg: SeriesConfig, category: str, raw: pd.DataFrame) -> pd.DataFrame:
    """raw is the normalized (date-indexed, 'value' column) frame from BaseSource.fetch().
    Returns a flat frame with columns: series_id, source, name, category, date, value, loaded_at.
    """
```

Pure function — no I/O, no BigQuery dependency, trivially unit-testable.

### `bigquery_load.py`

```python
def load_category_table(client, project: str, dataset: str, category: str, df: pd.DataFrame) -> int:
    """Load df into `{project}.{dataset}.{category}` with WRITE_TRUNCATE. Returns row count loaded."""
```

- Explicit BigQuery schema (not autodetect): `series_id STRING`,
  `source STRING`, `name STRING`, `date DATE`, `value FLOAT64`,
  `loaded_at TIMESTAMP`.
- `write_disposition=WRITE_TRUNCATE`, `create_disposition=CREATE_IF_NEEDED`
  — table is created on first run, replaced wholesale on every run after.
- Auth via standard Application Default Credentials /
  `GOOGLE_APPLICATION_CREDENTIALS` (default `google.cloud.bigquery.Client()`
  behavior) — no custom credential-handling code.

### `load_to_bigquery.py` (orchestration + CLI)

- Reads `GCP_PROJECT` and `BQ_DATASET` from the environment (via
  `python-dotenv`'s `load_dotenv()`, matching `pipeline.py`); missing either
  one fails fast before any fetch is attempted.
- Filters `catalog.yaml` to `source in {bot, yahoo, fred}`.
- Fetches each series independently; a per-series failure (e.g.
  `MissingKeyError` for `FRED_API_KEY`/`BOT_CLIENT_ID`, network error) is
  caught, logged, and recorded as `"failed: ..."` — the rest continue,
  mirroring `pipeline._run()`'s try/except-per-series pattern.
- Groups successful series by category, loads each category table
  independently; a per-category load failure is caught and recorded
  without blocking the other categories.
- Returns a status dict (fetch statuses keyed by series id, load statuses
  keyed by category) and prints a summary. Runnable directly:
  `python scripts/load_to_bigquery.py`.

## Configuration

`.env.example` gets two new vars, documented alongside the existing ones:

```
# BigQuery loader (scripts/load_to_bigquery.py) — optional, only needed to run it
GCP_PROJECT=
BQ_DATASET=
```

`pyproject.toml` gets a new opt-in extra (base install untouched):

```toml
[project.optional-dependencies]
bigquery = ["google-cloud-bigquery>=3.11", "pyarrow>=14.0"]
```

## Error handling

Two independent isolation layers, both modeled on `pipeline.py`'s existing
per-series try/except:

- **Fetch layer:** one series' `fetch()` raising never stops the others.
- **Load layer:** one category's BigQuery load raising never stops the
  others.
- **Config layer:** `GCP_PROJECT`/`BQ_DATASET` unset, or an unmapped
  `series_id` in `bigquery_categories.py`, are treated as programmer/config
  errors and raise immediately at startup — these are not per-series
  runtime conditions, they mean the tool isn't set up correctly yet.

## Testing

No real network or GCP calls, matching the project's existing convention
(mocked `requests`/`yfinance` in the source tests):

- `tests/test_bigquery_categories.py` — every `bot`/`yahoo`/`fred` series
  currently in `catalog.yaml` has a category entry; an unmapped id raises
  `KeyError`.
- `tests/test_bigquery_transform.py` — pure function tests: correct
  columns/dtypes produced from a sample normalized frame, no mocking
  needed.
- `tests/test_bigquery_load.py` — mocks `google.cloud.bigquery.Client`;
  asserts `WRITE_TRUNCATE` disposition, correct table ref
  (`project.dataset.category`), and correct explicit schema.
- `tests/test_load_to_bigquery.py` — mocks source `fetch()` (fake
  `BaseSource` subclasses, same pattern as `test_pipeline.py`'s
  `FakeOkSource`/`FakeBadSource`) and the BigQuery client; asserts
  fetch-layer and load-layer error isolation, and that the returned status
  dict shapes match.

## Out of scope

- GCS raw landing zone, scheduler/cron trigger — separate future design.
- World Bank source.
- Incremental/merge loads, row-level dedup in BigQuery.
- Any change to `macro_data/store.py`, `catalog.yaml`, or the CSV pipeline.
