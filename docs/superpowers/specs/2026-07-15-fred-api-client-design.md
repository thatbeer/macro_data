# FRED API Client — Design

**Date:** 2026-07-15
**Status:** Approved

## Purpose

A new standalone client, `src/fred_api`, for FRED's REST API
(`https://api.stlouisfed.org/fred/`), extending beyond the single
`series/observations` call already in `macro_data/sources/fred.py`. Adds
series discovery — search by text, series metadata, the categories/tags a
series belongs to — so notebooks can find and pull any FRED series without
first adding a `catalog.yaml` entry. Structurally identical to `src/bot_api`
and `src/fmp_api`, kept standalone for the same reason: ad-hoc querying
across a broader surface than the catalog pipeline's single-value contract
needs.

Scope is one namespace, `series` — the "series + search" tier (not category
browsing or release/source/tags metadata, which are separate FRED API
sections left for a future namespace if needed).

## Requirements

- **Reuses the existing `FRED_API_KEY` env var** — no new key, since
  `macro_data/sources/fred.py` already authenticates against the same host
  with the same key. `FREDClient()` must not require the key at construction
  time, matching `BOTClient`/`FMPClient`.
- All 5 methods live on `client.series`: `observations`, `info`, `search`,
  `categories`, `tags`.
- FRED wraps every response in a top-level key that **differs per
  endpoint** — `to_dataframe()` needs the key name passed in per call,
  unlike FMP's uniform flat list or BOT's uniform `data_detail`.

## Non-goals

- No `category`, `release`, `source`, or `tags`-browsing namespaces (FRED's
  broader API surface) — can be added later as `endpoints/category.py` etc.
  following the same pattern, if a future need for topic-browsing arises.
- No `macro_data` catalog integration — `macro_data/sources/fred.py`'s
  `series/observations` call is untouched, separate code path, same as
  `src/bot_api`'s relationship to `macro_data/sources/bot.py`.
- No GeoFRED/regional-data support (a genuinely separate API,
  `https://api.stlouisfed.org/geofred/`, different host path convention).

## Verification status

**Update (2026-07-15, post-implementation):** all 5 methods now confirmed
live against the real API with a real `FRED_API_KEY`. Wrapper keys matched
the coded `response_key` exactly, no corrections needed:

| Method | Live top-level keys returned | Coded `response_key` |
|---|---|---|
| `observations("GNPCA")` | `realtime_start, realtime_end, observations` | `observations` ✓ |
| `info("GNPCA")` | `realtime_start, realtime_end, seriess` | `seriess` ✓ |
| `search("money stock")` | `realtime_start, realtime_end, order_by, sort_order, count, offset, limit, seriess` | `seriess` ✓ |
| `categories("GNPCA")` | `categories` | `categories` ✓ |
| `tags("GNPCA")` | `realtime_start, realtime_end, order_by, sort_order, count, offset, limit, tags` | `tags` ✓ |

`to_dataframe()` conversion also verified end-to-end (e.g. `info("GNPCA")`
yields a 1-row frame with `id`/`title`/`frequency`/`units` columns;
`categories("GNPCA")` yields `id=106, name="GDP/GNP", parent_id=18`).

Original pre-implementation note, kept for history: only
`series/observations` had been exercised against the live API in this repo
before this client existed (`macro_data/sources/fred.py`, working today
with a real key per `CLAUDE.md`). The other 4 paths/params were built from
FRED's published API docs (a long-stable, widely-used public API — e.g.
the `fredapi` PyPI package relies on the same shapes), and a live WebFetch
double-check against this host returned `403 Forbidden` for *every* URL
tried during design — FRED's WAF blocks non-browser fetch tools outright,
independent of key validity — so the smoke test above had to wait for
implementation to complete and a real key to become available, per the
plan's Step 7.

Expected shapes (per FRED docs):

