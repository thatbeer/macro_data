import pandas as pd
import pytest

from yfinance_api import YFinanceClient


class FakeFastInfo(dict):
    """Stand-in for yfinance's FastInfo mapping object."""


class FakeTicker:
    def __init__(self, ticker, history_df=None, info=None, fast_info=None):
        self.ticker = ticker
        self._history_df = history_df if history_df is not None else pd.DataFrame()
        self.info = info if info is not None else {}
        self.fast_info = fast_info if fast_info is not None else FakeFastInfo()
        self.history_calls = []

    def history(self, period=None, interval=None):
        self.history_calls.append({"period": period, "interval": interval})
        return self._history_df


def _fake_ohlcv_df():
    idx = pd.to_datetime(["2024-01-01", "2024-01-02"])
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1000, 1100],
            "Dividends": [0.0, 0.0],
            "Stock Splits": [0.0, 0.0],
        },
        index=idx,
    )


def test_history_daily_calls_ticker_history_with_daily_interval(monkeypatch):
    captured = {}

    def fake_ticker_cls(ticker):
        captured["ticker"] = ticker
        return FakeTicker(ticker, history_df=_fake_ohlcv_df())

    monkeypatch.setattr("yfinance_api.endpoints.history.yf.Ticker", fake_ticker_cls)

    client = YFinanceClient()
    out = client.history.daily("AAPL", period="3mo")

    assert captured["ticker"] == "AAPL"
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert list(out["Close"]) == [101.0, 102.0]


def test_history_daily_default_period_is_3mo(monkeypatch):
    fake = FakeTicker("AAPL", history_df=_fake_ohlcv_df())
    monkeypatch.setattr("yfinance_api.endpoints.history.yf.Ticker", lambda ticker: fake)

    client = YFinanceClient()
    client.history.daily("AAPL")

    assert fake.history_calls == [{"period": "3mo", "interval": "1d"}]


def test_history_intraday_calls_ticker_history_with_given_interval(monkeypatch):
    fake = FakeTicker("AAPL", history_df=_fake_ohlcv_df())
    monkeypatch.setattr("yfinance_api.endpoints.history.yf.Ticker", lambda ticker: fake)

    client = YFinanceClient()
    out = client.history.intraday("AAPL", interval="1h", period="5d")

    assert fake.history_calls == [{"period": "5d", "interval": "1h"}]
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]


def test_history_intraday_defaults(monkeypatch):
    fake = FakeTicker("AAPL", history_df=_fake_ohlcv_df())
    monkeypatch.setattr("yfinance_api.endpoints.history.yf.Ticker", lambda ticker: fake)

    client = YFinanceClient()
    client.history.intraday("AAPL")

    assert fake.history_calls == [{"period": "5d", "interval": "1h"}]


def test_info_quote_returns_ticker_info_dict(monkeypatch):
    fake = FakeTicker("AAPL", info={"shortName": "Apple Inc.", "sector": "Technology"})
    monkeypatch.setattr("yfinance_api.endpoints.info.yf.Ticker", lambda ticker: fake)

    client = YFinanceClient()
    out = client.info.quote("AAPL")

    assert out == {"shortName": "Apple Inc.", "sector": "Technology"}


def test_info_fast_info_returns_plain_dict(monkeypatch):
    fake = FakeTicker("AAPL", fast_info=FakeFastInfo(lastPrice=200.0, marketCap=3_000_000_000))
    monkeypatch.setattr("yfinance_api.endpoints.info.yf.Ticker", lambda ticker: fake)

    client = YFinanceClient()
    out = client.info.fast_info("AAPL")

    assert out == {"lastPrice": 200.0, "marketCap": 3_000_000_000}
    assert type(out) is dict
