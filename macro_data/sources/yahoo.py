"""Yahoo Finance fetcher (FX, commodities futures, market indices). No API key."""

import pandas as pd
import yfinance as yf

from .. import schema
from ..catalog import SeriesConfig
from .base import BaseSource


class YahooSource(BaseSource):
    name = "yahoo"

    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        ticker = cfg.params["ticker"]
        kwargs = {"progress": False, "auto_adjust": True}
        if start is not None:
            kwargs["start"] = start.strftime("%Y-%m-%d")
        else:
            kwargs["period"] = "max"
        raw = yf.download(ticker, **kwargs)
        if raw is None or raw.empty:
            return schema.empty()
        close = raw["Close"]
        if isinstance(close, pd.DataFrame):  # yfinance returns MultiIndex columns
            close = close.iloc[:, 0]
        df = pd.DataFrame({"date": close.index, "value": close.to_numpy()})
        return schema.normalize(df)
