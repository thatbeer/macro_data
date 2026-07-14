"""Interbank Transaction Rate service (Stat-InterbankTransactionRate) -> `client.interbank_txn_rate`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class InterbankTransactionRateEndpoint(Endpoint):
    service = "Stat-InterbankTransactionRate/v2"
    key_attr = "interest_key"

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Interbank transaction interest rates by term (`/INTRBNK_TXN_RATE/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("INTRBNK_TXN_RATE", params, return_json)
