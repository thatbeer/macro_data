# Oil Prices Query Notebook — Design

## Purpose

A new notebook, `notebooks/oil_prices_query.ipynb`, queries the two major crude oil
benchmarks — Brent and WTI — through the `macro_data` package and plots them together.

## Catalog change

Add a `wti_oil` series to `catalog.yaml`'s Yahoo Finance section, next to the existing
`brent_oil`:

```yaml
- id: wti_oil
  source: yahoo
  ticker: "CL=F"
  name: "WTI crude futures (USD/bbl)"
```

`CL=F` is Yahoo's standard ticker for the NYMEX WTI crude futures contract, the same
convention already used for `brent_oil` (`BZ=F`) and `gold_usd` (`GC=F`).

## Notebook sections

Matches the simple fetch → load → plot style of `data_gathering_demo.ipynb` §2/§4 (not
the deeper trend-analysis style of `usd_thb_trend_and_indices.ipynb` — no moving
averages, volatility, or spread analysis):

1. **Intro (markdown)** — states the purpose: querying both crude benchmarks via
   `macro_data`.
2. **Fetch** — `update("yahoo")`, printing the returned status dict (this also refreshes
   every other Yahoo series in the catalog as a side effect, same as every other
   notebook in this repo that calls `update("yahoo")`).
3. **Load & recent values** — `load("brent_oil")`, `load("wti_oil")`; show `.tail()` for
   each.
4. **Chart** — both series overlaid on one chart. No normalization needed — both are
   already quoted in USD/bbl, unlike the FX-vs-index comparisons in other notebooks.

## Error handling

No try/except: `update("yahoo")` already isolates per-series failures into its returned
status dict (`pipeline.py`); a subsequent `load()` failure (missing CSV) raises
naturally, consistent with every other notebook in this repo.

## Testing

None — notebooks aren't covered by `pytest`; correctness is verified by
`jupyter nbconvert --execute --inplace notebooks/oil_prices_query.ipynb
--ExecutePreprocessor.timeout=180` per `CLAUDE.md`. `catalog.yaml` changes are
config-only (no code), so no new package tests are needed either.

## Out of scope

- No trend analysis (moving averages, volatility, 52-week range) — that's a possible
  follow-up notebook, not this one.
- No Brent-WTI spread calculation — a natural extension, but not part of the "simple
  query + plot" scope chosen for this notebook.
- No OHLCV bars — this notebook uses the canonical single-value `macro_data` store, not
  the separate `data/yahoo_ohlcv/` pattern from `fx_ohlcv_query.ipynb`.
