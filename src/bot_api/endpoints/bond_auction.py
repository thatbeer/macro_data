"""Bond auction service (BondAuction) -> `client.bond_auction`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class BondAuctionEndpoint(Endpoint):
    service = "BondAuction"
    key_attr = "bond_auction_key"

    def auction(
        self, start_period: str, end_period: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        """Government bond auction results (`/bond_auction_v2/`).

        start_period/end_period format: `YYYY-MM-DD`.
        """
        params = {"start_period": start_period, "end_period": end_period}
        return self._request(
            "bond_auction_v2", params, return_json, date_field="auction_date"
        )
