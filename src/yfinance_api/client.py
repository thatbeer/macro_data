"""Thin, consistent facade over the yfinance library's Ticker-based calls."""

from __future__ import annotations

from .endpoints.history import HistoryEndpoint
from .endpoints.info import InfoEndpoint


class YFinanceClient:
    """Namespaced facade over `yfinance.Ticker`, replacing ad hoc `yf.Ticker(...)`
    calls duplicated across notebooks::

        yfc = YFinanceClient()
        yfc.history.daily("AAPL", period="3mo")
        yfc.history.intraday("AAPL", interval="1h", period="5d")
        yfc.info.quote("AAPL")
        yfc.info.fast_info("AAPL")

    No API key — yfinance needs none.
    """

    def __init__(self):
        self.history = HistoryEndpoint(self)
        self.info = InfoEndpoint(self)
