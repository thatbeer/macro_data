from pathlib import Path

import pytest

from macro_data.catalog import load_catalog

from bigquery_categories import CATEGORY_BY_SERIES, category_for


def test_category_for_known_series():
    assert category_for("usd_thb") == "fx"
    assert category_for("gold_usd") == "commodities"
    assert category_for("us_10y_yield") == "rates"
    assert category_for("us_cpi") == "macro"
    assert category_for("sp500") == "equities"


def test_category_for_unknown_series_raises():
    with pytest.raises(KeyError, match="no_such_series"):
        category_for("no_such_series")


def test_every_bot_yahoo_fred_catalog_series_has_a_category():
    catalog_path = Path(__file__).resolve().parent.parent / "catalog.yaml"
    configs = load_catalog(catalog_path)
    missing = [
        c.id
        for c in configs
        if c.source in ("bot", "yahoo", "fred") and c.id not in CATEGORY_BY_SERIES
    ]
    assert missing == []
