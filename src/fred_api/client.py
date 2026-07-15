"""Thin HTTP client for FRED's REST API, beyond the single series/observations
call already in macro_data/sources/fred.py."""

from __future__ import annotations

import os

import pandas as pd
import requests

from .endpoints.series import SeriesEndpoint

BASE_URL = "https://api.stlouisfed.org/fred/"


class FREDClient:
    """HTTP client for api.stlouisfed.org/fred::

        fred = FREDClient()
        fred.series.observations("GNPCA", from_date, to_date)
        fred.series.info("GNPCA")
        fred.series.search("money stock")
        fred.series.categories("GNPCA")
        fred.series.tags("GNPCA")

    Reuses the same `FRED_API_KEY` as `macro_data/sources/fred.py` — no new
    env var. `FREDClient()` always succeeds; a missing key only raises when
    `client.series.<method>()` is actually called (see `endpoints/base.py`).
    """

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL, timeout: int = 30):
        self.api_key = api_key or os.environ.get("FRED_API_KEY")
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

        self.series = SeriesEndpoint(self)

    def get(self, path: str, params: dict) -> dict:
        response = requests.get(
            self.base_url + path.lstrip("/"),
            params={**params, "api_key": self.api_key, "file_type": "json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def to_dataframe(payload: dict, key: str) -> pd.DataFrame:
        return pd.DataFrame(payload.get(key, []))
