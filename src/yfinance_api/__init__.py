"""Standalone facade over the yfinance library, centralizing the yf.Ticker(...)
calls already duplicated across notebooks/fx_ohlcv_query.ipynb and
notebooks/commodities.ipynb.

Unlike src/bot_api, src/fmp_api, and src/fred_api, this isn't a REST client —
yfinance already is the client, so there's no HTTP layer here and no API key.
Separate from macro_data/sources/yahoo.py, which uses yf.download() (a
different yfinance entry point) for the catalog-driven single-series pipeline.

Usage::

    yfc = YFinanceClient()
    yfc.history.daily("AAPL", period="3mo")
    yfc.history.intraday("AAPL", interval="1h", period="5d")
    yfc.info.quote("AAPL")
    yfc.info.fast_info("AAPL")
"""

from .client import YFinanceClient

__all__ = ["YFinanceClient"]
