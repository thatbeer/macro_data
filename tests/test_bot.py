import pandas as pd
import pytest

from macro_data.catalog import SeriesConfig
from macro_data.sources.base import MissingKeyError
from macro_data.sources.bot import BotSource

CFG = SeriesConfig(
    id="usd_thb_bot",
    source="bot",
    params={
        "url": "https://apigw1.bot.or.th/bot/public/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/",
        "value_field": "mid_rate",
        "query": {"currency": "USD"},
    },
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {"period": "2024-01-02", "currency_id": "USD", "mid_rate": "34.5"},
                    {"period": "2024-01-03", "currency_id": "USD", "mid_rate": "34.6"},
                ]
            },
        }
    }


def test_fetch_parses_data_detail(monkeypatch):
    monkeypatch.setenv("BOT_CLIENT_ID", "client-123")
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured.update(url=url, params=params, headers=headers)
        return FakeResponse(_payload())

    monkeypatch.setattr("macro_data.sources.bot.requests.get", fake_get)
    out = BotSource().fetch(CFG, start=pd.Timestamp("2024-01-01"))
    assert captured["url"] == CFG.params["url"]
    assert captured["headers"] == {"X-IBM-Client-Id": "client-123"}
    assert captured["params"]["currency"] == "USD"
    assert captured["params"]["start_period"] == "2024-01-01"
    assert "end_period" in captured["params"]
    assert list(out["value"]) == [34.5, 34.6]


def test_fetch_default_start(monkeypatch):
    monkeypatch.setenv("BOT_CLIENT_ID", "client-123")
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["params"] = params
        return FakeResponse(_payload())

    monkeypatch.setattr("macro_data.sources.bot.requests.get", fake_get)
    BotSource().fetch(CFG)
    assert captured["params"]["start_period"] == "2000-01-01"


def test_fetch_empty_detail(monkeypatch):
    monkeypatch.setenv("BOT_CLIENT_ID", "client-123")
    monkeypatch.setattr(
        "macro_data.sources.bot.requests.get",
        lambda url, params=None, headers=None, timeout=None: FakeResponse(
            {"result": {"success": True, "data": {"data_detail": []}}}
        ),
    )
    out = BotSource().fetch(CFG)
    assert out.empty


def test_missing_client_id_raises(monkeypatch):
    monkeypatch.delenv("BOT_CLIENT_ID", raising=False)
    with pytest.raises(MissingKeyError, match="BOT_CLIENT_ID"):
        BotSource().fetch(CFG)
