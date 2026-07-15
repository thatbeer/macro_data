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

This notebook instead uses the catalog's `usd_thb_bot` series — BOT's **daily average
reference rate** (`mid_rate`, from `Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE`, the old
`apigw1.bot.or.th` gateway via `macro_data.sources.bot`). It's the closest live,
officially-published daily USD/THB figure BOT offers, and it's already wired into
`catalog.yaml`.

## Data sources

| Side | Series | Package call | Status |
|---|---|---|---|
| BOT | `usd_thb_bot` (mid_rate) | `macro_data.update("bot")` then `load("usd_thb_bot")` | Not yet fetched — no `data/bot/` folder exists yet |
| Yahoo | `usd_thb` (`THB=X`) | `macro_data.update("yahoo")` then `load("usd_thb")` | Already fetched (`data/yahoo/usd_thb.csv` exists) |

Both are loaded through the public `macro_data` package surface (`update`, `load`),
matching the convention already used in `usd_thb_trend_and_indices.ipynb` — not the
standalone `bot_api` client, which is for ad-hoc exploration only (`BOT_query.ipynb`).

## Notebook sections

1. **Intro (markdown)** — states the comparison purpose and documents upfront why
   `mid_rate` stands in for "BOT spot rate" (see above), so a reader doesn't wonder why
   the notebook isn't calling the endpoint literally named `spot_rate`.
2. **Fetch** — `update("bot")` and `update("yahoo")`, printing the returned status dicts.
   Both calls run un-guarded (no try/except): `pipeline.py` already isolates per-series
   failures internally and returns a status string per series id, so a failure surfaces
   in the printed dict rather than raising.
3. **Load & restrict to last 1 year** — `load("usd_thb_bot")`, `load("usd_thb")`; each
   sliced independently to its own last 365 days (`s.index >= s.index.max() -
   pd.Timedelta(days=365)`), since the two series may not share a last date.
4. **Align** — inner-join the two frames on date (same technique as `BOT_query.ipynb`
   §5's `ref_daily.merge(daily_usd[...], on="period", how="inner")`). Print how many of
   each source's dates survived the join, since BOT publishes business days only while
   `THB=X` trades most calendar days.
5. **Comparison table** — last ~10 aligned rows: BOT mid_rate, yfinance close, absolute
   diff, % diff.
6. **Chart** — both series overlaid on one time axis over the 1-year window.
7. **Difference chart + stats** — plot `(yahoo_close - bot_mid_rate)` over time; report
   mean, std, and max absolute difference, plus the Pearson correlation between the two
   levels.
8. **Closing notes (markdown)** — caveat that BOT's `mid_rate` is a once-daily official
   survey average (banks report rates to BOT, which computes the average) while
   yfinance's close is a continuously-quoted market snapshot at day-end — so a small,
   fairly consistent gap between the two is expected behavior, not a data error.

## Error handling

No additional try/except beyond what `pipeline.py` already provides. If `update("bot")`
reports a per-series failure (e.g., missing `BOT_CLIENT_ID`), that string is visible in
the printed status dict, and the subsequent `load("usd_thb_bot")` raises a natural
`FileNotFoundError`/`KeyError` if no CSV was ever written — consistent with how the
existing notebooks let missing-key failures surface rather than masking them.

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
