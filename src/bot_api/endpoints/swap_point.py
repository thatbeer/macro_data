"""Swap Point (Onshore) service (Stat-SwapPoint) -> `client.swap_point`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class SwapPointEndpoint(Endpoint):
    service = "Stat-SwapPoint/v2"
    key_attr = "interest_key"

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Onshore swap points, in satangs (`/SWAPPOINT/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("SWAPPOINT", params, return_json)