| Endpoint | Wrapper key | Fields (per item) |
|---|---|---|
| `series` (info) | `"seriess"` (FRED's real, double-s key name) | `id, title, units, frequency, seasonal_adjustment, observation_start, observation_end, ...` |
| `series/observations` | `"observations"` | `date, value` (already confirmed live) |
| `series/search` | `"seriess"` (same key as info — a list of matches, not one) | same fields as `series` info |
| `series/categories` | `"categories"` | `id, name, parent_id` |
| `series/tags` | `"tags"` | `name, group_id, notes, ...` |

## Architecture

### File layout

```
src/fred_api/
  __init__.py
  client.py
  endpoints/
    base.py
    series.py
```

### `client.py`

```python
BASE_URL = "https://api.stlouisfed.org/fred/"

class FREDClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL, timeout: int = 30):
        self.api_key = api_key or os.environ.get("FRED_API_KEY")
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.series = SeriesEndpoint(self)

    def get(self, path: str, params: dict) -> dict:
        params = {**params, "api_key": self.api_key, "file_type": "json"}
        response = requests.get(self.base_url + path.lstrip("/"), params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def to_dataframe(payload: dict, key: str) -> pd.DataFrame:
        return pd.DataFrame(payload.get(key, []))
```

### `endpoints/base.py`

```python
class Endpoint:
    def __init__(self, client: "FREDClient"):
        self._client = client

    def _resolve_key(self) -> str:
        if not self._client.api_key:
            raise ValueError(
                "FRED API key not set: pass api_key= to FREDClient() or set "
                "FRED_API_KEY (see .env.example)"
            )
        return self._client.api_key

    def _request(self, path: str, params: dict, response_key: str, return_json: bool = False):
        self._resolve_key()
        payload = self._client.get(path, params)
        if return_json:
            return payload
        return self._client.to_dataframe(payload, response_key)
```

### `endpoints/series.py`

```python
class SeriesEndpoint(Endpoint):
    def observations(self, series_id: str, from_date: str | None = None, to_date: str | None = None, return_json: bool = False):
        params = {"series_id": series_id}
        if from_date: params["observation_start"] = from_date
        if to_date: params["observation_end"] = to_date
        return self._request("series/observations", params, "observations", return_json)

    def info(self, series_id: str, return_json: bool = False):
        return self._request("series", {"series_id": series_id}, "seriess", return_json)

    def search(self, search_text: str, return_json: bool = False):
        return self._request("series/search", {"search_text": search_text}, "seriess", return_json)

    def categories(self, series_id: str, return_json: bool = False):
        return self._request("series/categories", {"series_id": series_id}, "categories", return_json)

    def tags(self, series_id: str, return_json: bool = False):
        return self._request("series/tags", {"series_id": series_id}, "tags", return_json)
```

## Error handling

No try/except in the client — `raise_for_status()` surfaces HTTP errors
(400 for a bad/missing key or unknown `series_id`, per FRED's own error
body). Missing key raises `ValueError` from `_resolve_key()` before any
request is made, matching `BOTClient`/`FMPClient`.

## Testing (`tests/test_fred_api.py`, new file)

Same shape as `tests/test_bot_api.py`: `FakeResponse` / `CAPTURED` /
`monkeypatch.setattr("fred_api.client.requests.get", fake_get)`. One test per
method asserting the correct path + params (`api_key`/`file_type` always
merged in, `observation_start`/`observation_end` only when passed) and
correct extraction from each method's differing wrapper key (`observations`
vs `seriess` vs `categories` vs `tags`) — this is the one place this client
needs more test variety than `fmp_api`'s single shared shape. One test
confirms `FREDClient()` with no key succeeds at construction; each method
raises `ValueError` matching `FRED_API_KEY` when called without a key.

## Documentation updates

- No `.env.example` change — `FRED_API_KEY` is already documented there.
- `src/fred_api/__init__.py` — module docstring explaining the relationship
  to `macro_data/sources/fred.py` (shared key, separate ad-hoc surface) and
  the `"seriess"` key-name quirk, mirroring `src/bot_api/__init__.py`'s
  style.

## Out of scope

- `category`/`release`/`source`/`tags`-browsing namespaces (see Non-goals).
- GeoFRED/regional data.
- `macro_data` catalog integration.
