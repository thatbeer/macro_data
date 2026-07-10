import pandas as pd

from macro_data.catalog import SeriesConfig
from macro_data.sources.worldbank import WorldBankSource

CFG = SeriesConfig(
    id="th_gdp_usd",
    source="worldbank",
    params={"indicator": "NY.GDP.MKTP.CD", "country": "THA"},
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _payload():
    meta = {"page": 1, "pages": 1, "total": 3}
    rows = [
        {"date": "2023", "value": 514969611656.0},
        {"date": "2022", "value": 495645559519.0},
        {"date": "2021", "value": None},  # not yet reported
    ]
    return [meta, rows]


def test_fetch_parses_yearly_rows(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(_payload())

    monkeypatch.setattr("macro_data.sources.worldbank.requests.get", fake_get)
    out = WorldBankSource().fetch(CFG)
    assert "THA" in captured["url"] and "NY.GDP.MKTP.CD" in captured["url"]
    assert captured["params"]["format"] == "json"
    assert len(out) == 2  # None value dropped
    assert out.index[0] == pd.Timestamp("2022-01-01")  # years parse to Jan 1, sorted


def test_fetch_incremental_filters_client_side(monkeypatch):
    monkeypatch.setattr(
        "macro_data.sources.worldbank.requests.get",
        lambda url, params=None, timeout=None: FakeResponse(_payload()),
    )
    out = WorldBankSource().fetch(CFG, start=pd.Timestamp("2023-01-01"))
    assert list(out.index) == [pd.Timestamp("2023-01-01")]


def test_fetch_no_data(monkeypatch):
    monkeypatch.setattr(
        "macro_data.sources.worldbank.requests.get",
        lambda url, params=None, timeout=None: FakeResponse([{"total": 0}]),
    )
    out = WorldBankSource().fetch(CFG)
    assert out.empty
