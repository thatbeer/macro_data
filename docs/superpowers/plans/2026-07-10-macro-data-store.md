# Macro Data Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Python package that fetches economics data (FX, commodities, indices, macro indicators) from FRED, Yahoo Finance, World Bank, and Bank of Thailand into per-series CSV files, driven by a declarative `catalog.yaml`.

**Architecture:** Plugin-style source fetchers behind one `BaseSource` interface, all returning a canonical date-indexed DataFrame. A `store` module owns CSV persistence (incremental, atomic writes). A `pipeline` module orchestrates updates with per-series error isolation. Public API: `update_all()`, `update(source)`, `load(series_id)`, `list_series()`.

**Tech Stack:** Python ≥3.10, pandas, requests, PyYAML, python-dotenv, yfinance, pytest.

## Global Constraints

- Storage is plain CSV: `data/<source>/<series_id>.csv`, columns `date,value`, ISO dates.
- Canonical DataFrame: index `date` (naive datetime64, ascending, unique), single column `value` (float64).
- No network in tests — mock `requests.get` / `yfinance.download`.
- API keys only via env vars `FRED_API_KEY`, `BOT_CLIENT_ID` (loaded from `.env` via python-dotenv).
- One failing series must never abort other series (spec §Error handling).
- Windows environment: use `os.replace` for atomic writes; paths via `pathlib`.
- Run tests with `python -m pytest` from the project root `D:\MyOffice\AXONS\Macro_data`.

---

