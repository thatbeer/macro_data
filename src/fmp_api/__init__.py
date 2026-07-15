"""Standalone client for Financial Modeling Prep's stable API (financialmodelingprep.com).

Kept outside the `macro_data` package on purpose: FMP's responses (quotes, OHLCV
bars, index constituents, indicator batches) don't fit the package's single-`value`
canonical schema — this client is for ad-hoc, notebook-driven queries that don't
need to land in the CSV store, the same rationale as `src/bot_api`.

A single `FMP_API_KEY` covers every namespace your FMP plan allows.
`technical_indicators` requires a paid plan (Starter/Premium/Ultimate/Enterprise)
and will fail via the underlying HTTP error on a free-tier key — this is expected,
not a bug.

Usage::

    fmp = FMPClient()  # reads FMP_API_KEY from the environment
    fmp.economics.treasury_rates(from_date, to_date)
    fmp.commodity.quote("GCUSD")
    fmp.forex.historical_eod_light("EURUSD")
    fmp.indexes.sp500()
    fmp.quote.batch_quote(["AAPL", "MSFT"])
    fmp.chart.historical_eod_full("AAPL", from_date, to_date)
    fmp.technical_indicators.rsi("AAPL", period_length=14, timeframe="1day")
"""

from .client import FMPClient

__all__ = ["FMPClient"]
