"""Macroeconomic data service (economics-calendar, treasury-rates, ...) -> `client.economics`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class EconomicsEndpoint(Endpoint):
    def calendar(
        self, from_date: str | None = None, to_date: str | None = None, return_json: bool = False
    ) -> pd.DataFrame | list:
        """Economic data releases calendar (`/economics-calendar`)."""
        params: dict = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._request("economics-calendar", params, return_json)

    def indicators(
        self,
        name: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | list:
        """Named economic indicator series, e.g. GDP, CPI (`/economics-indicators`)."""
        params: dict = {"name": name}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._request("economics-indicators", params, return_json)

    def market_risk_premium(self, return_json: bool = False) -> pd.DataFrame | list:
        """Market risk premium by country (`/market-risk-premium`)."""
        return self._request("market-risk-premium", {}, return_json)

    def treasury_rates(
        self, from_date: str | None = None, to_date: str | None = None, return_json: bool = False
    ) -> pd.DataFrame | list:
        """US Treasury rates across maturities (`/treasury-rates`)."""
        params: dict = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._request("treasury-rates", params, return_json)
