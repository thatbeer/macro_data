import pandas as pd
import pytest

from macro_data import pipeline, schema, store
from macro_data.catalog import SeriesConfig
from macro_data.sources.base import BaseSource

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
        rows = [("2024-01-01", 1.0), ("2024-01-02", 2.0)]
        if start is not None:
            rows = [(d, v) for d, v in rows if pd.Timestamp(d) >= start]
        return schema.normalize(pd.DataFrame(rows, columns=["date", "value"]))


class FakeBadSource(BaseSource):
    name = "fake_bad"

    def fetch(self, cfg, start=None):
        raise RuntimeError("api exploded")


@pytest.fixture
def env(tmp_path, monkeypatch):
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(CATALOG, encoding="utf-8")
    monkeypatch.setitem(pipeline.SOURCES, "fake_ok", FakeOkSource)
    monkeypatch.setitem(pipeline.SOURCES, "fake_bad", FakeBadSource)
    return {"catalog_path": catalog_path, "data_dir": tmp_path / "data"}


def test_update_all_isolates_failures(env):
    result = pipeline.update_all(**env)
    assert result["ok_series"] == "updated (2 rows)"
    assert result["ok_series_2"] == "updated (2 rows)"
    assert result["bad_series"].startswith("failed:")
    assert "api exploded" in result["bad_series"]
    # the good series really got written despite the bad one
    assert len(store.load(env["data_dir"], "fake_ok", "ok_series")) == 2


def test_update_all_is_incremental(env):
    pipeline.update_all(**env)
    result = pipeline.update_all(**env)  # second run: nothing new
    assert result["ok_series"] == "up-to-date"


def test_update_single_source(env):
    result = pipeline.update("fake_ok", **env)
    assert set(result) == {"ok_series", "ok_series_2"}


def test_update_unknown_source_in_catalog(env):
    (env["catalog_path"]).write_text(
        "series:\n  - {id: x, source: no_such_source}\n", encoding="utf-8"
    )
    result = pipeline.update_all(**env)
    assert result["x"].startswith("failed:")


def test_load_by_series_id(env):
    pipeline.update_all(**env)
    df = pipeline.load("ok_series", **env)
    assert list(df["value"]) == [1.0, 2.0]


def test_load_unknown_series_raises(env):
    with pytest.raises(KeyError, match="nope"):
        pipeline.load("nope", **env)


def test_public_api_exports():
    import macro_data

    for fn in ("update_all", "update", "load", "list_series"):
        assert callable(getattr(macro_data, fn))
