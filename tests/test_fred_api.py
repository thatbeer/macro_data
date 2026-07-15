import pandas as pd
import pytest

from fred_api import FREDClient

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
    path = url.rsplit("fred/", 1)[-1]
    return FakeResponse(PAYLOADS.get(path, {}))


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    CAPTURED.clear()
    PAYLOADS.clear()
    monkeypatch.setattr("fred_api.client.requests.get", fake_get)
    yield


def test_client_reads_key_from_env(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "key-123")
    client = FREDClient()
    assert client.api_key == "key-123"


def test_client_construction_never_raises_without_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    client = FREDClient()
    assert client.api_key is None


def test_missing_key_raises_on_namespace_call(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    client = FREDClient()
    with pytest.raises(ValueError, match="FRED_API_KEY"):
        client.series.observations("GNPCA")


def test_observations_builds_correct_request():
    PAYLOADS["series/observations"] = {
        "observations": [
            {"date": "2024-01-01", "value": "34.5"},
            {"date": "2024-01-02", "value": "34.6"},
        ]
    }
    client = FREDClient(api_key="key-123")

    out = client.series.observations("GNPCA", from_date="2024-01-01", to_date="2024-01-31")

    assert CAPTURED["url"] == "https://api.stlouisfed.org/fred/series/observations"
    assert CAPTURED["params"] == {
        "series_id": "GNPCA",
        "observation_start": "2024-01-01",
        "observation_end": "2024-01-31",
        "api_key": "key-123",
        "file_type": "json",
    }
    assert list(out["value"]) == ["34.5", "34.6"]


def test_observations_omits_unset_dates():
    PAYLOADS["series/observations"] = {"observations": [{"date": "2024-01-01", "value": "34.5"}]}
    client = FREDClient(api_key="key-123")
    client.series.observations("GNPCA")
    assert CAPTURED["params"] == {"series_id": "GNPCA", "api_key": "key-123", "file_type": "json"}


def test_observations_return_json_gives_raw_payload():
    PAYLOADS["series/observations"] = {"observations": [{"date": "2024-01-01", "value": "34.5"}]}
    client = FREDClient(api_key="key-123")
    out = client.series.observations("GNPCA", return_json=True)
    assert out == {"observations": [{"date": "2024-01-01", "value": "34.5"}]}


def test_info_builds_correct_request_and_uses_seriess_key():
    PAYLOADS["series"] = {"seriess": [{"id": "GNPCA", "title": "Real Gross National Product"}]}
    client = FREDClient(api_key="key-123")

    out = client.series.info("GNPCA")

    assert CAPTURED["url"] == "https://api.stlouisfed.org/fred/series"
    assert CAPTURED["params"] == {"series_id": "GNPCA", "api_key": "key-123", "file_type": "json"}
    assert list(out["title"]) == ["Real Gross National Product"]


def test_search_builds_correct_request_and_uses_seriess_key():
    PAYLOADS["series/search"] = {"seriess": [{"id": "GNPCA", "title": "Real Gross National Product"}]}
    client = FREDClient(api_key="key-123")

    out = client.series.search("money stock")

    assert CAPTURED["url"] == "https://api.stlouisfed.org/fred/series/search"
    assert CAPTURED["params"] == {
        "search_text": "money stock",
        "api_key": "key-123",
        "file_type": "json",
    }
    assert list(out["id"]) == ["GNPCA"]


def test_categories_builds_correct_request():
    PAYLOADS["series/categories"] = {"categories": [{"id": 18, "name": "Exports"}]}
    client = FREDClient(api_key="key-123")

    out = client.series.categories("GNPCA")

    assert CAPTURED["url"] == "https://api.stlouisfed.org/fred/series/categories"
    assert CAPTURED["params"] == {"series_id": "GNPCA", "api_key": "key-123", "file_type": "json"}
    assert list(out["name"]) == ["Exports"]


def test_tags_builds_correct_request():
    PAYLOADS["series/tags"] = {"tags": [{"name": "gnp", "group_id": "gen"}]}
    client = FREDClient(api_key="key-123")

    out = client.series.tags("GNPCA")

    assert CAPTURED["url"] == "https://api.stlouisfed.org/fred/series/tags"
    assert CAPTURED["params"] == {"series_id": "GNPCA", "api_key": "key-123", "file_type": "json"}
    assert list(out["name"]) == ["gnp"]
