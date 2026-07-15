"""Forex market data service (forex-quote, forex-list, ...) -> `client.forex`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


def _date_params(symbol: str, from_date: str | None, to_date: str | None) -> dict:
    params: dict = {"symbol": symbol}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return params


class ForexEndpoint(Endpoint):
    def list(self, return_json: bool = False) -> pd.DataFrame | list:
        """All tradable forex pairs (`/forex-list`)."""
        return self._request("forex-list", {}, return_json)

    def quote(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Full quote for one forex pair (`/forex-quote`)."""
        return self._request("forex-quote", {"symbol": symbol}, return_json)

    def quote_short(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Short quote for one forex pair (`/forex-quote-short`)."""
        return self._request("forex-quote-short", {"symbol": symbol}, return_json)

    def all_quotes(self, return_json: bool = False) -> pd.DataFrame | list:
        """Quotes for every forex pair at once (`/all-forex-quotes`)."""
        return self._request("all-forex-quotes", {}, return_json)

    def historical_eod_full(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Full OHLCV daily history (`/forex-historical-price-eod-full`)."""
        return self._request(
            "forex-historical-price-eod-full", _date_params(symbol, from_date, to_date), return_json
        )

    def historical_eod_light(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Close-only daily history (`/forex-historical-price-eod-light`)."""
        return self._request(
            "forex-historical-price-eod-light", _date_params(symbol, from_date, to_date), return_json
        )

    def intraday_1min(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """1-minute interval bars (`/forex-intraday-1-min`)."""
        return self._request(
            "forex-intraday-1-min", _date_params(symbol, from_date, to_date), return_json
        )

    def intraday_5min(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """5-minute interval bars (`/forex-intraday-5-min`)."""
        return self._request(
            "forex-intraday-5-min", _date_params(symbol, from_date, to_date), return_json
        )

    def intraday_1hour(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """1-hour interval bars (`/forex-intraday-1-hour`)."""
        return self._request(
            "forex-intraday-1-hour", _date_params(symbol, from_date, to_date), return_json
        )
