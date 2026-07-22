# BigQuery Loader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone script that fetches BOT/Yahoo/FRED series directly from their APIs, transforms them into category-tagged rows, and truncate-reloads them into per-category BigQuery staging tables.

**Architecture:** Four new files under `scripts/`, mirroring `macro_data`'s existing `schema.py`/`store.py`/`pipeline.py` split: a pure category lookup, a pure transform, a BigQuery I/O wrapper, and an orchestration/CLI entrypoint. Independent of `macro_data/store.py`'s CSV pipeline — reuses only the existing `BaseSource.fetch()` implementations and `catalog.yaml`.

**Tech Stack:** Python 3.10+, pandas, `google-cloud-bigquery` (new optional dependency), pytest with mocked BigQuery client (no real network/GCP calls in tests).

## Global Constraints

- Python `>=3.10` (existing `pyproject.toml` requirement).
- New dependency versions: `google-cloud-bigquery>=3.11`, `pyarrow>=14.0`, added as an opt-in `bigquery` extra — the base `macro_data` install stays untouched.
- Category names are exactly: `fx`, `commodities`, `rates`, `equities`, `macro` — one BigQuery table per category, table id `{project}.{dataset}.{category}`.
- BigQuery staging table columns (exact names/types): `series_id STRING`, `source STRING`, `name STRING`, `date DATE`, `value FLOAT64`, `loaded_at TIMESTAMP`.
- Every BigQuery load uses `write_disposition=WRITE_TRUNCATE`, `create_disposition=CREATE_IF_NEEDED`.
- Failure status strings follow the existing `pipeline.py` convention: `f"failed: {exc}"`.
- Env vars: `GCP_PROJECT`, `BQ_DATASET` — read via `python-dotenv`'s `load_dotenv()`, same pattern as `macro_data/pipeline.py`. Missing either raises `RuntimeError` before any fetch happens.
- Only `catalog.yaml` series with `source in {bot, yahoo, fred}` are in scope; World Bank series are excluded (not an error, just filtered out).
- No real network or GCP calls in any test — mock `BaseSource.fetch()` and the BigQuery client, matching the project's existing test convention (see `tests/test_pipeline.py`, `tests/test_bot_api.py`).
- Imports of sibling `scripts/` modules are flat top-level (`from bigquery_categories import category_for`), matching the existing `src/*` flat-import convention (`from bot_api import BOTClient`), not dotted-package imports.

---

### Task 1: Category lookup (`bigquery_categories.py`)

**Files:**
- Create: `scripts/bigquery_categories.py`
- Modify: `tests/conftest.py` (add `scripts/` to `sys.path`, alongside the existing `src/` entry)
- Test: `tests/test_bigquery_categories.py`

**Interfaces:**
- Produces: `CATEGORY_BY_SERIES: dict[str, str]`, `category_for(series_id: str) -> str` (raises `KeyError` if `series_id` has no mapping).

- [ ] **Step 1: Update `tests/conftest.py` to add `scripts/` to `sys.path`**

Read the current file first, then replace its contents:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_bigquery_categories.py`:

```python
from pathlib import Path

import pytest

from macro_data.catalog import load_catalog

from bigquery_categories import CATEGORY_BY_SERIES, category_for


def test_category_for_known_series():
    assert category_for("usd_thb") == "fx"
    assert category_for("gold_usd") == "commodities"
    assert category_for("us_10y_yield") == "rates"
    assert category_for("us_cpi") == "macro"
    assert category_for("sp500") == "equities"


def test_category_for_unknown_series_raises():
    with pytest.raises(KeyError, match="no_such_series"):
        category_for("no_such_series")


def test_every_bot_yahoo_fred_catalog_series_has_a_category():
    catalog_path = Path(__file__).resolve().parent.parent / "catalog.yaml"
    configs = load_catalog(catalog_path)
    missing = [
        c.id
        for c in configs
        if c.source in ("bot", "yahoo", "fred") and c.id not in CATEGORY_BY_SERIES
    ]
    assert missing == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_bigquery_categories.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bigquery_categories'`

