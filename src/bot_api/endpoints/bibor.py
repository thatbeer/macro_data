"""Bangkok Interbank Offered Rate service (BIBOR) -> `client.bibor`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class BiborEndpoint(Endpoint):
    service = "BIBOR/v2"
    key_attr = "interest_key"

    def daily(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Bangkok Interbank Offered Rate (`/bibor_rate/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        params = {"start_period": start_period, "end_period": end_period}
        return self._request("bibor_rate", params, return_json)
