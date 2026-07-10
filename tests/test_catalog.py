import pytest

from macro_data import catalog


def _write(tmp_path, text):
    p = tmp_path / "catalog.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_catalog_parses_entries_and_params(tmp_path):
    p = _write(
        tmp_path,
        """
series:
  - id: usd_thb
    source: yahoo
    ticker: "THB=X"
    name: "USD/THB exchange rate"
  - id: us_cpi
    source: fred
    series: CPIAUCSL
""",
    )
    entries = catalog.load_catalog(p)
    assert [e.id for e in entries] == ["usd_thb", "us_cpi"]
    assert entries[0].source == "yahoo"
    assert entries[0].name == "USD/THB exchange rate"
    assert entries[0].params == {"ticker": "THB=X"}
    assert entries[1].params == {"series": "CPIAUCSL"}
    assert entries[1].name == ""


def test_missing_required_key_raises(tmp_path):
    p = _write(tmp_path, "series:\n  - id: oops\n")
    with pytest.raises(catalog.CatalogError, match="source"):
        catalog.load_catalog(p)


def test_duplicate_id_raises(tmp_path):
    p = _write(
        tmp_path,
        """
series:
  - {id: dup, source: yahoo, ticker: A}
  - {id: dup, source: fred, series: B}
""",
    )
    with pytest.raises(catalog.CatalogError, match="dup"):
        catalog.load_catalog(p)


def test_empty_or_malformed_catalog_raises(tmp_path):
    p = _write(tmp_path, "not_series: []\n")
    with pytest.raises(catalog.CatalogError):
        catalog.load_catalog(p)
