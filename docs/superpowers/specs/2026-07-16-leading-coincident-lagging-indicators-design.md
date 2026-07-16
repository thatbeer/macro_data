# Leading/Coincident/Lagging Indicators Notebook — Design

## Purpose

A new notebook, `notebooks/leading_coincident_lagging_indicators.ipynb`, demonstrates
querying macro indicators tagged by their position in the business cycle — the
Conference Board's standard **leading / coincident / lagging** classification. Leading
indicators turn before the cycle, coincident indicators move with it, lagging
indicators confirm it after the fact. The notebook fetches a US panel from FRED (16
series, all live-verified) plus a thin Thailand panel (3 series, keyless sources only),
and visually demonstrates the turning-point relationship with normalized trend charts
shaded by NBER recession periods.

## Why standalone, not `catalog.yaml`

Following the `commodities_te_query.ipynb` / `fx_ohlcv_query.ipynb` pattern: this is a
one-off demonstration of the leading/coincident/lagging concept, not a curated set the
project has decided to track indefinitely through `macro_data.update()`/`load()`.
Series are fetched directly via `FredSource().fetch()`, `WorldBankSource().fetch()`,
and `yfinance` inside the notebook, with ad-hoc `SeriesConfig` objects constructed
in-notebook (not registered in `catalog.yaml`). Nothing is persisted to `data/`.

`catalog.yaml` also has no concept of a "tag" — any extra YAML key becomes a
source-specific `param`, which would be the wrong place to carry a
leading/coincident/lagging classification that's orthogonal to how each source fetches
its data. The tag lives in the notebook's own roster table instead (see below).

## Verified indicator roster

Every series was checked live against FRED's `series` endpoint (observation range,
last-updated date) or `yfinance`/World Bank directly, since a plausible-looking series
ID can be stale, discontinued, or thinner than it looks (same discipline the
commodities-catalog design applied to ticker verification). Checked 2026-07-16;
`FRED_API_KEY` is configured in this environment.

### US panel (FRED, 16 series)

| Tag | Series ID | Freq | Description | FRED observation_end (checked) |
|---|---|---|---|---|
| Leading | `T10Y3M` | D | 10-year minus 3-month Treasury yield spread | 2026-07-15 |
| Leading | `ICSA` | W | Initial jobless claims | 2026-07-04 |
| Leading | `PERMIT` | M | New private housing units authorized (building permits) | 2026-05-01 |
| Leading | `NEWORDER` | M | Manufacturers' new orders, core capital goods ex-aircraft | 2026-05-01 |
| Leading | `UMCSENT` | M | U. Michigan Consumer Sentiment Index | 2026-05-01 |
| Leading | `AWHMAN` | M | Average weekly hours, manufacturing | 2026-06-01 |
| Coincident | `PAYEMS` | M | Nonfarm payroll employment | 2026-06-01 |
| Coincident | `INDPRO` | M | Industrial production index | 2026-05-01 |
| Coincident | `W875RX1` | M | Real personal income excluding transfer receipts | 2026-05-01 |
| Coincident | `USPHCI` | M | Coincident Economic Activity Index (Philly Fed composite) | 2026-05-01 |
| Coincident | `RSAFS` | M | Retail sales | 2026-05-01 |
| Lagging | `UEMPMEAN` | M | Average (mean) duration of unemployment | 2026-06-01 |
| Lagging | `BUSLOANS` | M | Commercial & industrial loans outstanding | 2026-06-01 |
| Lagging | `MPRIME` | M | Bank prime loan rate | 2026-06-01 |
| Lagging | `CPILFESL` | M | Core CPI (all items less food & energy) | 2026-06-01 |
| Lagging | `ULCNFB` | Q | Unit labor cost, nonfarm business | 2026-01-01 |

Plus `USREC` (NBER-based recession indicator, monthly, observation_end 2026-06-01) used
only for recession-band shading, not classified into any of the three tags.

Excluded: `USSLIND` ("Leading Index for the United States", Philly Fed) — confirmed via
live metadata check that it was discontinued in 2020 (`observation_end: 2020-02-01`,
`last_updated: 2020-04-14`), so it would render as a dead flat line for the last ~6
years. `TOTCI` (weekly C&I loan series) — redundant with `BUSLOANS`, which already
covers the same lagging concept at a cleaner monthly frequency matching the rest of
that category.

### Thailand panel (3 series — deliberately thin)

| Tag | Source | ID/Ticker | Freq | Description |
|---|---|---|---|---|
| Leading | yfinance | `^SET.BK` | D | SET Index (Thailand equities — prices lead the real economy) |
| Coincident | World Bank | `NY.GDP.MKTP.KD.ZG` (country `THA`) | A | GDP growth (annual %) |
| Lagging | World Bank | `FP.CPI.TOTL.ZG` (country `THA`) | A | CPI inflation (annual %) — same indicator code as the catalog's `th_inflation` |

