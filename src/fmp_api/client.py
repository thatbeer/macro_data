"""Thin HTTP client for Financial Modeling Prep's stable API."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests

from .endpoints.economics import EconomicsEndpoint

BASE_URL = "https://financialmodelingprep.com/stable/"


class FMPClient:
    """HTTP client for financialmodelingprep.com/stable, namespaced by category::

        fmp = FMPClient()
        fmp.economics.treasury_rates(from_date, to_date)

    A single `FMP_API_KEY` covers every endpoint your FMP plan allows — unlike
    `BOTClient`'s three separate subscription keys. `FMPClient()` always
    succeeds; a missing key only raises when a namespace method is actually
    called (see `endpoints/base.py`).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        timeout: int = 30,
    ):
        self.api_key = api_key or os.environ.get("FMP_API_KEY")
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

        self.economics = EconomicsEndpoint(self)

    def get(self, path: str, params: dict[str, Any] | None = None) -> list | dict:
        """GET `path` (relative to base_url) with `apikey` merged into the query params."""
        response = requests.get(
            self.base_url + path.lstrip("/"),
            params={**(params or {}), "apikey": self.api_key},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def to_dataframe(payload: list | dict) -> pd.DataFrame:
        """FMP returns a flat JSON list for every endpoint tested, even single-item
        lookups like `/quote` — wrap a bare dict in a list just in case."""
        return pd.DataFrame(payload if isinstance(payload, list) else [payload])
