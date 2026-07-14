import pandas as pd
import pytest

from bot_api import BOTClient

CAPTURED = {}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _exchange_payload():
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


def _interest_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {"period": "2024-01-02", "bank_name_eng": "Bangkok Bank", "mlr": "6.9"},
                ]
            },
        }
    }


def _debt_payload():
    return {
        "result": {
            "api": "Bond Auction",
            "timestamp": "2017-10-03 08:53:51",
            "data": {
                "data_detail": [
                    {
                        "auction_date": "2017-09-26",
                        "debt_securities_type": "Government Bonds",
                        "thaibma_symbol": "LB233A",
                        "coupon_rate": "5.5",
                        "weighted_average_accepted_yield": "1.7077000",
                    },
                ]
            },
        }
    }


def _reference_rate_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {"period": "2024-01-02", "rate": "34.5"},
                    {"period": "2024-01-03", "rate": "34.6"},
                ]
            },
        }
    }


def fake_get(url, headers=None, params=None, timeout=None):
    CAPTURED.update(url=url, headers=headers, params=params)
    if "LoanRate" in url:
        return FakeResponse(_interest_payload())
    if "BondAuction" in url:
        return FakeResponse(_debt_payload())
    if "Stat-ReferenceRate" in url:
        return FakeResponse(_reference_rate_payload())
    return FakeResponse(_exchange_payload())


@pytest.fixture(autouse=True)
def _reset_captured():
    CAPTURED.clear()
    yield


@pytest.fixture(autouse=True)
def _patch_requests(monkeypatch):
    monkeypatch.setattr("bot_api.client.requests.get", fake_get)


@pytest.mark.parametrize(
    "attr, env_var",
    [
        ("api_key", "BOT_CLIENT_ID"),
        ("interest_key", "BOT_CLIENT_ID_INTEREST"),
        ("bond_auction_key", "BOT_CLIENT_ID_BOND_AUCTION"),
    ],
)
def test_client_reads_keys_from_env(monkeypatch, attr, env_var):
    monkeypatch.setenv(env_var, "client-123")
    client = BOTClient()
    assert getattr(client, attr) == "client-123"


def test_client_construction_never_raises_without_keys(monkeypatch):
    for env_var in ["BOT_CLIENT_ID", "BOT_CLIENT_ID_INTEREST", "BOT_CLIENT_ID_BOND_AUCTION"]:
        monkeypatch.delenv(env_var, raising=False)
    client = BOTClient()
    assert client.api_key is None
    assert client.interest_key is None
    assert client.bond_auction_key is None


def test_client_get_sends_authorization_header():
    client = BOTClient(api_key="client-123")
    client.get("Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/", params={"currency": "USD"})
    assert CAPTURED["headers"] == {"Authorization": "client-123", "Accept": "application/json"}
    assert CAPTURED["url"] == (
        "https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/"
    )


@pytest.mark.parametrize(
    "method_name, endpoint",
    [
        ("daily", "DAILY_AVG_EXG_RATE"),
        ("monthly", "MONTHLY_AVG_EXG_RATE"),
        ("quarterly", "QUARTERLY_AVG_EXG_RATE"),
        ("annual", "ANNUAL_AVG_EXG_RATE"),
    ],
)
def test_exchange_namespace_builds_correct_path(method_name, endpoint):
    bot = BOTClient(api_key="client-123")
    method = getattr(bot.exchange, method_name)

    out = method("2024-01-01", "2024-01-31", currency="USD")

    assert CAPTURED["url"] == f"https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/{endpoint}/"
    assert CAPTURED["params"] == {
        "start_period": "2024-01-01",
        "end_period": "2024-01-31",
        "currency": "USD",
    }
    assert list(out["mid_rate"]) == ["34.5", "34.6"]


def test_exchange_return_json_gives_raw_payload():
    bot = BOTClient(api_key="client-123")
    out = bot.exchange.daily("2024-01-01", "2024-01-31", return_json=True)
    assert out["result"]["success"] is True


def test_interest_namespace_builds_correct_path():
    bot = BOTClient(api_key="client-123")
    out = bot.interest.daily("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == "https://gateway.api.bot.or.th/LoanRate/v2/loan_rate/"
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["mlr"]) == ["6.9"]


def test_interest_avg_loan_rate_builds_correct_path():
    bot = BOTClient(api_key="client-123")
    out = bot.interest.avg_loan_interest("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == "https://gateway.api.bot.or.th/LoanRate/v2/avg_loan_rate/"
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["mlr"]) == ["6.9"]


def test_bond_auction_namespace_builds_correct_path():
    bot = BOTClient(api_key="client-123")
    out = bot.bond_auction.auction("2017-01-01", "2017-12-31")

    assert CAPTURED["url"] == "https://gateway.api.bot.or.th/BondAuction/bond_auction_v2/"
    assert CAPTURED["params"] == {"start_period": "2017-01-01", "end_period": "2017-12-31"}
    assert list(out["thaibma_symbol"]) == ["LB233A"]
    assert out["auction_date"].iloc[0] == pd.Timestamp("2017-09-26")


def test_bond_auction_return_json_gives_raw_payload():
    bot = BOTClient(api_key="client-123")
    out = bot.bond_auction.auction("2017-01-01", "2017-12-31", return_json=True)
    assert out["result"]["api"] == "Bond Auction"


@pytest.mark.parametrize(
    "method_name, endpoint",
    [
        ("daily", "DAILY_REF_RATE"),
        ("monthly", "MONTHLY_REF_RATE"),
        ("quarterly", "QUARTERLY_REF_RATE"),
        ("annual", "ANNUAL_REF_RATE"),
    ],
)
def test_reference_rate_namespace_builds_correct_path(method_name, endpoint):
    bot = BOTClient(api_key="client-123")
    method = getattr(bot.reference_rate, method_name)

    out = method("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == f"https://gateway.api.bot.or.th/Stat-ReferenceRate/v2/{endpoint}/"
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["rate"]) == ["34.5", "34.6"]


def test_reference_rate_return_json_gives_raw_payload():
    bot = BOTClient(api_key="client-123")
    out = bot.reference_rate.daily("2024-01-01", "2024-01-31", return_json=True)
    assert out["result"]["success"] is True
