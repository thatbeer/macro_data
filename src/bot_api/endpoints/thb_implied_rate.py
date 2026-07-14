"""Thai Baht Implied Interest Rate service (Stat-ThaiBahtImpliedInterestRate) -> `client.thb_implied_rate`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class ThaiBahtImpliedRateEndpoint(Endpoint):
    service = "Stat-ThaiBahtImpliedInterestRate/v2"
    key_attr = "interest_key"

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Thai Baht implied interest rate (`/THB_IMPL_INT_RATE/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("THB_IMPL_INT_RATE", params, return_json)
