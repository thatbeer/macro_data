import pandas as pd

from macro_data import schema
from macro_data.catalog import SeriesConfig

from bigquery_transform import annotate, group_by_category


def _raw(rows):
    return schema.normalize(pd.DataFrame(rows, columns=["date", "value"]))


def test_annotate_adds_metadata_columns():
    cfg = SeriesConfig(id="usd_thb", source="yahoo", name="USD/THB exchange rate")
    raw = _raw([("2024-01-01", 35.1), ("2024-01-02", 35.2)])
    loaded_at = pd.Timestamp("2026-07-22T00:00:00Z")

    out = annotate(cfg, "fx", raw, loaded_at)

    assert list(out.columns) == [
        "series_id", "source", "name", "category", "date", "value", "loaded_at",
    ]
    assert len(out) == 2
    assert (out["series_id"] == "usd_thb").all()
    assert (out["source"] == "yahoo").all()
    assert (out["name"] == "USD/THB exchange rate").all()
    assert (out["category"] == "fx").all()
    assert (out["loaded_at"] == loaded_at).all()
    assert out["date"].tolist() == [
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-01-02").date(),
    ]
    assert out["value"].tolist() == [35.1, 35.2]


def test_group_by_category_splits_and_drops_category_column():
    cfg_fx = SeriesConfig(id="usd_thb", source="yahoo", name="USD/THB")
    cfg_gold = SeriesConfig(id="gold_usd", source="yahoo", name="Gold")
    loaded_at = pd.Timestamp("2026-07-22T00:00:00Z")
    fx_frame = annotate(cfg_fx, "fx", _raw([("2024-01-01", 35.1)]), loaded_at)
    commodities_frame = annotate(
        cfg_gold, "commodities", _raw([("2024-01-01", 2000.0)]), loaded_at
    )

    grouped = group_by_category([fx_frame, commodities_frame])

    assert set(grouped) == {"fx", "commodities"}
    assert list(grouped["fx"].columns) == [
        "series_id", "source", "name", "date", "value", "loaded_at",
    ]
    assert grouped["fx"]["series_id"].tolist() == ["usd_thb"]
    assert grouped["commodities"]["series_id"].tolist() == ["gold_usd"]


def test_group_by_category_empty_list_returns_empty_dict():
    assert group_by_category([]) == {}