- [ ] **Step 4: Write the implementation**

Create `scripts/bigquery_categories.py`:

```python
"""series_id -> BigQuery staging category lookup.

Only series with source in {bot, yahoo, fred} need an entry here --
World Bank series are out of scope for the BigQuery loader.
"""

CATEGORY_BY_SERIES = {
    # --- fx ---
    "usd_thb": "fx",
    "eur_usd": "fx",
    "usd_dxy": "fx",
    "eur_thb": "fx",
    "jpy_thb": "fx",
    "gbp_thb": "fx",
    "usd_thb_bot": "fx",
    # --- commodities ---
    "gold_usd": "commodities",
    "brent_oil": "commodities",
    "wti_oil": "commodities",
    "silver_usd": "commodities",
    "copper_usd": "commodities",
    "natural_gas": "commodities",
    # --- rates ---
    "us_3m_yield": "rates",
    "us_5y_yield": "rates",
    "us_10y_yield": "rates",
    "us_30y_yield": "rates",
    # --- macro ---
    "fed_funds_rate": "macro",
    "us_cpi": "macro",
    # --- equities ---
    "sp500": "equities",
    "set_index": "equities",
}


def category_for(series_id: str) -> str:
    """Return the BigQuery staging category for series_id.

    Raises KeyError if series_id has no mapping -- a new catalog series
    with an in-scope source must be added here explicitly, it should
    never silently drop out of the BigQuery loader.
    """
    try:
        return CATEGORY_BY_SERIES[series_id]
    except KeyError:
        raise KeyError(
            f"no BigQuery category mapped for series '{series_id}' "
            f"(add it to CATEGORY_BY_SERIES in bigquery_categories.py)"
        ) from None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_bigquery_categories.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_bigquery_categories.py scripts/bigquery_categories.py
git commit -m "Add BigQuery category lookup for bot/yahoo/fred series"
```

---

### Task 2: Row transform (`bigquery_transform.py`)

**Files:**
- Create: `scripts/bigquery_transform.py`
- Test: `tests/test_bigquery_transform.py`

**Interfaces:**
- Consumes: `macro_data.catalog.SeriesConfig` (fields: `id`, `source`, `name`, `params`); `macro_data.schema.normalize(df) -> pd.DataFrame` (date-indexed, `value` column) for building test fixtures.
- Produces: `annotate(cfg: SeriesConfig, category: str, raw: pd.DataFrame, loaded_at: pd.Timestamp) -> pd.DataFrame` returning columns `["series_id", "source", "name", "category", "date", "value", "loaded_at"]`; `group_by_category(frames: list[pd.DataFrame]) -> dict[str, pd.DataFrame]` returning per-category frames with columns `["series_id", "source", "name", "date", "value", "loaded_at"]` (no `category` column — redundant once split into the dict).

- [ ] **Step 1: Write the failing test**

Create `tests/test_bigquery_transform.py`:

