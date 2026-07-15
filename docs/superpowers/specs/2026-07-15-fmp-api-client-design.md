# FMP API Client — Design

**Date:** 2026-07-15
**Status:** Approved

## Purpose

A new standalone client, `src/fmp_api`, for Financial Modeling Prep's "stable"
REST API (`https://financialmodelingprep.com/stable/`). Structurally
identical to `src/bot_api` (client.py + `endpoints/base.py` +
`endpoints/<namespace>.py`), kept outside `macro_data` because FMP's
responses (quotes, OHLCV bars, indicator batches, index constituents) don't
fit the package's single-`value`-per-date canonical schema — this is for
ad-hoc, notebook-driven querying, the same rationale documented in
`src/bot_api/__init__.py`.

Scope is 7 namespaces: `economics`, `commodity`, `forex`, `indexes`, `quote`,
`chart`, `technical_indicators` — a "core macro/market + charting" subset of
FMP's ~28 categories, matching this repo's existing focus (FX, commodities,
indices, macro indicators) plus the OHLCV/candlestick work already underway
in `notebooks/fx_ohlcv_query.ipynb` and `notebooks/commodities.ipynb`.

## Requirements

- Single API key (`FMP_API_KEY`), sent as the `apikey` query param on every
  request — much simpler than BOT's 3-key split, since FMP issues one key
  per account covering every endpoint the account's plan allows.
