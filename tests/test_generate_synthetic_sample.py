import pandas as pd

from generate_synthetic_sample import generate_synthetic_assets


def test_generate_synthetic_assets_shape():
    df = generate_synthetic_assets(n_assets_per_domain=3, start="2024-01-01", end="2024-01-31", seed=1)

    assert list(df.columns) == ["catalog_id", "date", "value", "domain_table"]
    assert df["catalog_id"].nunique() == 9  # 3 domains * 3 assets
    assert set(df["domain_table"].unique()) == {"fx_rates", "commodity_futures", "bars_ohlcv"}
    assert df["value"].notna().all()
    assert (df["value"] > 0).all()
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_generate_synthetic_assets_deterministic():
    df1 = generate_synthetic_assets(seed=7)
    df2 = generate_synthetic_assets(seed=7)
    pd.testing.assert_frame_equal(df1, df2)


def test_generate_synthetic_assets_date_range():
    df = generate_synthetic_assets(n_assets_per_domain=1, start="2024-01-01", end="2024-01-05", seed=1)
    one_series = df[df["catalog_id"] == "fx_rates_synth_00"]
    assert len(one_series) == 5
    assert one_series["date"].min() == pd.Timestamp("2024-01-01")
    assert one_series["date"].max() == pd.Timestamp("2024-01-05")
