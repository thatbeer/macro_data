import pandas as pd
import pytest

from macro_data import schema


def test_normalize_sorts_dedups_and_indexes():
    df = pd.DataFrame(
        {
            "date": ["2024-01-03", "2024-01-01", "2024-01-03"],
            "value": ["3.0", "1.0", "3.5"],
        }
    )
    out = schema.normalize(df)
    assert out.index.name == "date"
    assert list(out.columns) == ["value"]
    assert out.index.is_monotonic_increasing
    # duplicate date keeps the last occurrence
    assert out.loc[pd.Timestamp("2024-01-03"), "value"] == 3.5
    assert out["value"].dtype == "float64"


def test_normalize_drops_non_numeric_values():
    df = pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "value": ["1.5", "."]})
    out = schema.normalize(df)
    assert len(out) == 1


def test_normalize_strips_timezone():
    idx = pd.to_datetime(["2024-01-01", "2024-01-02"]).tz_localize("UTC")
    df = pd.DataFrame({"date": idx, "value": [1.0, 2.0]})
    out = schema.normalize(df)
    assert out.index.tz is None


def test_normalize_missing_columns_raises():
    with pytest.raises(schema.SchemaError):
        schema.normalize(pd.DataFrame({"date": ["2024-01-01"]}))


def test_empty_frame_is_canonical():
    out = schema.empty()
    assert out.index.name == "date"
    assert list(out.columns) == ["value"]
    assert len(out) == 0
