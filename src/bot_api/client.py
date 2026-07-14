"""Thin HTTP client for BOT's Open Data gateway."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests

from .endpoints.bond_auction import BondAuctionEndpoint
from .endpoints.exchange_rate import ExchangeRateEndpoint
from .endpoints.interest_rate import InterestRateEndpoint
from .endpoints.reference_rate import ReferenceRateEndpoint

BASE_URL = "https://gateway.api.bot.or.th/"


class BOTClient:
    """HTTP client for gateway.api.bot.or.th, namespaced by service::

        bot = BOTClient()
        bot.exchange.daily(start_period, end_period)
        bot.interest.daily(start_period, end_period)
        bot.bond_auction.auction(start_period, end_period)
        bot.reference_rate.daily(start_period, end_period)

    BOT's developer portal issues a separate subscription key per API
    product, so this client resolves three independent keys instead of one:

    - `api_key` (env `BOT_CLIENT_ID`) -> `exchange`, `reference_rate`
    - `interest_key` (env `BOT_CLIENT_ID_INTEREST`) -> `interest`
    - `bond_auction_key` (env `BOT_CLIENT_ID_BOND_AUCTION`) -> `bond_auction`

    Each may be passed explicitly or left to be read from its environment
    variable. None is required at construction time: `BOTClient()` always
    succeeds, and a missing key only raises when a namespace that needs it
    is actually called (see `endpoints/base.py`).
    """

    def __init__(
        self,
        api_key: str | None = None,
        interest_key: str | None = None,
        bond_auction_key: str | None = None,
        base_url: str = BASE_URL,
        timeout: int = 30,
    ):
        self.api_key = api_key or os.environ.get("BOT_CLIENT_ID")
        self.interest_key = interest_key or os.environ.get("BOT_CLIENT_ID_INTEREST")
        self.bond_auction_key = bond_auction_key or os.environ.get("BOT_CLIENT_ID_BOND_AUCTION")
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

        self.exchange = ExchangeRateEndpoint(self)
        self.interest = InterestRateEndpoint(self)
        self.bond_auction = BondAuctionEndpoint(self)
        self.reference_rate = ReferenceRateEndpoint(self)

    def get(
        self, path: str, params: dict[str, Any] | None = None, api_key: str | None = None
    ) -> dict[str, Any]:
        """GET `path` (relative to base_url) and return the parsed JSON body.

        Uses `api_key` if given, otherwise falls back to `self.api_key`. Callers
        needing a different product's key (interest, bond_auction) pass it explicitly.
        """
        response = requests.get(
            self.base_url + path.lstrip("/"),
            headers={"Authorization": api_key or self.api_key, "Accept": "application/json"},
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def to_dataframe(payload: dict[str, Any], date_field: str = "period") -> pd.DataFrame:
        """Flatten a `result.data.data_detail` payload into a DataFrame."""
        detail = payload.get("result", {}).get("data", {}).get("data_detail", []) or []
        df = pd.DataFrame(detail)
        if date_field in df.columns:
            # `period` granularity varies by frequency (`2024-01-05`, `2024-01`, `2024-Q1`,
            # `2024`), so a single strptime format can't cover every endpoint.
            df[date_field] = pd.to_datetime(df[date_field], format="mixed")
        return df
