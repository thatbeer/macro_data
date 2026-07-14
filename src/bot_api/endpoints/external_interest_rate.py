"""External Interest Rate service (Stat-ExternalInterestRate) -> `client.external_interest_rate`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class ExternalInterestRateEndpoint(Endpoint):
    service = "Stat-ExternalInterestRate/v2"
    key_attr = "interest_key"

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """External (offshore reference) interest rates (`/EXT_INT_RATE/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("EXT_INT_RATE", params, return_json)
