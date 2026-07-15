"""Real-time quote service (quote, batch-quote, full-*-quotes, ...) -> `client.quote`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class QuoteEndpoint(Endpoint):
    def quote(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Full stock quote (`/quote`)."""
        return self._request("quote", {"symbol": symbol}, return_json)

    def quote_short(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Short stock quote (`/quote-short`)."""
        return self._request("quote-short", {"symbol": symbol}, return_json)

    def quote_change(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Stock price change over standard periods (`/quote-change`)."""
        return self._request("quote-change", {"symbol": symbol}, return_json)

    def batch_quote(self, symbols: list[str], return_json: bool = False) -> pd.DataFrame | list:
        """Full quotes for multiple symbols at once (`/batch-quote`)."""
        return self._request("batch-quote", {"symbols": ",".join(symbols)}, return_json)

    def batch_quote_short(self, symbols: list[str], return_json: bool = False) -> pd.DataFrame | list:
        """Short quotes for multiple symbols at once (`/batch-quote-short`)."""
        return self._request("batch-quote-short", {"symbols": ",".join(symbols)}, return_json)

    def aftermarket_quote(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Aftermarket quote for one symbol (`/aftermarket-quote`)."""
        return self._request("aftermarket-quote", {"symbol": symbol}, return_json)

    def aftermarket_trade(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Aftermarket trade for one symbol (`/aftermarket-trade`)."""
        return self._request("aftermarket-trade", {"symbol": symbol}, return_json)

    def batch_aftermarket_quote(
        self, symbols: list[str], return_json: bool = False
    ) -> pd.DataFrame | list:
        """Aftermarket quotes for multiple symbols (`/batch-aftermarket-quote`)."""
        return self._request("batch-aftermarket-quote", {"symbols": ",".join(symbols)}, return_json)

    def batch_aftermarket_trade(
        self, symbols: list[str], return_json: bool = False
    ) -> pd.DataFrame | list:
        """Aftermarket trades for multiple symbols (`/batch-aftermarket-trade`)."""
        return self._request("batch-aftermarket-trade", {"symbols": ",".join(symbols)}, return_json)

    def full_commodities_quotes(self, return_json: bool = False) -> pd.DataFrame | list:
        """Full quotes for every commodity (`/full-commodities-quotes`)."""
        return self._request("full-commodities-quotes", {}, return_json)

    def full_cryptocurrency_quotes(self, return_json: bool = False) -> pd.DataFrame | list:
        """Full quotes for every cryptocurrency (`/full-cryptocurrency-quotes`)."""
        return self._request("full-cryptocurrency-quotes", {}, return_json)

    def full_etf_quotes(self, return_json: bool = False) -> pd.DataFrame | list:
        """Full quotes for every ETF (`/full-etf-quotes`)."""
        return self._request("full-etf-quotes", {}, return_json)

    def full_forex_quotes(self, return_json: bool = False) -> pd.DataFrame | list:
        """Full quotes for every forex pair (`/full-forex-quotes`)."""
        return self._request("full-forex-quotes", {}, return_json)

    def full_index_quotes(self, return_json: bool = False) -> pd.DataFrame | list:
        """Full quotes for every index (`/full-index-quotes`)."""
        return self._request("full-index-quotes", {}, return_json)

    def full_mutualfund_quotes(self, return_json: bool = False) -> pd.DataFrame | list:
        """Full quotes for every mutual fund (`/full-mutualfund-quotes`)."""
        return self._request("full-mutualfund-quotes", {}, return_json)

    def full_exchange_quotes(self, exchange: str, return_json: bool = False) -> pd.DataFrame | list:
        """Full quotes for every stock on one exchange (`/full-exchange-quotes`)."""
        return self._request("full-exchange-quotes", {"exchange": exchange}, return_json)
