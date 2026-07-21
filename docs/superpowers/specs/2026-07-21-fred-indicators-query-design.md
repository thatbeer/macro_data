# FRED Indicators Query Notebook — Design

## Purpose

A new notebook, `notebooks/fred_indicators_query.ipynb`, demonstrates FRED API usage
via the standalone `src/fred_api` client — fetching and charting CPI, inflation, and a
handful of other core US macro indicators. It's exploratory, same spirit as
`BOT_query.ipynb` and `worldbank_gep_forecast.ipynb`: it queries the API directly and
stays outside the `macro_data` catalog/schema/store pipeline. Nothing here is written
to `data/`.

`catalog.yaml` currently registers only two FRED series (`us_cpi`, `fed_funds_rate`),
each fetched through `macro_data/sources/fred.py`'s single `observations`-only call.
`src/fred_api`'s `FREDClient` was built to go beyond that (it also has `info`, `search`,
`categories`, `tags`), but this notebook only exercises `observations` — the goal is a
data/chart tour of the indicators themselves, not an API-mechanics tour.

## No catalog change

This notebook does not add anything to `catalog.yaml` and does not persist to `data/`.
It calls `FREDClient` directly, mirroring `BOT_query.ipynb`'s relationship to
`macro_data/sources/bot.py`.

## Series covered

All six fetched via `client.series.observations(series_id, from_date="2000-01-01")`
(full history from 2000 to present):

| Series ID  | What it is                                          | Frequency |
|------------|------------------------------------------------------|-----------|
| `CPIAUCSL` | Headline CPI, all urban consumers (index)             | Monthly   |
| `CPILFESL` | Core CPI, ex food & energy (index)                    | Monthly   |
| `PCEPI`    | PCE Price Index — the Fed's preferred inflation gauge | Monthly   |
| `UNRATE`   | Unemployment rate (%)                                 | Monthly   |
| `FEDFUNDS` | Fed funds effective rate (%)                          | Monthly   |
| `GDPC1`    | Real GDP, chained dollars (level)                     | Quarterly |

CPI/PCE series are index levels, not inflation rates. "Inflation" is derived
client-side as year-over-year percent change (`pct_change(12) * 100` for monthly index
series; `pct_change(4) * 100` for quarterly `GDPC1` to get YoY real GDP growth) — FRED
doesn't hand back a pre-computed rate for these series IDs. This mirrors how
`bonds_and_economic_indicators.ipynb` derives the 10Y-3M spread from raw yields rather
than expecting the source to provide it directly.

## Notebook sections

1. **Intro (markdown)** — states the purpose and that this exercises `src/fred_api`
   directly, not the `macro_data` catalog pipeline (same framing `BOT_query.ipynb`
   opens with).
2. **Setup** — `sys.path` insert `../src`, `load_dotenv(Path("..") / ".env")`,
   `FREDClient()`. A small `fetch_series(series_id, from_date)` helper wraps
   `client.series.observations()` and cleans the result: FRED's raw response has
   `value` as a string with `"."` for missing observations, so the helper does
   `pd.to_numeric(errors="coerce")` + `pd.to_datetime` + `dropna` + set `date` as
   index. (This is the notebook's own light cleanup, not `macro_data.schema.normalize`
   — that function is internal to the package pipeline.)
3. **CPI** — headline vs. core, fetched and plotted as index levels on one chart.
4. **Inflation, three ways** — headline CPI YoY, core CPI YoY, and PCE YoY computed and
   overlaid on one chart — the classic "which inflation gauge" comparison.
5. **Unemployment rate** — fetched and plotted alone.
6. **Fed funds rate vs. inflation** — fed funds rate plotted alongside headline CPI YoY
   from §4, showing the policy-rate response to inflation.
7. **Real GDP growth** — `GDPC1` YoY, fetched and plotted alone.
8. **Notes (markdown)** — states this is exploratory/standalone (no `data/` writes),
   and points out `catalog.yaml` already tracks `us_cpi`/`fed_funds_rate` for anyone
   who wants ongoing incremental history through the real pipeline instead of ad-hoc
   queries — with `UNRATE`/`GDPC1`/`PCEPI`/`CPILFESL` as candidates to add there if
   ongoing tracking is ever wanted.

## Error handling

No `try_call()`-style wrapper (unlike `BOT_query.ipynb`, which needs one because
several BOT endpoints require separate, sometimes-missing subscription keys). FRED is
a single stable provider, and `FRED_API_KEY` is already confirmed present in `.env`, so
a normal call failing would indicate a real problem worth seeing directly, not a
routine gap to swallow.

## Testing

None — notebooks aren't covered by `pytest`. Correctness is verified by running
`python -m jupyter nbconvert --to notebook --execute --inplace
notebooks/fred_indicators_query.ipynb --ExecutePreprocessor.timeout=180` per
`CLAUDE.md`, so committed outputs reflect a real run against the live FRED API.

## Out of scope

- No `catalog.yaml` changes and no `data/fred/` writes — this is exploratory only.
- No API-mechanics tour (`series.info`, `series.search`, `categories`, `tags`) — this
  notebook is data/chart-focused per explicit scope decision; a mechanics-focused
  notebook is a possible separate follow-up.
- No cross-country comparison (e.g., Thailand CPI) — `catalog.yaml`'s World Bank
  section and `leading_coincident_lagging_indicators.ipynb` already cover Thailand
  macro indicators; this notebook stays US-only, matching the "CPI, inflation, and
  others" scope as US FRED indicators.