### Task 1: Project scaffolding + canonical schema

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `macro_data/__init__.py` (empty for now), `macro_data/sources/__init__.py` (empty), `macro_data/schema.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Produces: `schema.normalize(df: pd.DataFrame) -> pd.DataFrame` (raises `schema.SchemaError` on missing columns), `schema.empty() -> pd.DataFrame` (canonical empty frame). Canonical frame: index named `date`, one float column `value`.

- [ ] **Step 1: Write scaffolding files**

`pyproject.toml`:

```toml
[project]
name = "macro-data"
version = "0.1.0"
description = "Local macro-economics data store: FX, commodities, indices, indicators"
requires-python = ">=3.10"
dependencies = [
    "pandas>=2.0",
    "requests>=2.31",
    "PyYAML>=6.0",
    "python-dotenv>=1.0",
    "yfinance>=0.2.40",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["macro_data", "macro_data.sources"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:

```gitignore
__pycache__/
*.egg-info/
.env
data/
!data/.gitkeep
.pytest_cache/
build/
dist/
```

Create empty `macro_data/__init__.py`, `macro_data/sources/__init__.py`, and empty dir `tests/`.

- [ ] **Step 2: Install the package editable**

Run: `pip install -e .[dev]`
Expected: `Successfully installed macro-data-0.1.0` (plus deps).

- [ ] **Step 3: Write the failing schema tests**

`tests/test_schema.py`:

```python
import pandas as pd
import pytest

from macro_data import schema


def test_normalize_sorts_dedups_and_indexes():
    df = pd.DataFrame(
        {
            "date": ["2024-01-03", "2024-01-01", "2024-01-03"],
            "value": ["3.0", "1.0", "3.5"],
        }
    )
    out = schema.normalize(df)
    assert out.index.name == "date"
    assert list(out.columns) == ["value"]
    assert out.index.is_monotonic_increasing
    # duplicate date keeps the last occurrence
    assert out.loc[pd.Timestamp("2024-01-03"), "value"] == 3.5
    assert out["value"].dtype == "float64"


def test_normalize_drops_non_numeric_values():
    df = pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "value": ["1.5", "."]})
    out = schema.normalize(df)
    assert len(out) == 1


def test_normalize_strips_timezone():
    idx = pd.to_datetime(["2024-01-01", "2024-01-02"]).tz_localize("UTC")
    df = pd.DataFrame({"date": idx, "value": [1.0, 2.0]})
    out = schema.normalize(df)
    assert out.index.tz is None


def test_normalize_missing_columns_raises():
    with pytest.raises(schema.SchemaError):
        schema.normalize(pd.DataFrame({"date": ["2024-01-01"]}))


def test_empty_frame_is_canonical():
    out = schema.empty()
    assert out.index.name == "date"
    assert list(out.columns) == ["value"]
    assert len(out) == 0
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_schema.py -v`
Expected: FAIL / ERROR with `AttributeError: module 'macro_data.schema' has no attribute` or import error (schema.py not yet written).

- [ ] **Step 5: Implement `macro_data/schema.py`**

```python
"""Canonical series schema: date-indexed DataFrame with one float 'value' column."""

import pandas as pd


class SchemaError(ValueError):
    """Raised when a fetcher result cannot be coerced into the canonical schema."""


def empty() -> pd.DataFrame:
    idx = pd.DatetimeIndex([], name="date")
    return pd.DataFrame({"value": pd.Series([], dtype="float64")}, index=idx)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a raw fetcher result (columns 'date' and 'value') into the canonical frame.

    Sorts by date, drops rows with non-numeric values, keeps the last row for
    duplicate dates, and strips any timezone.
    """
    missing = {"date", "value"} - set(df.columns)
    if missing:
        raise SchemaError(f"missing required column(s): {sorted(missing)}")

    out = df[["date", "value"]].copy()
    out["date"] = pd.to_datetime(out["date"])
    if isinstance(out["date"].dtype, pd.DatetimeTZDtype):
        out["date"] = out["date"].dt.tz_localize(None)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["date", "value"])
    out = out.drop_duplicates(subset="date", keep="last").sort_values("date")
    out = out.set_index("date")
    out["value"] = out["value"].astype("float64")
    return out
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_schema.py -v`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore macro_data tests
git commit -m "feat: project scaffolding and canonical series schema"
```

---

### Task 2: CSV store

**Files:**
- Create: `macro_data/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `schema.empty()`, canonical frame shape from Task 1.
- Produces: `store.path_for(data_dir: Path, source: str, series_id: str) -> Path`; `store.load(data_dir, source, series_id) -> pd.DataFrame` (raises `FileNotFoundError`); `store.last_date(data_dir, source, series_id) -> pd.Timestamp | None`; `store.append(data_dir, source, series_id, new: pd.DataFrame) -> int` (returns number of net new rows; dedup on date keeps incoming values).

- [ ] **Step 1: Write the failing store tests**

`tests/test_store.py`:

```python
import pandas as pd
import pytest

from macro_data import schema, store


def _frame(pairs):
    df = pd.DataFrame(pairs, columns=["date", "value"])
    return schema.normalize(df)


def test_append_then_load_round_trip(tmp_path):
    new = _frame([("2024-01-01", 1.0), ("2024-01-02", 2.0)])
    added = store.append(tmp_path, "yahoo", "usd_thb", new)
    assert added == 2
    out = store.load(tmp_path, "yahoo", "usd_thb")
    pd.testing.assert_frame_equal(out, new)


def test_append_is_incremental_and_dedups(tmp_path):
    store.append(tmp_path, "yahoo", "usd_thb", _frame([("2024-01-01", 1.0), ("2024-01-02", 2.0)]))
    # overlap on 01-02 with a revised value: incoming wins
    added = store.append(
        tmp_path, "yahoo", "usd_thb", _frame([("2024-01-02", 2.5), ("2024-01-03", 3.0)])
    )
    assert added == 1  # only 01-03 is net new
    out = store.load(tmp_path, "yahoo", "usd_thb")
    assert len(out) == 3
    assert out.loc[pd.Timestamp("2024-01-02"), "value"] == 2.5


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        store.load(tmp_path, "yahoo", "nope")


def test_last_date(tmp_path):
    assert store.last_date(tmp_path, "fred", "us_cpi") is None
    store.append(tmp_path, "fred", "us_cpi", _frame([("2024-01-01", 1.0), ("2024-02-01", 2.0)]))
    assert store.last_date(tmp_path, "fred", "us_cpi") == pd.Timestamp("2024-02-01")


def test_append_empty_frame_is_noop(tmp_path):
    added = store.append(tmp_path, "fred", "us_cpi", schema.empty())
    assert added == 0
    assert store.last_date(tmp_path, "fred", "us_cpi") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError`/`ImportError` for `macro_data.store`.

- [ ] **Step 3: Implement `macro_data/store.py`**

```python
"""CSV persistence: one file per series at <data_dir>/<source>/<series_id>.csv."""

import os
from pathlib import Path

import pandas as pd

from . import schema


def path_for(data_dir: Path, source: str, series_id: str) -> Path:
    return Path(data_dir) / source / f"{series_id}.csv"


def load(data_dir: Path, source: str, series_id: str) -> pd.DataFrame:
    path = path_for(data_dir, source, series_id)
    if not path.exists():
        raise FileNotFoundError(f"no data for series '{series_id}' at {path}")
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    df["value"] = df["value"].astype("float64")
    return df


def last_date(data_dir: Path, source: str, series_id: str):
    try:
        df = load(data_dir, source, series_id)
    except FileNotFoundError:
        return None
    return None if df.empty else df.index.max()


def append(data_dir: Path, source: str, series_id: str, new: pd.DataFrame) -> int:
    """Merge new rows into the series file. Incoming values win on duplicate dates.

    Returns the number of net new rows (dates not previously stored).
    """
    if new.empty:
        return 0
    try:
        existing = load(data_dir, source, series_id)
    except FileNotFoundError:
        existing = schema.empty()

    combined = pd.concat([existing, new])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()

    path = path_for(data_dir, source, series_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    combined.to_csv(tmp, date_format="%Y-%m-%d")
    os.replace(tmp, path)  # atomic on the same filesystem, including Windows
    return len(combined) - len(existing)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_store.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add macro_data/store.py tests/test_store.py
git commit -m "feat: CSV store with incremental append and atomic writes"
```

---

### Task 3: Catalog

**Files:**
- Create: `macro_data/catalog.py`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Produces: `catalog.SeriesConfig` frozen dataclass with fields `id: str`, `source: str`, `name: str = ""`, `params: dict`; `catalog.load_catalog(path: Path) -> list[SeriesConfig]` (raises `catalog.CatalogError` on missing keys or duplicate ids).

- [ ] **Step 1: Write the failing catalog tests**

`tests/test_catalog.py`:

```python
import pytest

from macro_data import catalog


def _write(tmp_path, text):
    p = tmp_path / "catalog.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_catalog_parses_entries_and_params(tmp_path):
    p = _write(
        tmp_path,
        """
series:
  - id: usd_thb
    source: yahoo
    ticker: "THB=X"
    name: "USD/THB exchange rate"
  - id: us_cpi
    source: fred
    series: CPIAUCSL
""",
    )
    entries = catalog.load_catalog(p)
    assert [e.id for e in entries] == ["usd_thb", "us_cpi"]
    assert entries[0].source == "yahoo"
    assert entries[0].name == "USD/THB exchange rate"
    assert entries[0].params == {"ticker": "THB=X"}
    assert entries[1].params == {"series": "CPIAUCSL"}
    assert entries[1].name == ""


def test_missing_required_key_raises(tmp_path):
    p = _write(tmp_path, "series:\n  - id: oops\n")
    with pytest.raises(catalog.CatalogError, match="source"):
        catalog.load_catalog(p)


def test_duplicate_id_raises(tmp_path):
    p = _write(
        tmp_path,
        """
series:
  - {id: dup, source: yahoo, ticker: A}
  - {id: dup, source: fred, series: B}
""",
    )
    with pytest.raises(catalog.CatalogError, match="dup"):
        catalog.load_catalog(p)


def test_empty_or_malformed_catalog_raises(tmp_path):
    p = _write(tmp_path, "not_series: []\n")
    with pytest.raises(catalog.CatalogError):
        catalog.load_catalog(p)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_catalog.py -v`
Expected: FAIL with import error for `macro_data.catalog`.

- [ ] **Step 3: Implement `macro_data/catalog.py`**

```python
"""Declarative series catalog loaded from catalog.yaml."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class CatalogError(ValueError):
    """Raised when catalog.yaml is malformed."""


_KNOWN_KEYS = {"id", "source", "name"}


@dataclass(frozen=True)
class SeriesConfig:
    id: str
    source: str
    name: str = ""
    params: dict = field(default_factory=dict)


def load_catalog(path: Path) -> list[SeriesConfig]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("series"), list):
        raise CatalogError(f"{path}: expected a top-level 'series' list")

    entries: list[SeriesConfig] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw["series"]):
        if not isinstance(entry, dict):
            raise CatalogError(f"{path}: series[{i}] is not a mapping")
        for key in ("id", "source"):
            if key not in entry:
                raise CatalogError(f"{path}: series[{i}] missing required key '{key}'")
        if entry["id"] in seen:
            raise CatalogError(f"{path}: duplicate series id '{entry['id']}'")
        seen.add(entry["id"])
        params = {k: v for k, v in entry.items() if k not in _KNOWN_KEYS}
        entries.append(
            SeriesConfig(
                id=entry["id"],
                source=entry["source"],
                name=entry.get("name", ""),
                params=params,
            )
        )
    return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_catalog.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add macro_data/catalog.py tests/test_catalog.py
git commit -m "feat: declarative series catalog"
```

---

### Task 4: Source base class + Yahoo Finance fetcher

**Files:**
- Create: `macro_data/sources/base.py`, `macro_data/sources/yahoo.py`
- Test: `tests/test_yahoo.py`

**Interfaces:**
- Consumes: `SeriesConfig` (Task 3), `schema.normalize`/`schema.empty` (Task 1).
- Produces: `base.BaseSource` ABC with class attr `name: str` and abstract method `fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame`; `base.MissingKeyError(RuntimeError)` with constructor arg = env var name; `yahoo.YahooSource` (name `"yahoo"`, requires `cfg.params["ticker"]`).

- [ ] **Step 1: Write `macro_data/sources/base.py`** (interface only, no test of its own)

```python
"""Source interface: every fetcher returns the canonical schema."""

from abc import ABC, abstractmethod

import pandas as pd

from ..catalog import SeriesConfig


class MissingKeyError(RuntimeError):
    """An API key env var required by a source is not set."""

    def __init__(self, env_var: str):
        super().__init__(
            f"environment variable {env_var} is not set "
            f"(put it in a .env file, see .env.example)"
        )
        self.env_var = env_var


class BaseSource(ABC):
    name: str = ""

    @abstractmethod
    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        """Return canonical rows for cfg with date >= start (full history if start is None)."""
```

- [ ] **Step 2: Write the failing Yahoo tests**

`tests/test_yahoo.py`:

```python
import pandas as pd

from macro_data.catalog import SeriesConfig
from macro_data.sources.yahoo import YahooSource

CFG = SeriesConfig(id="usd_thb", source="yahoo", params={"ticker": "THB=X"})


def _fake_download(rows):
    """Build a yfinance-shaped result: DatetimeIndex + MultiIndex columns."""
    idx = pd.to_datetime([d for d, _ in rows])
    cols = pd.MultiIndex.from_tuples([("Close", "THB=X")])
    return pd.DataFrame([[v] for _, v in rows], index=idx, columns=cols)


def test_fetch_full_history(monkeypatch):
    captured = {}

    def fake(ticker, **kwargs):
        captured.update(kwargs, ticker=ticker)
        return _fake_download([("2024-01-01", 34.5), ("2024-01-02", 34.6)])

    monkeypatch.setattr("macro_data.sources.yahoo.yf.download", fake)
    out = YahooSource().fetch(CFG)
    assert captured["ticker"] == "THB=X"
    assert captured["period"] == "max"
    assert list(out["value"]) == [34.5, 34.6]
    assert out.index.name == "date"


def test_fetch_incremental_passes_start(monkeypatch):
    captured = {}

    def fake(ticker, **kwargs):
        captured.update(kwargs)
        return _fake_download([("2024-01-03", 34.7)])

    monkeypatch.setattr("macro_data.sources.yahoo.yf.download", fake)
    out = YahooSource().fetch(CFG, start=pd.Timestamp("2024-01-03"))
    assert captured["start"] == "2024-01-03"
    assert len(out) == 1


def test_fetch_empty_result(monkeypatch):
    monkeypatch.setattr(
        "macro_data.sources.yahoo.yf.download", lambda *a, **k: pd.DataFrame()
    )
    out = YahooSource().fetch(CFG)
    assert out.empty
    assert out.index.name == "date"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_yahoo.py -v`
Expected: FAIL with import error for `macro_data.sources.yahoo`.

- [ ] **Step 4: Implement `macro_data/sources/yahoo.py`**

```python
"""Yahoo Finance fetcher (FX, commodities futures, market indices). No API key."""

import pandas as pd
import yfinance as yf

from .. import schema
from ..catalog import SeriesConfig
from .base import BaseSource


class YahooSource(BaseSource):
    name = "yahoo"

    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        ticker = cfg.params["ticker"]
        kwargs = {"progress": False, "auto_adjust": True}
        if start is not None:
            kwargs["start"] = start.strftime("%Y-%m-%d")
        else:
            kwargs["period"] = "max"
        raw = yf.download(ticker, **kwargs)
        if raw is None or raw.empty:
            return schema.empty()
        close = raw["Close"]
        if isinstance(close, pd.DataFrame):  # yfinance returns MultiIndex columns
            close = close.iloc[:, 0]
        df = pd.DataFrame({"date": close.index, "value": close.to_numpy()})
        return schema.normalize(df)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_yahoo.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add macro_data/sources tests/test_yahoo.py
git commit -m "feat: source base class and Yahoo Finance fetcher"
```

---

### Task 5: FRED fetcher

**Files:**
- Create: `macro_data/sources/fred.py`
- Test: `tests/test_fred.py`

**Interfaces:**
- Consumes: `BaseSource`, `MissingKeyError` (Task 4), `schema` (Task 1).
- Produces: `fred.FredSource` (name `"fred"`, requires `cfg.params["series"]` and env `FRED_API_KEY`).

- [ ] **Step 1: Write the failing FRED tests**

`tests/test_fred.py`:

```python
import pandas as pd
import pytest

from macro_data.catalog import SeriesConfig
from macro_data.sources.base import MissingKeyError
from macro_data.sources.fred import FredSource

CFG = SeriesConfig(id="us_cpi", source="fred", params={"series": "CPIAUCSL"})


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_parses_observations(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(
            {
                "observations": [
                    {"date": "2024-01-01", "value": "308.417"},
                    {"date": "2024-02-01", "value": "."},  # FRED missing marker
                    {"date": "2024-03-01", "value": "312.332"},
                ]
            }
        )

    monkeypatch.setattr("macro_data.sources.fred.requests.get", fake_get)
    out = FredSource().fetch(CFG)
    assert captured["params"]["series_id"] == "CPIAUCSL"
    assert captured["params"]["api_key"] == "test-key"
    assert "observation_start" not in captured["params"]
    assert len(out) == 2  # "." row dropped
    assert out.loc[pd.Timestamp("2024-03-01"), "value"] == 312.332


def test_fetch_incremental_sets_observation_start(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return FakeResponse({"observations": []})

    monkeypatch.setattr("macro_data.sources.fred.requests.get", fake_get)
    out = FredSource().fetch(CFG, start=pd.Timestamp("2024-04-01"))
    assert captured["params"]["observation_start"] == "2024-04-01"
    assert out.empty


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(MissingKeyError, match="FRED_API_KEY"):
        FredSource().fetch(CFG)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fred.py -v`
Expected: FAIL with import error for `macro_data.sources.fred`.

- [ ] **Step 3: Implement `macro_data/sources/fred.py`**

```python
"""FRED (US Federal Reserve) fetcher. Needs free API key: https://fred.stlouisfed.org/docs/api/api_key.html"""

import os

import pandas as pd
import requests

from .. import schema
from ..catalog import SeriesConfig
from .base import BaseSource, MissingKeyError

OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


class FredSource(BaseSource):
    name = "fred"

    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            raise MissingKeyError("FRED_API_KEY")
        params = {
            "series_id": cfg.params["series"],
            "api_key": api_key,
            "file_type": "json",
        }
        if start is not None:
            params["observation_start"] = start.strftime("%Y-%m-%d")
        resp = requests.get(OBSERVATIONS_URL, params=params, timeout=30)
        resp.raise_for_status()
        observations = resp.json().get("observations", [])
        if not observations:
            return schema.empty()
        df = pd.DataFrame(observations)
        return schema.normalize(df)  # coerces "." missing markers to NaN and drops them
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fred.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add macro_data/sources/fred.py tests/test_fred.py
git commit -m "feat: FRED fetcher"
```

---

### Task 6: World Bank fetcher

**Files:**
- Create: `macro_data/sources/worldbank.py`
- Test: `tests/test_worldbank.py`

**Interfaces:**
- Consumes: `BaseSource` (Task 4), `schema` (Task 1).
- Produces: `worldbank.WorldBankSource` (name `"worldbank"`, requires `cfg.params["indicator"]` and `cfg.params["country"]`, no API key).

- [ ] **Step 1: Write the failing World Bank tests**

`tests/test_worldbank.py`:

```python
import pandas as pd

from macro_data.catalog import SeriesConfig
from macro_data.sources.worldbank import WorldBankSource

CFG = SeriesConfig(
    id="th_gdp_usd",
    source="worldbank",
    params={"indicator": "NY.GDP.MKTP.CD", "country": "THA"},
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _payload():
    meta = {"page": 1, "pages": 1, "total": 3}
    rows = [
        {"date": "2023", "value": 514969611656.0},
        {"date": "2022", "value": 495645559519.0},
        {"date": "2021", "value": None},  # not yet reported
    ]
    return [meta, rows]


def test_fetch_parses_yearly_rows(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(_payload())

    monkeypatch.setattr("macro_data.sources.worldbank.requests.get", fake_get)
    out = WorldBankSource().fetch(CFG)
    assert "THA" in captured["url"] and "NY.GDP.MKTP.CD" in captured["url"]
    assert captured["params"]["format"] == "json"
    assert len(out) == 2  # None value dropped
    assert out.index[0] == pd.Timestamp("2022-01-01")  # years parse to Jan 1, sorted


def test_fetch_incremental_filters_client_side(monkeypatch):
    monkeypatch.setattr(
        "macro_data.sources.worldbank.requests.get",
        lambda url, params=None, timeout=None: FakeResponse(_payload()),
    )
    out = WorldBankSource().fetch(CFG, start=pd.Timestamp("2023-01-01"))
    assert list(out.index) == [pd.Timestamp("2023-01-01")]


def test_fetch_no_data(monkeypatch):
    monkeypatch.setattr(
        "macro_data.sources.worldbank.requests.get",
        lambda url, params=None, timeout=None: FakeResponse([{"total": 0}]),
    )
    out = WorldBankSource().fetch(CFG)
    assert out.empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_worldbank.py -v`
Expected: FAIL with import error for `macro_data.sources.worldbank`.

- [ ] **Step 3: Implement `macro_data/sources/worldbank.py`**

```python
"""World Bank open data fetcher (country-level macro indicators). No API key."""

import pandas as pd
import requests

from .. import schema
from ..catalog import SeriesConfig
from .base import BaseSource

BASE_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"


class WorldBankSource(BaseSource):
    name = "worldbank"

    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        url = BASE_URL.format(country=cfg.params["country"], indicator=cfg.params["indicator"])
        params = {"format": "json", "per_page": 20000}
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload[1] if len(payload) > 1 and payload[1] else []
        if not rows:
            return schema.empty()
        df = pd.DataFrame(rows)[["date", "value"]]
        out = schema.normalize(df)  # year strings like "2023" parse to Jan 1
        if start is not None:
            out = out[out.index >= start]  # API has no >= filter; trim client-side
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_worldbank.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add macro_data/sources/worldbank.py tests/test_worldbank.py
git commit -m "feat: World Bank fetcher"
```

---

### Task 7: Bank of Thailand fetcher

**Files:**
- Create: `macro_data/sources/bot.py`
- Test: `tests/test_bot.py`

**Interfaces:**
- Consumes: `BaseSource`, `MissingKeyError` (Task 4), `schema` (Task 1).
- Produces: `bot.BotSource` (name `"bot"`). Catalog params: `url` (full BOT API endpoint), `value_field` (which field holds the value), optional `date_field` (default `"period"`), optional `query` (dict of extra query params, e.g. `{currency: USD}`). Needs env `BOT_CLIENT_ID` sent as `X-IBM-Client-Id` header. BOT endpoints require `start_period`/`end_period`; default start is `2000-01-01`, end is today.

- [ ] **Step 1: Write the failing BOT tests**

`tests/test_bot.py`:

```python
import pandas as pd
import pytest

from macro_data.catalog import SeriesConfig
from macro_data.sources.base import MissingKeyError
from macro_data.sources.bot import BotSource

CFG = SeriesConfig(
    id="usd_thb_bot",
    source="bot",
    params={
        "url": "https://apigw1.bot.or.th/bot/public/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/",
        "value_field": "mid_rate",
        "query": {"currency": "USD"},
    },
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {"period": "2024-01-02", "currency_id": "USD", "mid_rate": "34.5"},
                    {"period": "2024-01-03", "currency_id": "USD", "mid_rate": "34.6"},
                ]
            },
        }
    }


def test_fetch_parses_data_detail(monkeypatch):
    monkeypatch.setenv("BOT_CLIENT_ID", "client-123")
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured.update(url=url, params=params, headers=headers)
        return FakeResponse(_payload())

    monkeypatch.setattr("macro_data.sources.bot.requests.get", fake_get)
    out = BotSource().fetch(CFG, start=pd.Timestamp("2024-01-01"))
    assert captured["url"] == CFG.params["url"]
    assert captured["headers"] == {"X-IBM-Client-Id": "client-123"}
    assert captured["params"]["currency"] == "USD"
    assert captured["params"]["start_period"] == "2024-01-01"
    assert "end_period" in captured["params"]
    assert list(out["value"]) == [34.5, 34.6]


def test_fetch_default_start(monkeypatch):
    monkeypatch.setenv("BOT_CLIENT_ID", "client-123")
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["params"] = params
        return FakeResponse(_payload())

    monkeypatch.setattr("macro_data.sources.bot.requests.get", fake_get)
    BotSource().fetch(CFG)
    assert captured["params"]["start_period"] == "2000-01-01"


def test_fetch_empty_detail(monkeypatch):
    monkeypatch.setenv("BOT_CLIENT_ID", "client-123")
    monkeypatch.setattr(
        "macro_data.sources.bot.requests.get",
        lambda url, params=None, headers=None, timeout=None: FakeResponse(
            {"result": {"success": True, "data": {"data_detail": []}}}
        ),
    )
    out = BotSource().fetch(CFG)
    assert out.empty


def test_missing_client_id_raises(monkeypatch):
    monkeypatch.delenv("BOT_CLIENT_ID", raising=False)
    with pytest.raises(MissingKeyError, match="BOT_CLIENT_ID"):
        BotSource().fetch(CFG)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bot.py -v`
Expected: FAIL with import error for `macro_data.sources.bot`.

- [ ] **Step 3: Implement `macro_data/sources/bot.py`**

```python
"""Bank of Thailand API fetcher. Needs free client id: https://apiportal.bot.or.th"""

import os

import pandas as pd
import requests

from .. import schema
from ..catalog import SeriesConfig
from .base import BaseSource, MissingKeyError

DEFAULT_START = "2000-01-01"


class BotSource(BaseSource):
    name = "bot"

    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        client_id = os.environ.get("BOT_CLIENT_ID")
        if not client_id:
            raise MissingKeyError("BOT_CLIENT_ID")

        params = dict(cfg.params.get("query", {}))
        params["start_period"] = (
            start.strftime("%Y-%m-%d") if start is not None else DEFAULT_START
        )
        params["end_period"] = pd.Timestamp.today().strftime("%Y-%m-%d")

        resp = requests.get(
            cfg.params["url"],
            params=params,
            headers={"X-IBM-Client-Id": client_id},
            timeout=30,
        )
        resp.raise_for_status()
        detail = (
            resp.json().get("result", {}).get("data", {}).get("data_detail", []) or []
        )
        if not detail:
            return schema.empty()
        date_field = cfg.params.get("date_field", "period")
        value_field = cfg.params["value_field"]
        df = pd.DataFrame(detail).rename(
            columns={date_field: "date", value_field: "value"}
        )
        return schema.normalize(df)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bot.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add macro_data/sources/bot.py tests/test_bot.py
git commit -m "feat: Bank of Thailand fetcher"
```

---

### Task 8: Pipeline + public API

**Files:**
- Create: `macro_data/pipeline.py`
- Modify: `macro_data/__init__.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything above.
- Produces (public API, re-exported in `macro_data/__init__.py`):
  - `update_all(catalog_path=None, data_dir=None) -> dict[str, str]`
  - `update(source_name: str, catalog_path=None, data_dir=None) -> dict[str, str]`
  - `load(series_id: str, catalog_path=None, data_dir=None) -> pd.DataFrame`
  - `list_series(catalog_path=None) -> list[SeriesConfig]`
  - Status strings: `"updated (N rows)"`, `"up-to-date"`, `"failed: <error>"`.
  - Defaults: `PROJECT_ROOT = Path(__file__).resolve().parent.parent`, `CATALOG_PATH = PROJECT_ROOT / "catalog.yaml"`, `DATA_DIR = PROJECT_ROOT / "data"`. `load_dotenv()` is called at pipeline import.

- [ ] **Step 1: Write the failing pipeline tests**

`tests/test_pipeline.py`:

```python
import pandas as pd
import pytest

from macro_data import pipeline, schema, store
from macro_data.catalog import SeriesConfig
from macro_data.sources.base import BaseSource

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
        rows = [("2024-01-01", 1.0), ("2024-01-02", 2.0)]
        if start is not None:
            rows = [(d, v) for d, v in rows if pd.Timestamp(d) >= start]
        return schema.normalize(pd.DataFrame(rows, columns=["date", "value"]))


class FakeBadSource(BaseSource):
    name = "fake_bad"

    def fetch(self, cfg, start=None):
        raise RuntimeError("api exploded")


@pytest.fixture
def env(tmp_path, monkeypatch):
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(CATALOG, encoding="utf-8")
    monkeypatch.setitem(pipeline.SOURCES, "fake_ok", FakeOkSource)
    monkeypatch.setitem(pipeline.SOURCES, "fake_bad", FakeBadSource)
    return {"catalog_path": catalog_path, "data_dir": tmp_path / "data"}


def test_update_all_isolates_failures(env):
    result = pipeline.update_all(**env)
    assert result["ok_series"] == "updated (2 rows)"
    assert result["ok_series_2"] == "updated (2 rows)"
    assert result["bad_series"].startswith("failed:")
    assert "api exploded" in result["bad_series"]
    # the good series really got written despite the bad one
    assert len(store.load(env["data_dir"], "fake_ok", "ok_series")) == 2


def test_update_all_is_incremental(env):
    pipeline.update_all(**env)
    result = pipeline.update_all(**env)  # second run: nothing new
    assert result["ok_series"] == "up-to-date"


def test_update_single_source(env):
    result = pipeline.update("fake_ok", **env)
    assert set(result) == {"ok_series", "ok_series_2"}


def test_update_unknown_source_in_catalog(env):
    (env["catalog_path"]).write_text(
        "series:\n  - {id: x, source: no_such_source}\n", encoding="utf-8"
    )
    result = pipeline.update_all(**env)
    assert result["x"].startswith("failed:")


def test_load_by_series_id(env):
    pipeline.update_all(**env)
    df = pipeline.load("ok_series", **env)
    assert list(df["value"]) == [1.0, 2.0]


def test_load_unknown_series_raises(env):
    with pytest.raises(KeyError, match="nope"):
        pipeline.load("nope", **env)


def test_public_api_exports():
    import macro_data

    for fn in ("update_all", "update", "load", "list_series"):
        assert callable(getattr(macro_data, fn))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL with import error for `macro_data.pipeline`.

- [ ] **Step 3: Implement `macro_data/pipeline.py`**

```python
"""Update orchestration: catalog -> fetchers -> store, with per-series error isolation."""

import logging
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from . import store
from .catalog import SeriesConfig, load_catalog
from .sources.bot import BotSource
from .sources.fred import FredSource
from .sources.worldbank import WorldBankSource
from .sources.yahoo import YahooSource

load_dotenv()

logger = logging.getLogger("macro_data")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "catalog.yaml"
DATA_DIR = PROJECT_ROOT / "data"

SOURCES = {
    cls.name: cls for cls in (YahooSource, FredSource, WorldBankSource, BotSource)
}


def list_series(catalog_path=None) -> list[SeriesConfig]:
    return load_catalog(catalog_path or CATALOG_PATH)


def load(series_id: str, catalog_path=None, data_dir=None) -> pd.DataFrame:
    for cfg in list_series(catalog_path):
        if cfg.id == series_id:
            return store.load(data_dir or DATA_DIR, cfg.source, series_id)
    raise KeyError(f"series '{series_id}' not found in catalog")


def update_all(catalog_path=None, data_dir=None) -> dict[str, str]:
    return _run(list_series(catalog_path), data_dir or DATA_DIR)


def update(source_name: str, catalog_path=None, data_dir=None) -> dict[str, str]:
    selected = [c for c in list_series(catalog_path) if c.source == source_name]
    return _run(selected, data_dir or DATA_DIR)


def _run(configs: list[SeriesConfig], data_dir: Path) -> dict[str, str]:
    results: dict[str, str] = {}
    instances = {}
    for cfg in configs:
        try:
            if cfg.source not in SOURCES:
                raise KeyError(f"unknown source '{cfg.source}'")
            if cfg.source not in instances:
                instances[cfg.source] = SOURCES[cfg.source]()
            results[cfg.id] = _update_series(instances[cfg.source], cfg, data_dir)
        except Exception as exc:  # noqa: BLE001 - one bad series must not stop the rest
            logger.warning("series %s failed: %s", cfg.id, exc)
            results[cfg.id] = f"failed: {exc}"
    return results


def _update_series(source, cfg: SeriesConfig, data_dir: Path) -> str:
    last = store.last_date(data_dir, cfg.source, cfg.id)
    start = None if last is None else last + pd.Timedelta(days=1)
    new = source.fetch(cfg, start=start)
    added = store.append(data_dir, cfg.source, cfg.id, new)
    return f"updated ({added} rows)" if added else "up-to-date"
```

- [ ] **Step 4: Replace `macro_data/__init__.py` with the public API**

```python
"""Macro data store: fetch economics data into local CSVs, load into pandas.

Usage:
    from macro_data import update_all, load
    update_all()
    df = load("usd_thb")
"""

from .pipeline import list_series, load, update, update_all

__all__ = ["update_all", "update", "load", "list_series"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: 7 passed.

- [ ] **Step 6: Run the whole suite**

Run: `python -m pytest -v`
Expected: all tests pass (schema 5, store 5, catalog 4, yahoo 3, fred 3, worldbank 3, bot 4, pipeline 7 = 34).

- [ ] **Step 7: Commit**

```bash
git add macro_data/pipeline.py macro_data/__init__.py tests/test_pipeline.py
git commit -m "feat: update pipeline and public API"
```

---

### Task 9: Starter catalog, env template, README, live smoke test

**Files:**
- Create: `catalog.yaml`, `.env.example`, `README.md`, `data/.gitkeep`

**Interfaces:**
- Consumes: the whole public API.

- [ ] **Step 1: Write `catalog.yaml`** (keyless sources have real starter series; keyed sources included but will report `failed: ... env var not set` until keys are added — that is expected behavior, not an error)

```yaml
# Series catalog: add an entry here to start collecting a new series.
# Keys other than id/source/name are passed to the source fetcher.
series:
  # --- Yahoo Finance (no key) ---
  - id: usd_thb
    source: yahoo
    ticker: "THB=X"
    name: "USD/THB exchange rate"
  - id: eur_usd
    source: yahoo
    ticker: "EURUSD=X"
    name: "EUR/USD exchange rate"
  - id: gold_usd
    source: yahoo
    ticker: "GC=F"
    name: "Gold futures (USD/oz)"
  - id: brent_oil
    source: yahoo
    ticker: "BZ=F"
    name: "Brent crude futures (USD/bbl)"
  - id: sp500
    source: yahoo
    ticker: "^GSPC"
    name: "S&P 500 index"
  - id: set_index
    source: yahoo
    ticker: "^SET.BK"
    name: "SET index (Thailand)"

  # --- World Bank (no key) ---
  - id: th_gdp_usd
    source: worldbank
    indicator: NY.GDP.MKTP.CD
    country: THA
    name: "Thailand GDP (current US$)"
  - id: th_inflation
    source: worldbank
    indicator: FP.CPI.TOTL.ZG
    country: THA
    name: "Thailand inflation, CPI (annual %)"

  # --- FRED (needs FRED_API_KEY) ---
  - id: us_cpi
    source: fred
    series: CPIAUCSL
    name: "US CPI (all urban consumers)"
  - id: fed_funds_rate
    source: fred
    series: FEDFUNDS
    name: "US federal funds effective rate"

  # --- Bank of Thailand (needs BOT_CLIENT_ID) ---
  - id: usd_thb_bot
    source: bot
    url: "https://apigw1.bot.or.th/bot/public/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/"
    value_field: mid_rate
    query:
      currency: USD
    name: "USD/THB daily average reference rate (BOT)"
```

- [ ] **Step 2: Write `.env.example`**

```bash
# Copy to .env and fill in. Sources without a key here (yahoo, worldbank) work out of the box.
# FRED: register free at https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY=
# Bank of Thailand: register free at https://apiportal.bot.or.th
BOT_CLIENT_ID=
```

- [ ] **Step 3: Write `README.md`**

````markdown
# Macro Data Store

Collects economics data (FX rates, commodities, indices, macro indicators)
from FRED, Yahoo Finance, World Bank, and Bank of Thailand into plain CSV
files under `data/`, one file per series.

## Setup

```bash
pip install -e .[dev]
copy .env.example .env   # then fill in FRED_API_KEY / BOT_CLIENT_ID (optional)
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
````

- [ ] **Step 4: Create `data/.gitkeep`** (empty file) so the data dir exists in git while its CSVs stay ignored.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -v`
Expected: all 34 tests pass.

- [ ] **Step 6: Live smoke test (network) for the keyless sources**

Run: `python -c "from macro_data import update; print(update('yahoo')); print(update('worldbank'))"`
Expected: dict of `updated (N rows)` statuses and CSVs under `data/yahoo/` and `data/worldbank/`. If a network/source hiccup makes one series fail, its status says `failed: ...` while others still update — note it, don't block the task.

Then: `python -c "from macro_data import load; print(load('usd_thb').tail())"`
Expected: last 5 rows of USD/THB with real dates and rates.

- [ ] **Step 7: Commit**

```bash
git add catalog.yaml .env.example README.md data/.gitkeep
git commit -m "feat: starter catalog, env template, and README"
```
