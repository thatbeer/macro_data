"""World Bank open data fetcher (country-level macro indicators). No API key."""

import pandas as pd
import requests

from .. import schema
from ..catalog import SeriesConfig
from .base import BaseSource

BASE_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"


class WorldBankSource(BaseSource):
    name = "worldbank"

    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        url = BASE_URL.format(country=cfg.params["country"], indicator=cfg.params["indicator"])
        params = {"format": "json", "per_page": 20000}
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload[1] if len(payload) > 1 and payload[1] else []
        if not rows:
            return schema.empty()
        df = pd.DataFrame(rows)[["date", "value"]]
        out = schema.normalize(df)  # year strings like "2023" parse to Jan 1
        if start is not None:
            out = out[out.index >= start]  # API has no >= filter; trim client-side
        return out
