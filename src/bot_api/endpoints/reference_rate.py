"""Weighted-average interbank reference rate service (Stat-ReferenceRate) -> `client.reference_rate`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class ReferenceRateEndpoint(Endpoint):
    """Weighted-average Interbank Exchange Rate - THB / USD.

    Data is calculated from daily interbank purchases and sales of US Dollar (against
    THB) for transactions worth more than or equal to 1 million USD. The exchange
    rates are calculated using a weighted-average between the trading volume and the
    exchange rate specified. THB/USD only — unlike `Stat-ExchangeRate`, the response
    has no `currency` field to filter by.

    Frequency        : Daily
    Lag time         : --
    Release schedule : Every business day at 6.00 p.m. (BKK, GMT+07:00)
    Source of data   :
        1. Commercial Banks registered in Thailand
        2. Foreign Bank Branches
        3. Special-purpose Financial Institutions
    """

    service = "Stat-ReferenceRate/v2"

    def _rate(
        self, endpoint: str, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        params = {"start_period": start_period, "end_period": end_period}
        return self._request(endpoint, params, return_json)

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Daily weighted-average interbank THB/USD rate (`/DAILY_REF_RATE/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        return self._rate("DAILY_REF_RATE", start_period, end_period, return_json)

    def monthly(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Monthly weighted-average interbank THB/USD rate (`/MONTHLY_REF_RATE/`).

        start_period/end_period format: `YYYY-MM`.
        """
        return self._rate("MONTHLY_REF_RATE", start_period, end_period, return_json)

    def quarterly(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Quarterly weighted-average interbank THB/USD rate (`/QUARTERLY_REF_RATE/`).

        start_period/end_period format: `YYYY-Q#` (e.g. `2024-Q1`).
        """
        return self._rate("QUARTERLY_REF_RATE", start_period, end_period, return_json)

    def annual(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Annual weighted-average interbank THB/USD rate (`/ANNUAL_REF_RATE/`).

        start_period/end_period format: `YYYY`.
        """
        return self._rate("ANNUAL_REF_RATE", start_period, end_period, return_json)
