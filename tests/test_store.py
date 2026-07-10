import pandas as pd
import pytest

from macro_data import schema, store


def _frame(pairs):
    df = pd.DataFrame(pairs, columns=["date", "value"])
    return schema.normalize(df)


def test_append_then_load_round_trip(tmp_path):
    new = _frame([("2024-01-01", 1.0), ("2024-01-02", 2.0)])
    added = store.append(tmp_path, "yahoo", "usd_thb", new)
    assert added == 2
    out = store.load(tmp_path, "yahoo", "usd_thb")
    pd.testing.assert_frame_equal(out, new)


def test_append_is_incremental_and_dedups(tmp_path):
    store.append(tmp_path, "yahoo", "usd_thb", _frame([("2024-01-01", 1.0), ("2024-01-02", 2.0)]))
    # overlap on 01-02 with a revised value: incoming wins
    added = store.append(
        tmp_path, "yahoo", "usd_thb", _frame([("2024-01-02", 2.5), ("2024-01-03", 3.0)])
    )
    assert added == 1  # only 01-03 is net new
    out = store.load(tmp_path, "yahoo", "usd_thb")
    assert len(out) == 3
    assert out.loc[pd.Timestamp("2024-01-02"), "value"] == 2.5


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        store.load(tmp_path, "yahoo", "nope")


def test_last_date(tmp_path):
    assert store.last_date(tmp_path, "fred", "us_cpi") is None
    store.append(tmp_path, "fred", "us_cpi", _frame([("2024-01-01", 1.0), ("2024-02-01", 2.0)]))
    assert store.last_date(tmp_path, "fred", "us_cpi") == pd.Timestamp("2024-02-01")


def test_append_empty_frame_is_noop(tmp_path):
    added = store.append(tmp_path, "fred", "us_cpi", schema.empty())
    assert added == 0
    assert store.last_date(tmp_path, "fred", "us_cpi") is None
