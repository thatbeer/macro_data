"""Historical and intraday price chart service (historical-price-eod-*, intraday-*) -> `client.chart`."""

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


class ChartEndpoint(Endpoint):
    def historical_eod_full(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Full OHLCV daily history (`/historical-price-eod-full`)."""
        return self._request(
            "historical-price-eod-full", _date_params(symbol, from_date, to_date), return_json
        )

    def historical_eod_light(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Close-only daily history (`/historical-price-eod-light`)."""
        return self._request(
            "historical-price-eod-light", _date_params(symbol, from_date, to_date), return_json
        )

    def historical_eod_dividend_adjusted(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Dividend-adjusted daily history (`/historical-price-eod-dividend-adjusted`)."""
        return self._request(
            "historical-price-eod-dividend-adjusted",
            _date_params(symbol, from_date, to_date),
            return_json,
        )

    def historical_eod_non_split_adjusted(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Unadjusted-for-splits daily history (`/historical-price-eod-non-split-adjusted`)."""
        return self._request(
            "historical-price-eod-non-split-adjusted",
            _date_params(symbol, from_date, to_date),
            return_json,
        )

    def intraday_1min(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """1-minute interval bars (`/intraday-1-min`)."""
        return self._request("intraday-1-min", _date_params(symbol, from_date, to_date), return_json)

    def intraday_5min(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """5-minute interval bars (`/intraday-5-min`)."""
        return self._request("intraday-5-min", _date_params(symbol, from_date, to_date), return_json)

    def intraday_15min(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """15-minute interval bars (`/intraday-15-min`)."""
        return self._request("intraday-15-min", _date_params(symbol, from_date, to_date), return_json)

    def intraday_30min(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """30-minute interval bars (`/intraday-30-min`)."""
        return self._request("intraday-30-min", _date_params(symbol, from_date, to_date), return_json)

    def intraday_1hour(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """1-hour interval bars (`/intraday-1-hour`)."""
        return self._request("intraday-1-hour", _date_params(symbol, from_date, to_date), return_json)

    def intraday_4hour(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """4-hour interval bars (`/intraday-4-hour`)."""
        return self._request("intraday-4-hour", _date_params(symbol, from_date, to_date), return_json)
