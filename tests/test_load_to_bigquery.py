import pandas as pd
import pytest

from macro_data import schema
from macro_data.sources.base import BaseSource

import load_to_bigquery

CATALOG = """
series:
  - id: ok_series
    source: fake_ok
    name: "always works"
  - id: bad_series
    source: fake_bad
  - id: ok_series_2
    source: fake_ok
"""


class FakeOkSource(BaseSource):
    name = "fake_ok"

    def fetch(self, cfg, start=None):
        return schema.normalize(
            pd.DataFrame(
                [("2024-01-01", 1.0), ("2024-01-02", 2.0)], columns=["date", "value"]
            )
        )


class FakeBadSource(BaseSource):
    name = "fake_bad"

    def fetch(self, cfg, start=None):
        raise RuntimeError("api exploded")


@pytest.fixture
def env(tmp_path, monkeypatch):
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(CATALOG, encoding="utf-8")
    monkeypatch.setitem(load_to_bigquery.SOURCES, "fake_ok", FakeOkSource)
    monkeypatch.setitem(load_to_bigquery.SOURCES, "fake_bad", FakeBadSource)
    monkeypatch.setenv("GCP_PROJECT", "proj")
    monkeypatch.setenv("BQ_DATASET", "ds")
    return {"catalog_path": catalog_path}


def test_run_isolates_fetch_failures_and_loads_by_category(env, monkeypatch):
    monkeypatch.setattr(load_to_bigquery, "category_for", lambda series_id: "fx")
    calls = []

    def fake_load_category_table(client, project, dataset, category, df):
        calls.append((category, len(df)))
        return len(df)

    monkeypatch.setattr(load_to_bigquery, "load_category_table", fake_load_category_table)

    result = load_to_bigquery.run(catalog_path=env["catalog_path"], client=object())

    assert result["fetch"]["ok_series"] == "fetched (2 rows)"
    assert result["fetch"]["ok_series_2"] == "fetched (2 rows)"
    assert result["fetch"]["bad_series"].startswith("failed:")
    assert "api exploded" in result["fetch"]["bad_series"]
    assert result["load"]["fx"] == "loaded (4 rows)"
    assert calls == [("fx", 4)]


def test_run_load_failure_does_not_block_other_categories(env, monkeypatch):
    monkeypatch.setattr(
        load_to_bigquery,
        "category_for",
        lambda series_id: "fx" if series_id == "ok_series" else "commodities",
    )

    def flaky_load(client, project, dataset, category, df):
        if category == "commodities":
            raise RuntimeError("bigquery exploded")
        return len(df)

    monkeypatch.setattr(load_to_bigquery, "load_category_table", flaky_load)

    result = load_to_bigquery.run(catalog_path=env["catalog_path"], client=object())

    assert result["load"]["fx"] == "loaded (2 rows)"
    assert result["load"]["commodities"].startswith("failed:")
    assert "bigquery exploded" in result["load"]["commodities"]


def test_run_missing_gcp_project_raises(env, monkeypatch):
    monkeypatch.delenv("GCP_PROJECT")
    with pytest.raises(RuntimeError, match="GCP_PROJECT"):
        load_to_bigquery.run(catalog_path=env["catalog_path"])


def test_run_missing_bq_dataset_raises(env, monkeypatch):
    monkeypatch.delenv("BQ_DATASET")
    with pytest.raises(RuntimeError, match="BQ_DATASET"):
        load_to_bigquery.run(catalog_path=env["catalog_path"])