- `FMPClient()` must not require the key at construction time — only raise
  when a namespace method is actually called (matches `BOTClient`'s pattern).
- `technical_indicators` requires a paid FMP plan (Starter/Premium/
  Ultimate/Enterprise per FMP's own docs); this repo currently has free-tier
  access only. The code ships regardless — it should fail with FMP's own
  403/402-type error surfaced via `raise_for_status()`, not be silently
  disabled or special-cased.
- `to_dataframe()` is simpler than BOT's: every endpoint tested returns a
  flat JSON list of objects (even single-item lookups like `/quote` — see
  Confirmed response shapes below), so it's unconditionally
  `pd.DataFrame(payload)`, no per-endpoint date-field or nesting logic
  needed.

## Non-goals

- No `macro_data` catalog/schema/store integration (standalone-first, per
  the `src/bot_api` precedent — a catalog source can follow later if a
  specific FMP series needs auto-tracking).
- No rate-limiting, retry/backoff, or caching layer (FMP free tier caps at
  250 requests/day; out of scope for v1).
- No coverage of FMP's other ~21 categories (statements, ESG, insiderTrades,
  crypto, senate, form13F, etc.) — can be added later as new
  `endpoints/<name>.py` files following the same pattern.

## Confirmed response shapes (live, 2026-07-15, via the FMP MCP connector already authorized in this environment, and cross-checked directly against `https://financialmodelingprep.com/stable/<path>?apikey=demo` returning `401 Unauthorized` — i.e. route recognized, only the demo key rejected — for `treasury-rates` and `commodities-list`)

| Endpoint (path = MCP `endpoint` value) | Shape |
|---|---|
| `treasury-rates` | flat list: `date, month1, month2, month3, month6, year1, year2, year3, year5, year7, year10, year20, year30` |
| `commodities-list` | flat list: `symbol, name, exchange, tradeMonth, currency` |
| `forex-list` | flat list: `symbol, fromCurrency, toCurrency, fromName, toName` |
| `sp-500` (constituents, not price) | flat list: `symbol, name, sector, subSector, headQuarter, dateFirstAdded, cik, founded` |
| `quote` | **single-item list**: `symbol, name, price, changePercentage, change, volume, dayLow, dayHigh, yearHigh, yearLow, marketCap, priceAvg50, priceAvg200, exchange, open, previousClose, timestamp` |
| `historical-price-eod-light` | flat list: `symbol, date, price, volume` (close-only — "light" omits open/high/low) |
| `simple-moving-average` (technical indicator, verified via MCP only — requires the connector's own paid access, not confirmed against a raw HTTP call) | flat list: `date` (with a time component, `"2026-07-14 00:00:00"`, unlike the plain-date other endpoints), `open, high, low, close, volume, sma` |

Every endpoint returns a **flat JSON list**, including the single-quote
lookup — confirming `to_dataframe()` needs no dict-vs-list branching.

## Architecture

### File layout

```
src/fmp_api/
  __init__.py
  client.py
  endpoints/
    base.py
    economics.py
    commodity.py
    forex.py
    indexes.py
    quote.py
    chart.py
    technical_indicators.py
```

### `client.py`

```python
BASE_URL = "https://financialmodelingprep.com/stable/"

class FMPClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL, timeout: int = 30):
        self.api_key = api_key or os.environ.get("FMP_API_KEY")
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

        self.economics = EconomicsEndpoint(self)
        self.commodity = CommodityEndpoint(self)
        self.forex = ForexEndpoint(self)
        self.indexes = IndexesEndpoint(self)
        self.quote = QuoteEndpoint(self)
        self.chart = ChartEndpoint(self)
        self.technical_indicators = TechnicalIndicatorsEndpoint(self)

    def get(self, path: str, params: dict | None = None) -> list | dict:
        params = {**(params or {}), "apikey": self.api_key}
        response = requests.get(self.base_url + path.lstrip("/"), params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def to_dataframe(payload: list | dict) -> pd.DataFrame:
        return pd.DataFrame(payload if isinstance(payload, list) else [payload])
```

Unlike BOT's `Authorization` header, FMP's key travels as a query param —
so `get()` merges it into `params` rather than building `headers`.

### `endpoints/base.py`

```python
class Endpoint:
    def __init__(self, client: "FMPClient"):
        self._client = client

    def _resolve_key(self) -> str:
        if not self._client.api_key:
            raise ValueError(
                "FMP API key not set: pass api_key= to FMPClient() or set "
                "FMP_API_KEY (see .env.example)"
            )
        return self._client.api_key

    def _request(self, path: str, params: dict, return_json: bool = False) -> pd.DataFrame | dict | list:
        self._resolve_key()  # raise before making the call, not after
        payload = self._client.get(path, params=params)
        if return_json:
            return payload
        return self._client.to_dataframe(payload)
```

Single-key model means no `key_attr` indirection like BOT's — every
namespace just calls `self._request(...)`.

### Representative endpoint file (`commodity.py`)

```python
class CommodityEndpoint(Endpoint):
    def list(self, return_json: bool = False):
        return self._request("commodities-list", {}, return_json)

    def quote(self, symbol: str, return_json: bool = False):
        return self._request("commodities-quote", {"symbol": symbol}, return_json)

    def quote_short(self, symbol: str, return_json: bool = False):
        return self._request("commodities-quote-short", {"symbol": symbol}, return_json)

    def all_quotes(self, return_json: bool = False):
        return self._request("all-commodities-quotes", {}, return_json)

    def historical_eod_full(self, symbol: str, from_date: str | None = None, to_date: str | None = None, return_json: bool = False):
        params = {"symbol": symbol}
        if from_date: params["from"] = from_date
        if to_date: params["to"] = to_date
        return self._request("commodities-historical-price-eod-full", params, return_json)

    def historical_eod_light(self, symbol: str, from_date: str | None = None, to_date: str | None = None, return_json: bool = False):
        params = {"symbol": symbol}
        if from_date: params["from"] = from_date
        if to_date: params["to"] = to_date
        return self._request("commodities-historical-price-eod-light", params, return_json)

    def intraday_1min(self, symbol: str, from_date=None, to_date=None, return_json=False):
        ...  # same param pattern, path "commodities-intraday-1-min"
    def intraday_5min(self, symbol: str, from_date=None, to_date=None, return_json=False):
        ...  # path "commodities-intraday-5-min"
    def intraday_1hour(self, symbol: str, from_date=None, to_date=None, return_json=False):
        ...  # path "commodities-intraday-1-hour"
```

`forex.py` is structurally identical (same 9 methods, `forex-*` paths).

### Remaining namespaces (method → path mapping)

- **`economics.py`**: `calendar(from_date=None, to_date=None)` → `economics-calendar`; `indicators(name, from_date=None, to_date=None)` → `economics-indicators`; `market_risk_premium()` → `market-risk-premium`; `treasury_rates(from_date=None, to_date=None)` → `treasury-rates`
- **`indexes.py`**: same 9-method shape as `commodity`/`forex` (`list→indexes-list`, `quote→index-quote`, etc.) plus `sp500()→sp-500`, `nasdaq()→nasdaq`, `dow_jones()→dow-jones`, `historical_sp500()→historical-sp-500`, `historical_nasdaq()→historical-nasdaq`, `historical_dow_jones()→historical-dow-jones`
- **`quote.py`**: `quote(symbol)`, `quote_short(symbol)`, `quote_change(symbol)`, `batch_quote(symbols: list[str])` (joins with `,`), `batch_quote_short(symbols)`, `aftermarket_quote(symbol)`, `aftermarket_trade(symbol)`, `batch_aftermarket_quote(symbols)`, `batch_aftermarket_trade(symbols)`, plus the market-wide `full_commodities_quotes()`, `full_cryptocurrency_quotes()`, `full_etf_quotes()`, `full_forex_quotes()`, `full_index_quotes()`, `full_mutualfund_quotes()`, `full_exchange_quotes(exchange)`
- **`chart.py`**: `historical_eod_full/light/dividend_adjusted/non_split_adjusted(symbol, from_date=None, to_date=None)` and `intraday_1min/5min/15min/30min/1hour/4hour(symbol, from_date=None, to_date=None)` → paths swap `historical-price-eod-*`/`intraday-*` per the MCP enum
- **`technical_indicators.py`**: `sma/ema/dema/tema/wma/rsi/adx/williams/standard_deviation(symbol, period_length, timeframe, from_date=None, to_date=None)` → paths per the MCP enum (`simple-moving-average`, `relative-strength-index`, etc.); `period_length` and `timeframe` are always required params (no defaults), matching FMP's own required-field docs surfaced via the MCP schema

## Error handling

No try/except in the client — `raise_for_status()` surfaces HTTP errors
directly: 401 for a missing/invalid key, 403 (or FMP's own paid-plan error
body) for `technical_indicators` on a free-tier key. Missing key raises
`ValueError` from `_resolve_key()`, named the same way as BOT's.

## Testing (`tests/test_fmp_api.py`, new file)

Mirrors `tests/test_bot_api.py`'s pattern: `FakeResponse` /
`CAPTURED` / `monkeypatch.setattr("fmp_api.client.requests.get", fake_get)`,
routing by URL/path substring. Per namespace: one test asserting the correct
path + params (`apikey` merged in, `from`/`to` only present when passed) and
correct DataFrame parsing (all endpoints share one `to_dataframe()`, so a
single conversion test can cover both list- and single-item-list inputs).
One test confirms `FMPClient()` with no key succeeds at construction; each
namespace method raises `ValueError` matching `FMP_API_KEY` when called
without a key. `tests/conftest.py` already puts `src/` on `sys.path` — no
`pyproject.toml` changes needed.

## Documentation updates

- `.env.example` — add `FMP_API_KEY=` with a one-line comment and a link to
  FMP's key registration page.
- `src/fmp_api/__init__.py` — module docstring listing the 7 namespaces and
  the free-tier caveat on `technical_indicators`, mirroring
  `src/bot_api/__init__.py`'s style.

## Out of scope

- `macro_data` catalog integration (see Non-goals).
- The other ~21 FMP categories.
- Rate-limiting/retry/caching.
- A notebook demonstrating this client — not requested; `src/bot_api` shipped
  without one too until `notebooks/BOT_query.ipynb` was added separately.