```python
import pandas as pd

from macro_data import schema
from macro_data.catalog import SeriesConfig

from bigquery_transform import annotate, group_by_category


def _raw(rows):
    return schema.normalize(pd.DataFrame(rows, columns=["date", "value"]))


def test_annotate_adds_metadata_columns():
    cfg = SeriesConfig(id="usd_thb", source="yahoo", name="USD/THB exchange rate")
    raw = _raw([("2024-01-01", 35.1), ("2024-01-02", 35.2)])
    loaded_at = pd.Timestamp("2026-07-22T00:00:00Z")

    out = annotate(cfg, "fx", raw, loaded_at)

    assert list(out.columns) == [
        "series_id", "source", "name", "category", "date", "value", "loaded_at",
    ]
    assert len(out) == 2
    assert (out["series_id"] == "usd_thb").all()
    assert (out["source"] == "yahoo").all()
    assert (out["name"] == "USD/THB exchange rate").all()
    assert (out["category"] == "fx").all()
    assert (out["loaded_at"] == loaded_at).all()
    assert out["date"].tolist() == [
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-01-02").date(),
    ]
    assert out["value"].tolist() == [35.1, 35.2]


def test_group_by_category_splits_and_drops_category_column():
    cfg_fx = SeriesConfig(id="usd_thb", source="yahoo", name="USD/THB")
    cfg_gold = SeriesConfig(id="gold_usd", source="yahoo", name="Gold")
    loaded_at = pd.Timestamp("2026-07-22T00:00:00Z")
    fx_frame = annotate(cfg_fx, "fx", _raw([("2024-01-01", 35.1)]), loaded_at)
    commodities_frame = annotate(
        cfg_gold, "commodities", _raw([("2024-01-01", 2000.0)]), loaded_at
    )

    grouped = group_by_category([fx_frame, commodities_frame])

    assert set(grouped) == {"fx", "commodities"}
    assert list(grouped["fx"].columns) == [
        "series_id", "source", "name", "date", "value", "loaded_at",
    ]
    assert grouped["fx"]["series_id"].tolist() == ["usd_thb"]
    assert grouped["commodities"]["series_id"].tolist() == ["gold_usd"]


def test_group_by_category_empty_list_returns_empty_dict():
    assert group_by_category([]) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_bigquery_transform.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bigquery_transform'`

- [ ] **Step 3: Write the implementation**

Create `scripts/bigquery_transform.py`:

```python
"""Pure transform: a source's normalized fetch DataFrame -> BigQuery-ready rows.

No I/O, no BigQuery dependency -- validation itself already happened inside
BaseSource.fetch() via schema.normalize().
"""

import pandas as pd

from macro_data.catalog import SeriesConfig


def annotate(
    cfg: SeriesConfig, category: str, raw: pd.DataFrame, loaded_at: pd.Timestamp
) -> pd.DataFrame:
    """raw is the normalized (date-indexed, 'value' column) frame from BaseSource.fetch().

    Returns a flat frame with columns:
    series_id, source, name, category, date, value, loaded_at.
    """
    out = raw.reset_index()[["date", "value"]].copy()
    out["series_id"] = cfg.id
    out["source"] = cfg.source
    out["name"] = cfg.name
    out["category"] = category
    out["date"] = out["date"].dt.date
    out["loaded_at"] = loaded_at
    return out[["series_id", "source", "name", "category", "date", "value", "loaded_at"]]


def group_by_category(frames: list[pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Concatenate annotated frames and split by category.

    Output frames drop the 'category' column (redundant once split into a
    per-category dict -- the dict key already encodes it) and keep exactly:
    series_id, source, name, date, value, loaded_at -- matching
    bigquery_load.SCHEMA.
    """
    if not frames:
        return {}
    combined = pd.concat(frames, ignore_index=True)
    return {
        category: group.drop(columns="category").reset_index(drop=True)
        for category, group in combined.groupby("category")
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_bigquery_transform.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/test_bigquery_transform.py scripts/bigquery_transform.py
git commit -m "Add BigQuery row transform (annotate + group_by_category)"
```

---

### Task 3: BigQuery write wrapper (`bigquery_load.py`)

**Files:**
- Modify: `pyproject.toml` (add `bigquery` optional-dependency group)
- Create: `scripts/bigquery_load.py`
- Test: `tests/test_bigquery_load.py`

