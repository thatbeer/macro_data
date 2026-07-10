import pandas as pd

from macro_data.catalog import SeriesConfig
from macro_data.sources.yahoo import YahooSource

CFG = SeriesConfig(id="usd_thb", source="yahoo", params={"ticker": "THB=X"})


def _fake_download(rows):
    """Build a yfinance-shaped result: DatetimeIndex + MultiIndex columns."""
    idx = pd.to_datetime([d for d, _ in rows])
    cols = pd.MultiIndex.from_tuples([("Close", "THB=X")])
    return pd.DataFrame([[v] for _, v in rows], index=idx, columns=cols)


def test_fetch_full_history(monkeypatch):
    captured = {}

    def fake(ticker, **kwargs):
        captured.update(kwargs, ticker=ticker)
        return _fake_download([("2024-01-01", 34.5), ("2024-01-02", 34.6)])

    monkeypatch.setattr("macro_data.sources.yahoo.yf.download", fake)
    out = YahooSource().fetch(CFG)
    assert captured["ticker"] == "THB=X"
    assert captured["period"] == "max"
    assert list(out["value"]) == [34.5, 34.6]
    assert out.index.name == "date"


def test_fetch_incremental_passes_start(monkeypatch):
    captured = {}

    def fake(ticker, **kwargs):
        captured.update(kwargs)
        return _fake_download([("2024-01-03", 34.7)])

    monkeypatch.setattr("macro_data.sources.yahoo.yf.download", fake)
    out = YahooSource().fetch(CFG, start=pd.Timestamp("2024-01-03"))
    assert captured["start"] == "2024-01-03"
    assert len(out) == 1


def test_fetch_empty_result(monkeypatch):
    monkeypatch.setattr(
        "macro_data.sources.yahoo.yf.download", lambda *a, **k: pd.DataFrame()
    )
    out = YahooSource().fetch(CFG)
    assert out.empty
    assert out.index.name == "date"
