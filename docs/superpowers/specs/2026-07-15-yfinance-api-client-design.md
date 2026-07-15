# yfinance API Client — Design

**Date:** 2026-07-15
**Status:** Approved

## Purpose

A new standalone client, `src/yfinance_api`, wrapping the `yfinance` library
(already a dependency, already used by `macro_data/sources/yahoo.py` via
`yf.download()` and ad hoc in `notebooks/fx_ohlcv_query.ipynb`/
`notebooks/commodities.ipynb` via `yf.Ticker(...).history(...)`) into the
same namespaced-client shape as `src/bot_api`/`src/fmp_api`/`src/fred_api` —
`client.history.daily(ticker)` instead of duplicating `yf.Ticker(ticker)...`
calls across notebooks.

Unlike the other three clients, there is **no HTTP layer to wrap** —
`yfinance` already is the client library. `src/yfinance_api` is a thin
consistency facade, not a REST client, and needs no API key.

Scope is two namespaces: `history` (OHLCV bars) and `info` (quote/company
summary fields) — the two capabilities already used ad hoc in this repo's
notebooks, now centralized.

## Requirements

- `history.daily(ticker, period="3mo")` and
  `history.intraday(ticker, interval="1h", period="5d")` wrap
  `yf.Ticker(ticker).history(...)`, returning the same
  `Open/High/Low/Close/Volume` shape `fetch_ohlcv()` already produces in
  `fx_ohlcv_query.ipynb`.
- `info.quote(ticker)` wraps `yf.Ticker(ticker).info` (full dict — company
  name, sector, market cap, etc.; a slower call per yfinance's own docs).
- `info.fast_info(ticker)` wraps `yf.Ticker(ticker).fast_info` (a smaller,
  faster dict — last price, day high/low, market cap, shares outstanding).
- No API key, no construction-time failure mode to test — `YFinanceClient()`
  always succeeds and every method always attempts a real call (bad tickers
  are yfinance's own concern, e.g. an empty `DataFrame` or an empty `dict`,
  not this client's).

## Non-goals

- No `financials`/`actions`/`options`/`batch` namespaces (the "+Fundamentals"
  and "Full" tiers considered and declined) — can be added later as new
  `endpoints/<name>.py` files.
- No change to `macro_data/sources/yahoo.py` (uses `yf.download()`, a
  different yfinance entry point suited to catalog-driven single-series
  fetches) or to the existing notebooks' inline `fetch_ohlcv()` helpers —
  this client doesn't retroactively replace them, it's a new reusable
  option for future notebook work.
- No API key handling of any kind — genuinely nothing to configure.

## Architecture

### File layout

```
src/yfinance_api/
  __init__.py
  client.py
  endpoints/
    base.py
    history.py
    info.py
```

### `client.py`

```python
class YFinanceClient:
    def __init__(self):
        self.history = HistoryEndpoint(self)
        self.info = InfoEndpoint(self)
```

No `base_url`, no `timeout`, no key — `yfinance` handles its own HTTP
internals.

### `endpoints/base.py`

```python
class Endpoint:
    """Shared base for yfinance_api namespaces — kept for structural
    consistency with bot_api/fmp_api/fred_api even though there's no key
    resolution needed here."""

    def __init__(self, client: "YFinanceClient"):
        self._client = client
```

### `endpoints/history.py`

```python
class HistoryEndpoint(Endpoint):
    def daily(self, ticker: str, period: str = "3mo") -> pd.DataFrame:
        df = yf.Ticker(ticker).history(period=period, interval="1d")
        return df[["Open", "High", "Low", "Close", "Volume"]]

    def intraday(self, ticker: str, interval: str = "1h", period: str = "5d") -> pd.DataFrame:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return df[["Open", "High", "Low", "Close", "Volume"]]
```

### `endpoints/info.py`

```python
class InfoEndpoint(Endpoint):
    def quote(self, ticker: str) -> dict:
        return yf.Ticker(ticker).info

    def fast_info(self, ticker: str) -> dict:
        return dict(yf.Ticker(ticker).fast_info)
```

`fast_info` is cast to `dict` since yfinance returns a custom
`FastInfo` mapping object, not a plain `dict` — casting keeps this client's
return type consistent (`dict` from both `info` methods).

## Error handling

None added — no try/except, no key checks. A bad ticker surfaces however
`yfinance` itself handles it (an empty `DataFrame` from `history()`, a
minimal/empty dict from `.info`/`.fast_info`), same behavior notebooks
already see today calling `yf.Ticker` directly.

## Testing (`tests/test_yfinance_api.py`, new file)

Mirrors `tests/test_yahoo.py`'s approach (mock the yfinance call site) but
adapted to `Ticker`-based calls rather than the module-level `yf.download()`
that file mocks: `monkeypatch.setattr("yfinance_api.endpoints.history.yf.Ticker", fake_ticker_cls)`,
where `fake_ticker_cls` returns a stub object exposing `.history()`,
`.info`, and `.fast_info`. One test per method asserting the right
ticker/period/interval was passed through and the right columns/keys come
back; `fast_info`'s test confirms the `FastInfo`-like stub is coerced to a
plain `dict`.

## Documentation updates

- None needed — no env vars, no new docs page; `src/yfinance_api/__init__.py`
  gets a short module docstring (relationship to `macro_data/sources/yahoo.py`
  and the existing notebooks' inline helpers), mirroring the other three
  clients' `__init__.py` style.

## Out of scope

- `financials`/`actions`/`options`/`batch` namespaces (see Non-goals).
- Any change to existing `yahoo` source or notebook code.
