"""Exchange rate service (Stat-ExchangeRate) -> `client.exchange`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class ExchangeRateEndpoint(Endpoint):
    """Average Exchange Rate - THB / Foreign Currency.

    Data collected include exchange rates quoted for immediate delivery (i.e., in the
    spot market) between Thai Baht vis-à-vis 19 other currencies. Exchange rate data
    are obtained from daily foreign exchange transaction reports from commercial banks
    in Thailand.

    Frequency        : Daily
    Lag time         : --
    Release schedule : Every business day at 6.00 p.m. (BKK, GMT+07:00)
    Source of data   :
        1. Commercial Banks registered in Thailand
        2. Foreign Bank Branches
        3. Special-purpose Financial Institutions
    """

    service = "Stat-ExchangeRate/v2"

    def _rates(
        self,
        endpoint: str,
        start_period: str,
        end_period: str,
        currency: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | dict:
        params = {"start_period": start_period, "end_period": end_period}
        if currency is not None:
            params["currency"] = currency   
        return self._request(endpoint, params, return_json)

    def daily(
        self,
        start_period: str,
        end_period: str,
        currency: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | dict:
        """Daily average reference exchange rates (`/DAILY_AVG_EXG_RATE/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        return self._rates("DAILY_AVG_EXG_RATE", start_period, end_period, currency, return_json)

    def monthly(
        self,
        start_period: str,
        end_period: str,
        currency: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | dict:
        """Monthly average reference exchange rates (`/MONTHLY_AVG_EXG_RATE/`).

        start_period/end_period format: `YYYY-MM`.
        """
        return self._rates(
            "MONTHLY_AVG_EXG_RATE", start_period, end_period, currency, return_json
        )

    def quarterly(
        self,
        start_period: str,
        end_period: str,
        currency: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | dict:
        """Quarterly average reference exchange rates (`/QUARTERLY_AVG_EXG_RATE/`).

        start_period/end_period format: `YYYY-Q#` (e.g. `2024-Q1`).
        """
        return self._rates(
            "QUARTERLY_AVG_EXG_RATE", start_period, end_period, currency, return_json
        )

    def annual(
        self,
        start_period: str,
        end_period: str,
        currency: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | dict:
        """Annual average reference exchange rates (`/ANNUAL_AVG_EXG_RATE/`).

        start_period/end_period format: `YYYY`.
        """
        return self._rates(
            "ANNUAL_AVG_EXG_RATE", start_period, end_period, currency, return_json
        )
