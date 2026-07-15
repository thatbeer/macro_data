"""Quote/company summary info, wrapping yf.Ticker(...).info / .fast_info -> `client.info`."""

from __future__ import annotations

import yfinance as yf

from .base import Endpoint


class InfoEndpoint(Endpoint):
    def quote(self, ticker: str) -> dict:
        """Full quote/company summary dict (`yf.Ticker(ticker).info`) — slower, more fields."""
        return yf.Ticker(ticker).info

    def fast_info(self, ticker: str) -> dict:
        """Lightweight quote dict (`yf.Ticker(ticker).fast_info`) — faster, fewer fields.

        yfinance returns a custom `FastInfo` mapping object here, not a plain
        `dict`; casting keeps this client's return type consistent with `quote()`.
        """
        return dict(yf.Ticker(ticker).fast_info)
