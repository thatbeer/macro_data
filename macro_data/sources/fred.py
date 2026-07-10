"""FRED (US Federal Reserve) fetcher. Needs free API key: https://fred.stlouisfed.org/docs/api/api_key.html"""

import os

import pandas as pd
import requests

from .. import schema
from ..catalog import SeriesConfig
from .base import BaseSource, MissingKeyError

OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


class FredSource(BaseSource):
    name = "fred"

    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            raise MissingKeyError("FRED_API_KEY")
        params = {
            "series_id": cfg.params["series"],
            "api_key": api_key,
            "file_type": "json",
        }
        if start is not None:
            params["observation_start"] = start.strftime("%Y-%m-%d")
        resp = requests.get(OBSERVATIONS_URL, params=params, timeout=30)
        resp.raise_for_status()
        observations = resp.json().get("observations", [])
        if not observations:
            return schema.empty()
        df = pd.DataFrame(observations)
        return schema.normalize(df)  # coerces "." missing markers to NaN and drops them
