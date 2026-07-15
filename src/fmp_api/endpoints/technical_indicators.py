"""Technical analysis indicator service (simple-moving-average, rsi, ...) -> `client.technical_indicators`.

Requires a paid FMP plan (Starter/Premium/Ultimate/Enterprise) per FMP's own
docs — every method here will fail via `raise_for_status()` on a free-tier
key, same as any other HTTP error this client surfaces. Not special-cased.
"""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


def _indicator_params(
    symbol: str, period_length: int, timeframe: str, from_date: str | None, to_date: str | None
) -> dict:
    params: dict = {"symbol": symbol, "periodLength": period_length, "timeframe": timeframe}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return params


class TechnicalIndicatorsEndpoint(Endpoint):
    def sma(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Simple moving average (`/simple-moving-average`)."""
        return self._request(
            "simple-moving-average",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )

    def ema(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Exponential moving average (`/exponential-moving-average`)."""
        return self._request(
            "exponential-moving-average",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )

    def dema(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Double exponential moving average (`/double-exponential-moving-average`)."""
        return self._request(
            "double-exponential-moving-average",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )

    def tema(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Triple exponential moving average (`/triple-exponential-moving-average`)."""
        return self._request(
            "triple-exponential-moving-average",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )

    def wma(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Weighted moving average (`/weighted-moving-average`)."""
        return self._request(
            "weighted-moving-average",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )

    def rsi(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Relative strength index (`/relative-strength-index`)."""
        return self._request(
            "relative-strength-index",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )

    def adx(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Average directional index (`/average-directional-index`)."""
        return self._request(
            "average-directional-index",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )

    def williams(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Williams %R (`/williams`)."""
        return self._request(
            "williams",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )

    def standard_deviation(
        self,
        symbol: str,
        period_length: int,
        timeframe: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Standard deviation (`/standard-deviation`)."""
        return self._request(
            "standard-deviation",
            _indicator_params(symbol, period_length, timeframe, from_date, to_date),
            return_json,
        )
