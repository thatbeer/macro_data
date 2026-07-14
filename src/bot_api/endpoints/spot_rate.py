"""Spot Rate USD/THB service (Stat-SpotRate) -> `client.spot_rate`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class SpotRateEndpoint(Endpoint):
    service = "Stat-SpotRate/v2"
    key_attr = "interest_key"

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Spot exchange rate USD/THB (`/SPOTRATE/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("SPOTRATE", params, return_json)
