# World Bank GEP Forecast Notebook — Design

## Purpose

Provide a way to query World Bank **Global Economic Prospects (GEP)** GDP growth
forecasts — the "assumption values" used as forward-looking macro inputs — for
Thailand, the US, and the World aggregate.

## Source

- Endpoint: `https://api.worldbank.org/v2/country/{codes}/indicator/{indicator}?source=27&format=json`
  — the same World Bank REST API the project's existing `macro_data/sources/worldbank.py`
  already calls, just with `source=27` (Global Economic Prospects) instead of the
  default WDI source (`2`).
- Indicator: `NYGDPMKTPKDZ` — "GDP growth, constant (average 2010-19 prices and
  exchange rates)". This is the *only* indicator available under source 27.
- Country codes: `THA`, `USA`, `1T` (World Bank's own aggregate code for
  "World (WBG members)" — the ISO3 code `WLD` used elsewhere in this project
  returns nothing under this source).
- Confirmed live: data covers 2023–2028 (6 years), every row flagged
  `obs_status: "F"` (forecast), refreshed roughly twice a year alongside the
  GEP report.

## Scope boundary — why this is a standalone notebook, not a catalog source

`catalog.yaml` → `pipeline.py` → `store.py` assumes each series is a growing
history of actuals, appended incrementally (`store.last_date() + 1 day` drives
the next fetch). GEP data is the opposite: a small, fully-revised forecast
vintage published a few times a year, where old "forecast" years get
overwritten by the next vintage rather than extended. Forcing it through
`normalize()`/`append()` would misrepresent revisions as new history.

This follows the same precedent as `notebooks/fx_ohlcv_query.ipynb`, which
keeps OHLCV bars out of the canonical single-value store for a similar
shape-mismatch reason (see CLAUDE.md's "Deliberate scope boundary — OHLCV").

## Notebook: `notebooks/worldbank_gep_forecast.ipynb`

1. **Intro** (markdown) — what GEP forecasts are, and the scope-boundary
   rationale above.
2. **Fetch** — a small function wrapping `requests.get` against the endpoint
   above for THA/USA/1T, returning a tidy DataFrame (`country`, `year`,
   `value`, `obs_status`).
3. **Table** — display the fetched data, calling out that every row is
   forecast (`obs_status == "F"`).
4. **Chart** — line chart comparing GDP growth trajectories for Thailand, US,
   and World, 2023–2028.
5. **Save** — write the snapshot to `data/worldbank_gep/gdp_growth_forecast.csv`,
   a separate folder from `data/worldbank/` (which holds actuals from the
   existing `worldbank` source), consistent with how `fx_ohlcv_query.ipynb`
   saves to `data/yahoo_ohlcv/` instead of `data/yahoo/`.

## Out of scope

- No changes to `macro_data/sources/worldbank.py`, `catalog.yaml`, or
  `store.py`.
- No support for additional countries/aggregates or other GEP indicators
  beyond `NYGDPMKTPKDZ` (it's the only one that exists under this source).
- No automated re-fetch/refresh logic — this is a query/exploration notebook,
  executed and committed like the project's other notebooks.
