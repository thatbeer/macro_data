"""Stock market indexes service (index-quote, sp-500, ...) -> `client.indexes`."""

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


class IndexesEndpoint(Endpoint):
    def list(self, return_json: bool = False) -> pd.DataFrame | list:
        """All tradable index symbols (`/indexes-list`)."""
        return self._request("indexes-list", {}, return_json)

    def quote(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Full quote for one index (`/index-quote`)."""
        return self._request("index-quote", {"symbol": symbol}, return_json)

    def quote_short(self, symbol: str, return_json: bool = False) -> pd.DataFrame | list:
        """Short quote for one index (`/index-quote-short`)."""
        return self._request("index-quote-short", {"symbol": symbol}, return_json)

    def all_quotes(self, return_json: bool = False) -> pd.DataFrame | list:
        """Quotes for every index at once (`/all-index-quotes`)."""
        return self._request("all-index-quotes", {}, return_json)

    def historical_eod_full(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Full OHLCV daily history (`/index-historical-price-eod-full`)."""
        return self._request(
            "index-historical-price-eod-full", _date_params(symbol, from_date, to_date), return_json
        )

    def historical_eod_light(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Close-only daily history (`/index-historical-price-eod-light`)."""
        return self._request(
            "index-historical-price-eod-light", _date_params(symbol, from_date, to_date), return_json
        )

    def intraday_1min(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """1-minute interval bars (`/index-intraday-1-min`)."""
        return self._request(
            "index-intraday-1-min", _date_params(symbol, from_date, to_date), return_json
        )

    def intraday_5min(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """5-minute interval bars (`/index-intraday-5-min`)."""
        return self._request(
            "index-intraday-5-min", _date_params(symbol, from_date, to_date), return_json
        )

    def intraday_1hour(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """1-hour interval bars (`/index-intraday-1-hour`)."""
        return self._request(
            "index-intraday-1-hour", _date_params(symbol, from_date, to_date), return_json
        )

    def sp500(self, return_json: bool = False) -> pd.DataFrame | list:
        """Current S&P 500 constituents (`/sp-500`)."""
        return self._request("sp-500", {}, return_json)

    def nasdaq(self, return_json: bool = False) -> pd.DataFrame | list:
        """Current Nasdaq constituents (`/nasdaq`)."""
        return self._request("nasdaq", {}, return_json)

    def dow_jones(self, return_json: bool = False) -> pd.DataFrame | list:
        """Current Dow Jones constituents (`/dow-jones`)."""
        return self._request("dow-jones", {}, return_json)

    def historical_sp500(self, return_json: bool = False) -> pd.DataFrame | list:
        """Historical S&P 500 constituent changes (`/historical-sp-500`)."""
        return self._request("historical-sp-500", {}, return_json)

    def historical_nasdaq(self, return_json: bool = False) -> pd.DataFrame | list:
        """Historical Nasdaq constituent changes (`/historical-nasdaq`)."""
        return self._request("historical-nasdaq", {}, return_json)

    def historical_dow_jones(self, return_json: bool = False) -> pd.DataFrame | list:
        """Historical Dow Jones constituent changes (`/historical-dow-jones`)."""
        return self._request("historical-dow-jones", {}, return_json)
