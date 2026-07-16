# Commodities (Trading Economics Categories) Query Notebook — Design

## Purpose

A new notebook, `notebooks/commodities_te_query.ipynb`, surveys commodity prices
organized under Trading Economics' own category taxonomy (Energy, Metals,
Agricultural, Industrial, Livestock, Index, Electricity) as supplied by the user. The
full taxonomy names 103 individual commodities; this notebook fetches real data for
whichever of those have a free, identity-verified Yahoo Finance ticker, and documents
the rest as unavailable with a reason, rather than silently omitting them or
fabricating data for series with no free source.

This is deliberately a coverage survey, not a claim of Trading Economics API parity —
this project holds no Trading Economics (or Platts/Argus/Fastmarkets/LME) credentials,
and most of the taxonomy's granular items (rare earths, regional gas hubs, national
electricity prices, freight indices) are only available through those paid feeds.

## Why standalone, not `catalog.yaml`

Every other commodity notebook in this repo (`commodity_prices_query.ipynb`,
`oil_prices_query.ipynb`) adds its series to `catalog.yaml` and fetches through
`macro_data.update()`/`load()`, so the series are tracked long-term in `data/yahoo/`.
This notebook instead queries `yfinance` directly, following the
`fx_ohlcv_query.ipynb` pattern of a standalone query notebook: the ~32 available
series here are a one-off taxonomy survey, not a curated set the project has decided
to track indefinitely. `catalog.yaml` is left untouched.

## Verified data mapping

Every ticker below was checked live against `yfinance` — both for data availability
and instrument identity (`Ticker.info` short/long name), since a plausible-looking
ticker guess can silently collide with an unrelated real instrument (e.g. `ZN=F` is
the CBOT 10-Year T-Note future, not Zinc — excluded for exactly this reason).

### Energy (5 of 17 available)

| Item | Ticker | Unit |
|---|---|---|
| Crude Oil (WTI) | `CL=F` | USD/bbl |
| Brent | `BZ=F` | USD/bbl |
| Natural Gas | `NG=F` | USD/MMBtu |
| Gasoline | `RB=F` | USD/gal (RBOB) |
| Heating Oil | `HO=F` | USD/gal |

Unavailable: Coal, TTF Gas, UK Gas, Ethanol, Naphtha, Propane, Uranium, Methanol,
Coking Coal, LNG JKM, German Gas, Urals Oil — regional hubs / OTC benchmarks with no
free Yahoo ticker.

### Metals (7 of 13 available)

| Item | Ticker | Unit |
|---|---|---|
| Gold | `GC=F` | USD/oz |
| Silver | `SI=F` | USD/oz |
| Copper | `HG=F` | USD/lb |
| Platinum | `PL=F` | USD/oz |
| Lithium | `LTH=F` | Lithium Hydroxide CIF CJK (Fastmarkets) |
| HRC Steel | `HRC=F` | USD/short ton (US Midwest HRC) |
| Iron Ore | `TIO=F` | USD/dry metric ton (62% Fe CFR China) |

Unavailable: Steel (generic — HRC Steel above is the only steel benchmark Yahoo
carries), Iron Ore CNY (Dalian Commodity Exchange RMB-denominated contract), Cobalt
Hydroxide, Silicon, Scrap Steel, Titanium.

### Agricultural (14 of 23 available)

