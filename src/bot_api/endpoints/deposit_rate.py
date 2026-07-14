"""Deposit Rate service (DepositRate) -> `client.deposit_rate`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class DepositRateEndpoint(Endpoint):
    service = "DepositRate/v2"
    key_attr = "interest_key"

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Commercial bank deposit interest rates for individuals (`/deposit_rate/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("deposit_rate", params, return_json)
