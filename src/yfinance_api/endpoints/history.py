"""OHLCV bar history, wrapping yf.Ticker(...).history() -> `client.history`."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from .base import Endpoint

_OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


class HistoryEndpoint(Endpoint):
    def daily(self, ticker: str, period: str = "3mo") -> pd.DataFrame:
        """Daily OHLCV bars (`yf.Ticker(ticker).history(period=period, interval="1d")`)."""
        df = yf.Ticker(ticker).history(period=period, interval="1d")
        return df[_OHLCV_COLUMNS]

    def intraday(self, ticker: str, interval: str = "1h", period: str = "5d") -> pd.DataFrame:
        """Intraday OHLCV bars at the given interval (e.g. `"1m"`, `"5m"`, `"1h"`)."""
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return df[_OHLCV_COLUMNS]