| Item | Ticker | Unit |
|---|---|---|
| Soybeans | `ZS=F` | cents/bu |
| Wheat | `ZW=F` | cents/bu |
| Corn | `ZC=F` | cents/bu |
| Lumber | `LBR=F` | USD/1,000 board ft |
| Cheese | `CSC=F` | cents/lb |
| Milk | `DC=F` | USD/cwt (Class III) |
| Orange Juice | `OJ=F` | cents/lb |
| Coffee | `KC=F` | cents/lb |
| Cotton | `CT=F` | cents/lb |
| Rice | `ZR=F` | USD/cwt (Rough Rice) |
| Oat | `ZO=F` | cents/bu |
| Sugar | `SB=F` | cents/lb (#11) |
| Cocoa | `CC=F` | USD/metric ton |
| Butter | `CB=F` | cents/lb |

Unavailable: Palm Oil, Rubber, Canola, Wool, Tea, Sunflower Oil, Rapeseed, Barley,
Potatoes — mostly Bursa Malaysia / regional exchanges Yahoo doesn't mirror.

### Industrial (2 of 28 available)

| Item | Ticker | Unit |
|---|---|---|
| Aluminum | `ALI=F` | USD/metric ton |
| Palladium | `PA=F` | USD/oz |

Unavailable: the remaining 26 — LME base metals (Lead, Tin, Zinc, Nickel), rare
earths/minor metals (Rhodium, Molybdenum, Neodymium, Tellurium, Gallium, Germanium,
Indium, Manganese, Cobalt, Magnesium), petrochemicals/plastics (Polyethylene,
Polyvinyl, Polypropylene, Synthetic Rubber, Styrene, Sulfur), fertilizers (Urea,
Di-ammonium, Soda Ash), and Bitumen, Phosphorus, Kraft Pulp. None trade on a
Yahoo-mirrored exchange.

### Livestock (3 of 8 available)

| Item | Ticker | Unit |
|---|---|---|
| Feeder Cattle | `GF=F` | cents/lb |
| Live Cattle | `LE=F` | cents/lb |
| Lean Hogs | `HE=F` | cents/lb |

Unavailable: Beef, Poultry, Eggs US, Eggs CH, Salmon (Fish Pool) — no futures-exchange
proxy on Yahoo.

### Index (1 of 9 available)

| Item | Ticker | Unit |
|---|---|---|
| GSCI | `^SPGSCI` | index points (S&P GSCI) |

Unavailable: CRB Index (checked `^CRB`/`CRBQ`, neither resolves), SSE Commodity
Index, World Container Index, Containerized Freight Index, EU Carbon Permits, Wind/
Nuclear/Solar Energy Index — the energy-transition "indexes" are thematic ETF baskets
(e.g. `TAN`, `ICLN`), not literal commodity indices, so they're excluded rather than
mislabeled as equivalents.

### Electricity (0 of 5 available)

United Kingdom, Germany, France, Italy, Spain day-ahead power prices trade on
regional exchanges (EPEX, Nord Pool) with no free/keyless data source. All five are
documented as unavailable; no code fetches anything for this section.

**Total: 32 of 103 named items available.**

## Notebook sections

Matches the simple fetch → table style of `oil_prices_query.ipynb` (not the deeper
trend-analysis style of `usd_thb_trend_and_indices.ipynb`):

1. **Intro (markdown)** — states purpose and the 32/103 headline coverage number, and
   why the gap exists (no paid Trading Economics/Platts/Argus/LME feed configured).
2. **One section per category** (Energy, Metals, Agricultural, Industrial, Livestock,
   Index, Electricity), each:
   - Markdown subheader: "N of M available"
   - Code cell (skipped entirely for Electricity, which has zero available items):
     fetch each ticker via `yf.Ticker(ticker).history(period="5d")`, take the latest
     close, assemble into a small `DataFrame` (columns: item, ticker, date, price,
     unit) and display it
   - Markdown note: bullet list of that category's unavailable items with a one-line
     reason
3. **Coverage summary** — a horizontal bar chart, one bar per category, available vs.
   unavailable stacked or grouped (32/103 overall called out in the title/caption).
   Built following the `dataviz` skill's guidance (invoked at implementation time,
   before writing this chart cell).

## Error handling

Each per-category fetch loop wraps individual ticker calls so one bad/delisted ticker
doesn't blank the whole category table — same spirit as `pipeline.py`'s per-series
isolation, but implemented locally in the notebook since this bypasses
`macro_data.update()` entirely (no `MissingKeyError`/status-dict machinery to reuse
here — these are all keyless Yahoo tickers).

## Testing

No pytest coverage (notebooks aren't covered by the suite). Correctness is verified by
`jupyter nbconvert --to notebook --execute --inplace notebooks/commodities_te_query.ipynb
--ExecutePreprocessor.timeout=180` per CLAUDE.md, confirming all 32 tickers resolve and
every cell runs end-to-end.

## Out of scope

- No historical trend charts, moving averages, or volatility — this is a coverage/
  latest-value survey, not a trend-analysis notebook.
- No `catalog.yaml` changes — standalone, per the chosen approach; only the reference
  catalog CSV described below is persisted, not a `macro_data`-store series.
- No attempt to reach 100% coverage via a paid feed (Trading Economics, FMP paid
  tier, Platts/Argus) — out of scope until the user decides to acquire and configure
  one of those keys.
- No normalized cross-category comparison chart (as in `commodity_prices_query.ipynb`)
  — 32 series on one chart would be unreadable; the coverage bar chart replaces it.

## Addendum: reference catalog CSV (2026-07-16)

Added `notebooks/commodities_te_catalog.csv` alongside the notebook — a flat,
spreadsheet-friendly reference table (one row per named item, all 103) so a user can
see at a glance which source/ticker to use for each commodity without opening the
notebook. Columns: `ticker`, `source` (`"Yahoo Finance"` or blank), `security_name`,
`description` (unit + exchange for available items; reason it's unavailable
otherwise), `tag` (the category). This surfaced the Industrial count error corrected
above (27 → 28) — the CSV's per-category row counts are the authoritative numbers
going forward.
