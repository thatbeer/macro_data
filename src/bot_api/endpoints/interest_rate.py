"""Interest/loan rate service (LoanRate) -> `client.interest`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class InterestRateEndpoint(Endpoint):
    service = "LoanRate/v2"
    key_attr = "interest_key"

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Commercial bank loan interest rates (`/loan_rate/`)."""
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("loan_rate", params, return_json)

    def avg_loan_interest(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Average commercial bank loan interest rates (`/avg_loan_rate/`)."""
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("avg_loan_rate", params, return_json)