**Interfaces:**
- Consumes: a BigQuery client object with a `load_table_from_dataframe(dataframe, destination, job_config=...)` method returning a job with `.result()` (matches `google.cloud.bigquery.Client`'s real interface; tests pass a `MagicMock`).
- Produces: `SCHEMA: list[bigquery.SchemaField]`; `load_category_table(client, project: str, dataset: str, category: str, df: pd.DataFrame) -> int` (returns rows loaded).

- [ ] **Step 1: Add the `bigquery` extra and install it**

Read `pyproject.toml`, then add a new key under `[project.optional-dependencies]` (after the existing `notebook` line):

```toml
bigquery = ["google-cloud-bigquery>=3.11", "pyarrow>=14.0"]
```

Install it into the project's venv:

Run: `uv pip install -e ".[bigquery]"`
Expected: installs `google-cloud-bigquery`, `pyarrow`, and their dependencies without error.

- [ ] **Step 2: Write the failing test**

Create `tests/test_bigquery_load.py`:

```python
from unittest.mock import MagicMock

import pandas as pd
from google.cloud import bigquery

from bigquery_load import SCHEMA, load_category_table


def _df():
    return pd.DataFrame(
        {
            "series_id": ["usd_thb"],
            "source": ["yahoo"],
            "name": ["USD/THB exchange rate"],
            "date": [pd.Timestamp("2024-01-01").date()],
            "value": [35.1],
            "loaded_at": [pd.Timestamp("2026-07-22T00:00:00Z")],
        }
    )


def test_load_category_table_truncates_and_loads():
    client = MagicMock()
    job = MagicMock()
    client.load_table_from_dataframe.return_value = job
    df = _df()

    rows = load_category_table(client, "my-project", "my_dataset", "fx", df)

    assert rows == 1
    job.result.assert_called_once()
    client.load_table_from_dataframe.assert_called_once()
    call_args = client.load_table_from_dataframe.call_args
    assert call_args.args[0] is df
    assert call_args.args[1] == "my-project.my_dataset.fx"
    job_config = call_args.kwargs["job_config"]
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert job_config.create_disposition == bigquery.CreateDisposition.CREATE_IF_NEEDED
    assert job_config.schema == SCHEMA
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_bigquery_load.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bigquery_load'`

- [ ] **Step 4: Write the implementation**

Create `scripts/bigquery_load.py`:

```python
"""BigQuery I/O: truncate-and-reload one category's staging table."""

import pandas as pd
from google.cloud import bigquery

SCHEMA = [
    bigquery.SchemaField("series_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("value", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
]


def load_category_table(
    client, project: str, dataset: str, category: str, df: pd.DataFrame
) -> int:
    """Truncate-and-reload `{project}.{dataset}.{category}` with df's rows.

    Returns the number of rows loaded.
    """
    table_id = f"{project}.{dataset}.{category}"
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    return len(df)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_bigquery_load.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock scripts/bigquery_load.py tests/test_bigquery_load.py
git commit -m "Add BigQuery staging table load wrapper"
```

---

### Task 4: Orchestration + CLI (`load_to_bigquery.py`)

**Files:**
- Create: `scripts/load_to_bigquery.py`
- Modify: `.env.example` (add `GCP_PROJECT`, `BQ_DATASET`)
- Test: `tests/test_load_to_bigquery.py`

**Interfaces:**
- Consumes: `bigquery_categories.category_for`; `bigquery_transform.annotate`, `bigquery_transform.group_by_category`; `bigquery_load.load_category_table`; `macro_data.catalog.load_catalog(path) -> list[SeriesConfig]`; `macro_data.sources.{yahoo.YahooSource, fred.FredSource, bot.BotSource}`, each with `.fetch(cfg, start=None) -> pd.DataFrame`.
- Produces: `SOURCES: dict[str, type[BaseSource]]`; `run(catalog_path=None, client=None, project=None, dataset=None) -> dict` returning `{"fetch": {series_id: status}, "load": {category: status}}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_load_to_bigquery.py`:

```python
import pandas as pd
import pytest

from macro_data import schema
from macro_data.sources.base import BaseSource

import load_to_bigquery

CATALOG = """
series:
  - id: ok_series
    source: fake_ok
    name: "always works"
  - id: bad_series
    source: fake_bad
  - id: ok_series_2
    source: fake_ok
"""


class FakeOkSource(BaseSource):
    name = "fake_ok"

    def fetch(self, cfg, start=None):
        return schema.normalize(
            pd.DataFrame(
                [("2024-01-01", 1.0), ("2024-01-02", 2.0)], columns=["date", "value"]
            )
        )


class FakeBadSource(BaseSource):
    name = "fake_bad"

    def fetch(self, cfg, start=None):
        raise RuntimeError("api exploded")


@pytest.fixture
def env(tmp_path, monkeypatch):
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(CATALOG, encoding="utf-8")
    monkeypatch.setitem(load_to_bigquery.SOURCES, "fake_ok", FakeOkSource)
    monkeypatch.setitem(load_to_bigquery.SOURCES, "fake_bad", FakeBadSource)
    monkeypatch.setenv("GCP_PROJECT", "proj")
    monkeypatch.setenv("BQ_DATASET", "ds")
    return {"catalog_path": catalog_path}


def test_run_isolates_fetch_failures_and_loads_by_category(env, monkeypatch):
    monkeypatch.setattr(load_to_bigquery, "category_for", lambda series_id: "fx")
    calls = []

    def fake_load_category_table(client, project, dataset, category, df):
        calls.append((category, len(df)))
        return len(df)

    monkeypatch.setattr(load_to_bigquery, "load_category_table", fake_load_category_table)

    result = load_to_bigquery.run(catalog_path=env["catalog_path"], client=object())

    assert result["fetch"]["ok_series"] == "fetched (2 rows)"
    assert result["fetch"]["ok_series_2"] == "fetched (2 rows)"
    assert result["fetch"]["bad_series"].startswith("failed:")
    assert "api exploded" in result["fetch"]["bad_series"]
    assert result["load"]["fx"] == "loaded (4 rows)"
    assert calls == [("fx", 4)]


def test_run_load_failure_does_not_block_other_categories(env, monkeypatch):
    monkeypatch.setattr(
        load_to_bigquery,
        "category_for",
        lambda series_id: "fx" if series_id == "ok_series" else "commodities",
    )

    def flaky_load(client, project, dataset, category, df):
        if category == "commodities":
            raise RuntimeError("bigquery exploded")
        return len(df)

    monkeypatch.setattr(load_to_bigquery, "load_category_table", flaky_load)

    result = load_to_bigquery.run(catalog_path=env["catalog_path"], client=object())

    assert result["load"]["fx"] == "loaded (2 rows)"
    assert result["load"]["commodities"].startswith("failed:")
    assert "bigquery exploded" in result["load"]["commodities"]


def test_run_missing_gcp_project_raises(env, monkeypatch):
    monkeypatch.delenv("GCP_PROJECT")
    with pytest.raises(RuntimeError, match="GCP_PROJECT"):
        load_to_bigquery.run(catalog_path=env["catalog_path"])


def test_run_missing_bq_dataset_raises(env, monkeypatch):
    monkeypatch.delenv("BQ_DATASET")
    with pytest.raises(RuntimeError, match="BQ_DATASET"):
        load_to_bigquery.run(catalog_path=env["catalog_path"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_load_to_bigquery.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'load_to_bigquery'`

- [ ] **Step 3: Write the implementation**

Create `scripts/load_to_bigquery.py`:

```python
"""Fetch BOT/Yahoo/FRED series directly from their APIs and load them into
BigQuery staging tables, independent of macro_data's local CSV store.

Usage: python scripts/load_to_bigquery.py
Requires GCP_PROJECT and BQ_DATASET in the environment (see .env.example).
"""

import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

from macro_data.catalog import load_catalog
from macro_data.sources.bot import BotSource
from macro_data.sources.fred import FredSource
from macro_data.sources.yahoo import YahooSource

from bigquery_categories import category_for
from bigquery_load import load_category_table
from bigquery_transform import annotate, group_by_category

load_dotenv()

logger = logging.getLogger("load_to_bigquery")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "catalog.yaml"

SOURCES = {"yahoo": YahooSource, "fred": FredSource, "bot": BotSource}


def run(catalog_path=None, client=None, project=None, dataset=None) -> dict:
    project = project or os.environ.get("GCP_PROJECT")
    if not project:
        raise RuntimeError(
            "GCP_PROJECT is not set (put it in a .env file, see .env.example)"
        )
    dataset = dataset or os.environ.get("BQ_DATASET")
    if not dataset:
        raise RuntimeError(
            "BQ_DATASET is not set (put it in a .env file, see .env.example)"
        )

    configs = [c for c in load_catalog(catalog_path or CATALOG_PATH) if c.source in SOURCES]
    loaded_at = pd.Timestamp.now(tz="UTC")

    fetch_status: dict[str, str] = {}
    annotated: list[pd.DataFrame] = []
    instances = {}
    for cfg in configs:
        try:
            category = category_for(cfg.id)
            if cfg.source not in instances:
                instances[cfg.source] = SOURCES[cfg.source]()
            raw = instances[cfg.source].fetch(cfg, start=None)
            frame = annotate(cfg, category, raw, loaded_at)
            annotated.append(frame)
            fetch_status[cfg.id] = f"fetched ({len(frame)} rows)"
        except Exception as exc:  # noqa: BLE001 - one bad series must not stop the rest
            logger.warning("series %s failed: %s", cfg.id, exc)
            fetch_status[cfg.id] = f"failed: {exc}"

    by_category = group_by_category(annotated)

    if client is None:
        client = bigquery.Client(project=project)

    load_status: dict[str, str] = {}
    for category, df in by_category.items():
        try:
            rows = load_category_table(client, project, dataset, category, df)
            load_status[category] = f"loaded ({rows} rows)"
        except Exception as exc:  # noqa: BLE001 - one bad table must not stop the rest
            logger.warning("category %s failed to load: %s", category, exc)
            load_status[category] = f"failed: {exc}"

    return {"fetch": fetch_status, "load": load_status}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run()
    for series_id, status in result["fetch"].items():
        print(f"[fetch] {series_id}: {status}")
    for category, status in result["load"].items():
        print(f"[load] {category}: {status}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_load_to_bigquery.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Add BigQuery env vars to `.env.example`**

Read `.env.example`, then append:

```
# BigQuery loader (scripts/load_to_bigquery.py) -- optional, only needed to run it
GCP_PROJECT=
BQ_DATASET=
```

- [ ] **Step 6: Run the full test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass, including the pre-existing suite (no regressions).

- [ ] **Step 7: Commit**

```bash
git add scripts/load_to_bigquery.py tests/test_load_to_bigquery.py .env.example
git commit -m "Add BigQuery loader orchestration and CLI entrypoint"
```

---

### Task 5: Document the loader in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Add a new section to `CLAUDE.md`**

Read the current file, then insert a new section after the "## Keyless vs. keyed sources" section (before end of file):

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Document the BigQuery loader script in CLAUDE.md"
```

---

## Self-Review Notes

- **Spec coverage:** every spec requirement maps to a task — category mapping (Task 1), transform (Task 2), BigQuery load + config/dependency setup (Task 3), orchestration/error-isolation/CLI/env vars (Task 4), documentation (Task 5). Non-goals (World Bank, GCS landing zone, incremental merge, catalog.yaml changes) are respected: no task touches `catalog.yaml`, `store.py`, or adds a GCS dependency.
- **Type consistency:** `annotate()`'s output columns (Task 2) exactly match `bigquery_load.SCHEMA`'s field names (Task 3) once `group_by_category()` drops `category`. `load_to_bigquery.run()` (Task 4) calls `category_for`, `annotate`, `group_by_category`, `load_category_table` with the exact signatures defined in Tasks 1-3.
- **Test isolation:** Task 4's tests never construct a real `bigquery.Client` or call real APIs — `client=object()` plus monkeypatched `category_for`/`load_category_table` keep the orchestration test fully offline, consistent with Task 3's own (separately tested) BigQuery interaction.