This is not parity with the US panel — it's the honest ceiling of what's available
without paid data or the (currently broken, per project history) BOT gateway. FRED's
Thailand coverage was searched live (`series/search` for "Thailand leading indicator",
"Thailand composite leading", "Thailand industrial production", "Thailand interest rate
spread", etc.) and returned nothing both monthly and current — matches largely stale
World Bank mirror series (`last_updated` 2019–2024) or annual-only data. The notebook
states this gap explicitly rather than stretching weak annual proxies to look like a
real monthly leading/coincident/lagging panel.

## Notebook sections

1. **Intro (markdown)** — explains the leading/coincident/lagging framework, states
   scope (16 US FRED series + thin 3-series Thailand panel), and notes this is
   standalone (no `catalog.yaml`/`data/` changes).
2. **Indicator roster table** — loads and displays
   `notebooks/macro_cycle_indicators_catalog.csv` (see below) so the reader sees the
   full roster with tags before any chart appears.
3. **Fetch US series** — one code cell iterating the 16 FRED series (+ `USREC`),
   constructing an ad-hoc `SeriesConfig` per series and calling `FredSource().fetch()`
   directly. Each call wrapped in its own try/except (mirrors `pipeline.py`'s
   per-series isolation contract, implemented locally since this bypasses
   `macro_data.update()`'s status-dict machinery) — one bad/rate-limited series prints
   a warning and is dropped from its category rather than failing the whole cell.
   Series are aligned to a common month-start index: `T10Y3M`/`ICSA` (daily/weekly) via
   `.resample("MS").mean()`; the already-monthly series via `.resample("MS").last()`;
   `ULCNFB` (quarterly) is reindexed to month-start and forward-filled so it plots as a
   step function alongside the monthly series rather than leaving two-month gaps.
4. **Three stacked trend charts** (Leading / Coincident / Lagging), sharing an x-axis,
   window 1992-01-01 onward (the shortest available start, `NEWORDER`). Each series
   is z-scored (`(x - x.mean()) / x.std()`) over that window so differently-scaled
   series overlay meaningfully. `USREC` months are shaded across all three subplots
   with `axvspan` so the reader can see leading-panel turns happening before
   coincident-panel turns, which happen before lagging-panel turns, around each
   recession band. Built following the `dataviz` skill's guidance (invoked at
   implementation time, before writing this chart cell).
5. **Commentary (markdown)** — brief, general explanation of the typical lead/lag
   relationship (e.g., the yield curve and jobless claims historically lead by
   several months to over a year; payrolls/industrial production move with the cycle;
   unemployment duration and loan balances keep rising after a recession ends). Framed
   as general economic background, not a claim about exact values in this specific
   chart render.
6. **Latest snapshot table (US)** — one row per US series: id, tag, latest value,
   as-of date. Same style as `bonds_and_economic_indicators.ipynb`'s indicator table.
7. **Thailand panel** — markdown note stating the coverage gap and why (see above),
   then a fetch cell (SET Index via `yfinance`, GDP growth + CPI inflation via
   `WorldBankSource().fetch()`), a simple SET Index line chart (last ~5 years, no
   normalization/recession shading needed for a single series), and a small latest-
   value table for all 3 Thailand series.
8. **Scope/limitations (markdown)** — restates: standalone notebook (no persistence),
   US-centric by data availability not choice, no recession-probability modeling, no
   claim of US/Thailand parity.

## Companion file

`notebooks/macro_cycle_indicators_catalog.csv` — one row per tagged series (19 total:
16 US + 3 Thailand). `USREC` is a helper series used only for recession-band shading,
not a roster row, since it isn't classified into any of the three tags. Columns: `id`
(FRED series ID or ticker), `region`
(`US`/`Thailand`), `source` (`fred`/`worldbank`/`yfinance`), `tag`
(`leading`/`coincident`/`lagging`), `frequency`, `name`. Matches the reference-CSV
pattern established by `commodities_te_catalog.csv`.

## Error handling

Each fetch call (US and Thailand) is individually wrapped in try/except — a single
failing series prints a warning and is excluded from its category's chart/table rather
than blanking the whole section. Same spirit as `pipeline.py`'s per-series isolation,
implemented locally since this notebook bypasses `macro_data.update()` entirely.

## Testing

No pytest coverage (notebooks aren't covered by the suite). Correctness is verified by
`jupyter nbconvert --to notebook --execute --inplace
notebooks/leading_coincident_lagging_indicators.ipynb
--ExecutePreprocessor.timeout=180` per CLAUDE.md, confirming all 19 series resolve
(or fail gracefully with a printed warning) and every cell runs end-to-end.

## Out of scope

- No `catalog.yaml` changes, no `data/` persistence — standalone, per the chosen
  approach.
- No BOT (Bank of Thailand) source — confirmed broken in project history (old gateway
  dead since 2026-07-15); Thailand panel uses only World Bank and `yfinance`.
- No recession-probability model or forecast — descriptive/visual only.
- No claim of US/Thailand parity — the Thailand panel is explicitly thinner and
  annual-frequency where the US panel is monthly/weekly/daily.
- No attempt to backfill Thailand coverage via a paid feed (Trading Economics, FMP paid
  tier) — out of scope until the user decides to acquire and configure one.
