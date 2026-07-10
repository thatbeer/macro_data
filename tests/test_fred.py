import pandas as pd
import pytest

from macro_data.catalog import SeriesConfig
from macro_data.sources.base import MissingKeyError
from macro_data.sources.fred import FredSource

CFG = SeriesConfig(id="us_cpi", source="fred", params={"series": "CPIAUCSL"})


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_parses_observations(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(
            {
                "observations": [
                    {"date": "2024-01-01", "value": "308.417"},
                    {"date": "2024-02-01", "value": "."},  # FRED missing marker
                    {"date": "2024-03-01", "value": "312.332"},
                ]
            }
        )

    monkeypatch.setattr("macro_data.sources.fred.requests.get", fake_get)
    out = FredSource().fetch(CFG)
    assert captured["params"]["series_id"] == "CPIAUCSL"
    assert captured["params"]["api_key"] == "test-key"
    assert "observation_start" not in captured["params"]
    assert len(out) == 2  # "." row dropped
    assert out.loc[pd.Timestamp("2024-03-01"), "value"] == 312.332


def test_fetch_incremental_sets_observation_start(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return FakeResponse({"observations": []})

    monkeypatch.setattr("macro_data.sources.fred.requests.get", fake_get)
    out = FredSource().fetch(CFG, start=pd.Timestamp("2024-04-01"))
    assert captured["params"]["observation_start"] == "2024-04-01"
    assert out.empty


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(MissingKeyError, match="FRED_API_KEY"):
        FredSource().fetch(CFG)
