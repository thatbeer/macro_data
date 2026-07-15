# THB Rate: BOT vs. Yahoo Finance — Design

## Purpose

A new notebook, `notebooks/thb_rate_bot_vs_yahoo.ipynb`, compares Bank of Thailand's
official USD/THB rate against Yahoo Finance's `THB=X` spot quote over the last year,
to see how closely a market quote tracks BOT's officially published rate.

## Why not BOT's literal "Spot Rate" endpoint

`src/bot_api`'s `spot_rate.daily()` (`Stat-SpotRate/v2/SPOTRATE`) is the BOT endpoint
literally named "spot rate," but it is confirmed discontinued: it authenticates and
returns the right shape, but every value field is blank. BOT's own response metadata
(`data_header.report_remark_eng`) marks the table discontinued (`last_updated:
2024-12-27`, "redundant with other tables on the BOT website"). This is documented in
`notebooks/BOT_query.ipynb` §9 and is a live BOT-side fact, not a client bug — see the
`bot-api-standalone-client` memory.

This notebook was originally going to use the catalog's `usd_thb_bot` series — BOT's
**daily average reference rate** (`mid_rate`, from `Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE`,
the old `apigw1.bot.or.th` gateway via `macro_data.sources.bot`). **Amendment (found
during implementation, 2026-07-15):** that old gateway is now fully dead — `apigw1.bot.or.th`
doesn't even resolve in DNS (`NameResolutionError`), not just missing a key. This matches
a risk flagged in a prior session's memory (BOT announced discontinuing that gateway end
of 2025). So `usd_thb_bot` can't be fetched at all right now, through no fault of the
notebook or the package code.

The notebook instead uses the standalone `bot_api` client's `reference_rate.daily()` —
BOT's **weighted-average interbank reference rate** (THB/USD), on the *new* gateway
(`gateway.api.bot.or.th`), confirmed live and working in `notebooks/BOT_query.ipynb` §5.
It's queried the same ad-hoc way that notebook already does, not through
`catalog.yaml`/`macro_data`.

## Data sources

| Side | Series | Call | Status |
|---|---|---|---|
| BOT | Weighted-average interbank reference rate (THB/USD) | `bot_api.BOTClient().reference_rate.daily(start, end)` | Confirmed live (`BOT_query.ipynb` §5); needs `BOT_CLIENT_ID` (set in `.env`) |
| Yahoo | `usd_thb` (`THB=X`) | `macro_data.update("yahoo")` then `load("usd_thb")` | Already fetched (`data/yahoo/usd_thb.csv` exists) |

Yahoo is loaded through the public `macro_data` package surface (`update`, `load`),
matching the convention in `usd_thb_trend_and_indices.ipynb`. BOT is queried directly via
the standalone `bot_api` client (`sys.path.insert(0, str(Path("..") / "src"))`,
`load_dotenv`), matching the convention in `BOT_query.ipynb` — `usd_thb_bot` and
`macro_data.sources.bot` are not used by this notebook at all now.

## Notebook sections

1. **Intro (markdown)** — states the comparison purpose and documents upfront why the
   notebook uses BOT's interbank reference rate rather than the literal `spot_rate`
   endpoint (discontinued) or the catalog's `usd_thb_bot` (old gateway now dead).
2. **Setup / fetch / load** — construct a `BOTClient`, call `reference_rate.daily(start,
   end)` for the last 365 days. **Amendment:** `reference_rate.daily()` enforces an
   undocumented 31-day-per-call limit (HTTP 400 `"Exceed limit period. Limit period is 31
   days"`, discovered empirically — previously only known to apply to `bond_auction`), so
   fetching runs in ≤31-day chunks, concatenated. No per-series try/except needed: this
   is a direct ad-hoc call, matching `BOT_query.ipynb`'s style, not `pipeline.py`'s
   multi-series isolation (no catalog/store involved on the BOT side). `update("yahoo")`
   + `load("usd_thb")` for the Yahoo side, sliced to its own last 365 days.
3. **Align** — inner-join the two frames on date (same technique as `BOT_query.ipynb`
   §5's `ref_daily.merge(daily_usd[...], on="period", how="inner")`). Print how many of
   each source's dates survived the join, since BOT publishes business days only while
   `THB=X` trades most calendar days.
4. **Comparison table** — last ~10 aligned rows: BOT reference rate, yfinance close,
   absolute diff, % diff.
5. **Chart** — both series overlaid on one time axis over the 1-year window.
6. **Difference chart + stats** — plot `(yahoo_close - bot_ref_rate)` over time; report
   mean, std, and max absolute difference, plus the Pearson correlation between the two
   levels.
7. **Closing notes (markdown)** — caveat that BOT's reference rate is a once-daily
   official calculation (weighted average of interbank USD/THB trades $\geq$1M,
   published 6pm BKK) while yfinance's close is a continuously-quoted market snapshot at
   day-end — so a small, fairly consistent gap between the two is expected behavior, not
   a data error. Also notes both reasons `usd_thb_bot`/`spot_rate` weren't used.

## Error handling

No try/except around the Yahoo side beyond what `pipeline.py` already provides (a
per-series failure surfaces in `update("yahoo")`'s returned status dict). The BOT side is
a single direct `bot_client.reference_rate.daily(...)` call with no wrapping try/except —
if `BOT_CLIENT_ID` is missing, `Endpoint._resolve_key()` raises `ValueError` naming the
env var, which is an acceptable hard stop for a single ad-hoc call (this is exactly how
`BOT_query.ipynb`'s un-wrapped calls, e.g. §1 and §5, already behave).

## Testing

None — notebooks in this repo aren't covered by `pytest`; correctness is verified by
`jupyter nbconvert --execute --inplace notebooks/thb_rate_bot_vs_yahoo.ipynb
--ExecutePreprocessor.timeout=180` per `CLAUDE.md`.

## Out of scope

- Not persisting a merged/derived CSV — this notebook is comparison/analysis only,
  same spirit as `usd_thb_trend_and_indices.ipynb` (reads from the existing store,
  writes nothing new).
- Not touching `src/bot_api` or `BOT_query.ipynb` — no client code changes needed.
- Not attempting to resurrect or work around the discontinued `Stat-SpotRate` endpoint.
