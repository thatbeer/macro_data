import pandas as pd
import pytest

from fmp_api import FMPClient

CAPTURED = {}
PAYLOADS = {}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def fake_get(url, params=None, timeout=None):
    CAPTURED.update(url=url, params=params)
    path = url.rsplit("/", 1)[-1]
    return FakeResponse(PAYLOADS.get(path, []))


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    CAPTURED.clear()
    PAYLOADS.clear()
    monkeypatch.setattr("fmp_api.client.requests.get", fake_get)
    yield


def test_client_reads_key_from_env(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "key-123")
    client = FMPClient()
    assert client.api_key == "key-123"


def test_client_construction_never_raises_without_key(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    client = FMPClient()
    assert client.api_key is None


def test_get_sends_apikey_query_param():
    client = FMPClient(api_key="key-123")
    client.get("treasury-rates", params={"from": "2024-01-01"})
    assert CAPTURED["url"] == "https://financialmodelingprep.com/stable/treasury-rates"
    assert CAPTURED["params"] == {"from": "2024-01-01", "apikey": "key-123"}


def test_to_dataframe_handles_list_payload():
    df = FMPClient.to_dataframe([{"a": 1}, {"a": 2}])
    assert list(df["a"]) == [1, 2]


def test_to_dataframe_handles_single_dict_payload():
    df = FMPClient.to_dataframe({"a": 1})
    assert list(df["a"]) == [1]


def test_missing_key_raises_on_namespace_call(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    client = FMPClient()
    with pytest.raises(ValueError, match="FMP_API_KEY"):
        client.economics.treasury_rates()


@pytest.mark.parametrize(
    "method_name, path, extra_kwargs, expected_params",
    [
        ("calendar", "economics-calendar", {"from_date": "2024-01-01", "to_date": "2024-01-31"}, {"from": "2024-01-01", "to": "2024-01-31"}),
        ("indicators", "economics-indicators", {"name": "GDP"}, {"name": "GDP"}),
        ("market_risk_premium", "market-risk-premium", {}, {}),
        ("treasury_rates", "treasury-rates", {"from_date": "2024-01-01", "to_date": "2024-01-31"}, {"from": "2024-01-01", "to": "2024-01-31"}),
    ],
)
def test_economics_namespace_builds_correct_request(method_name, path, extra_kwargs, expected_params):
    PAYLOADS[path] = [{"date": "2024-01-02", "year10": 4.5}]
    client = FMPClient(api_key="key-123")
    method = getattr(client.economics, method_name)

    out = method(**extra_kwargs)

    assert CAPTURED["url"] == f"https://financialmodelingprep.com/stable/{path}"
    assert CAPTURED["params"] == {**expected_params, "apikey": "key-123"}
    assert list(out["year10"]) == [4.5]


def test_economics_return_json_gives_raw_payload():
    PAYLOADS["treasury-rates"] = [{"date": "2024-01-02", "year10": 4.5}]
    client = FMPClient(api_key="key-123")
    out = client.economics.treasury_rates(return_json=True)
    assert out == [{"date": "2024-01-02", "year10": 4.5}]


@pytest.mark.parametrize(
    "method_name, path, call_kwargs, expected_params",
    [
        ("list", "commodities-list", {}, {}),
        ("quote", "commodities-quote", {"symbol": "GCUSD"}, {"symbol": "GCUSD"}),
        ("quote_short", "commodities-quote-short", {"symbol": "GCUSD"}, {"symbol": "GCUSD"}),
        ("all_quotes", "all-commodities-quotes", {}, {}),
        (
            "historical_eod_full",
            "commodities-historical-price-eod-full",
            {"symbol": "GCUSD", "from_date": "2024-01-01", "to_date": "2024-01-31"},
            {"symbol": "GCUSD", "from": "2024-01-01", "to": "2024-01-31"},
        ),
        (
            "historical_eod_light",
            "commodities-historical-price-eod-light",
            {"symbol": "GCUSD"},
            {"symbol": "GCUSD"},
        ),
        ("intraday_1min", "commodities-intraday-1-min", {"symbol": "GCUSD"}, {"symbol": "GCUSD"}),
        ("intraday_5min", "commodities-intraday-5-min", {"symbol": "GCUSD"}, {"symbol": "GCUSD"}),
        ("intraday_1hour", "commodities-intraday-1-hour", {"symbol": "GCUSD"}, {"symbol": "GCUSD"}),
    ],
)
def test_commodity_namespace_builds_correct_request(method_name, path, call_kwargs, expected_params):
    PAYLOADS[path] = [{"symbol": "GCUSD", "price": 2400.0}]
    client = FMPClient(api_key="key-123")
    method = getattr(client.commodity, method_name)

    out = method(**call_kwargs)

    assert CAPTURED["url"] == f"https://financialmodelingprep.com/stable/{path}"
    assert CAPTURED["params"] == {**expected_params, "apikey": "key-123"}
    assert list(out["price"]) == [2400.0]


@pytest.mark.parametrize(
    "method_name, path, call_kwargs, expected_params",
    [
        ("list", "forex-list", {}, {}),
        ("quote", "forex-quote", {"symbol": "EURUSD"}, {"symbol": "EURUSD"}),
        ("quote_short", "forex-quote-short", {"symbol": "EURUSD"}, {"symbol": "EURUSD"}),
        ("all_quotes", "all-forex-quotes", {}, {}),
        (
            "historical_eod_full",
            "forex-historical-price-eod-full",
            {"symbol": "EURUSD", "from_date": "2024-01-01", "to_date": "2024-01-31"},
            {"symbol": "EURUSD", "from": "2024-01-01", "to": "2024-01-31"},
        ),
        (
            "historical_eod_light",
            "forex-historical-price-eod-light",
            {"symbol": "EURUSD"},
            {"symbol": "EURUSD"},
        ),
        ("intraday_1min", "forex-intraday-1-min", {"symbol": "EURUSD"}, {"symbol": "EURUSD"}),
        ("intraday_5min", "forex-intraday-5-min", {"symbol": "EURUSD"}, {"symbol": "EURUSD"}),
        ("intraday_1hour", "forex-intraday-1-hour", {"symbol": "EURUSD"}, {"symbol": "EURUSD"}),
    ],
)
def test_forex_namespace_builds_correct_request(method_name, path, call_kwargs, expected_params):
    PAYLOADS[path] = [{"symbol": "EURUSD", "price": 1.09}]
    client = FMPClient(api_key="key-123")
    method = getattr(client.forex, method_name)

    out = method(**call_kwargs)

    assert CAPTURED["url"] == f"https://financialmodelingprep.com/stable/{path}"
    assert CAPTURED["params"] == {**expected_params, "apikey": "key-123"}
    assert list(out["price"]) == [1.09]
