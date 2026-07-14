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


def _thb_implied_rate_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {
                        "period": "2024-01-02",
                        "rate_type_name_th": "อัตราดอกเบี้ยโดยนัย",
                        "rate_type_name_eng": "Onshore",
                        "interest_rate": "2.50",
                    },
                ]
            },
        }
    }


def _external_interest_rate_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {
                        "period": "2024-01-02",
                        "rate_type_name_th": "อัตราดอกเบี้ยต่างประเทศ",
                        "rate_type_name_eng": "SOFR",
                        "interest_rate": "5.31",
                    },
                ]
            },
        }
    }


def _deposit_rate_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {
                        "period": "2024-01-02",
                        "bank_type_name_th": "ธนาคารพาณิชย์จดทะเบียนในประเทศ",
                        "bank_type_name_eng": "Thai Commercial Banks",
                        "bank_name_th": "ธนาคารกรุงเทพ",
                        "bank_name_eng": "Bangkok Bank",
                        "saving_min": "0.25",
                        "saving_max": "0.50",
                        "fix_3_mths_min": "0.90",
                        "fix_3_mths_max": "1.15",
                        "fix_6_mths_min": "1.05",
                        "fix_6_mths_max": "1.30",
                        "fix_12_mths_min": "1.35",
                        "fix_12_mths_max": "1.60",
                        "fix_24_mths_min": "1.40",
                        "fix_24_mths_max": "1.65",
                    },
                ]
            },
        }
    }


def _spot_rate_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {"period": "2024-01-02", "bid_rate": "34.50", "offer_rate": "34.55"},
                ]
            },
        }
    }


def _swap_point_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {
                        "period": "2024-01-02",
                        "term_type_name_th": "1 สัปดาห์",
                        "term_type_name_eng": "1 Week",
                        "bid_rate": "0.50",
                        "offer_rate": "0.60",
                    },
                ]
            },
        }
    }


def _interbank_transaction_rate_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {
                        "period": "2024-01-02",
                        "term_type_name_th": "ข้ามคืน",
                        "term_type_name_eng": "Overnight",
                        "min_interest_rate": "1.20",
                        "max_interest_rate": "1.30",
                        "mode_interest_rate": "1.25",
                        "weighted_average_interest_rate": "1.24",
                    },
                ]
            },
        }
    }


def _bibor_payload():
    return {
        "result": {
            "success": True,
            "data": {
                "data_detail": [
                    {
                        "period": "2024-01-02",
                        "bankname_th": "ธนาคารกรุงเทพ จำกัด (มหาชน)",
                        "bankname_eng": "Bangkok Bank",
                        "bibor_o_n": "2.50000",
                        "bibor_1_week": "2.52000",
                        "bibor_1_month": "2.55000",
                        "bibor_2_month": "2.60000",
                        "bibor_3_month": "2.65000",
                        "bibor_6_month": "2.75000",
                        "bibor_9_month": "",
                        "bibor_1_year": "2.85000",
                    },
                ]
            },
        }
    }


def fake_get(url, headers=None, params=None, timeout=None):
    CAPTURED.update(url=url, headers=headers, params=params)
    if "Stat-ThaiBahtImpliedInterestRate" in url:
        return FakeResponse(_thb_implied_rate_payload())
    if "Stat-ExternalInterestRate" in url:
        return FakeResponse(_external_interest_rate_payload())
    if "DepositRate" in url:
        return FakeResponse(_deposit_rate_payload())
    if "Stat-SpotRate" in url:
        return FakeResponse(_spot_rate_payload())
    if "Stat-SwapPoint" in url:
        return FakeResponse(_swap_point_payload())
    if "Stat-InterbankTransactionRate" in url:
        return FakeResponse(_interbank_transaction_rate_payload())
    if "BIBOR" in url:
        return FakeResponse(_bibor_payload())
    raise AssertionError(f"unexpected URL in test: {url}")


@pytest.fixture(autouse=True)
def _reset_captured():
    CAPTURED.clear()
    yield


@pytest.fixture(autouse=True)
def _patch_requests(monkeypatch):
    monkeypatch.setattr("bot_api.client.requests.get", fake_get)


def test_thb_implied_rate_builds_correct_path():
    bot = BOTClient(interest_key="client-123")
    out = bot.thb_implied_rate.daily("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == (
        "https://gateway.api.bot.or.th/Stat-ThaiBahtImpliedInterestRate/v2/THB_IMPL_INT_RATE/"
    )
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["interest_rate"]) == ["2.50"]


def test_external_interest_rate_builds_correct_path():
    bot = BOTClient(interest_key="client-123")
    out = bot.external_interest_rate.daily("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == "https://gateway.api.bot.or.th/Stat-ExternalInterestRate/v2/EXT_INT_RATE/"
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["interest_rate"]) == ["5.31"]


def test_deposit_rate_builds_correct_path():
    bot = BOTClient(interest_key="client-123")
    out = bot.deposit_rate.daily("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == "https://gateway.api.bot.or.th/DepositRate/v2/deposit_rate/"
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["saving_min"]) == ["0.25"]


def test_spot_rate_builds_correct_path():
    bot = BOTClient(interest_key="client-123")
    out = bot.spot_rate.daily("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == "https://gateway.api.bot.or.th/Stat-SpotRate/v2/SPOTRATE/"
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["bid_rate"]) == ["34.50"]


def test_swap_point_builds_correct_path():
    bot = BOTClient(interest_key="client-123")
    out = bot.swap_point.daily("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == "https://gateway.api.bot.or.th/Stat-SwapPoint/v2/SWAPPOINT/"
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["bid_rate"]) == ["0.50"]


def test_interbank_transaction_rate_builds_correct_path():
    bot = BOTClient(interest_key="client-123")
    out = bot.interbank_txn_rate.daily("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == (
        "https://gateway.api.bot.or.th/Stat-InterbankTransactionRate/v2/INTRBNK_TXN_RATE/"
    )
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    assert list(out["weighted_average_interest_rate"]) == ["1.24"]


def test_bibor_builds_correct_path():
    bot = BOTClient(interest_key="client-123")
    out = bot.bibor.daily("2024-01-01", "2024-01-31")

    assert CAPTURED["url"] == "https://gateway.api.bot.or.th/BIBOR/v2/bibor_rate/"
    assert CAPTURED["params"] == {"start_period": "2024-01-01", "end_period": "2024-01-31"}
    # column confirmed present in Step 1's real live response
    assert list(out["bibor_1_month"]) == ["2.55000"]
