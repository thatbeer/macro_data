"""Synthetic sample shaped like the forecast_assets BigQuery view (see
forecasting/market_data_forecast_view.sql), for smoke-testing the forecast
config's dataset/keys mapping without live BigQuery data."""

from pathlib import Path

import numpy as np
import pandas as pd

DOMAIN_BASE_PRICE_RANGE = {
    "fx_rates": (1.0, 40.0),
    "commodity_futures": (20.0, 2000.0),
    "bars_ohlcv": (50.0, 5000.0),
}


def generate_synthetic_assets(
    n_assets_per_domain: int = 5,
    start: str = "2023-01-01",
    end: str = "2026-07-22",
    seed: int = 42,
) -> pd.DataFrame:
    """Returns a DataFrame with columns (catalog_id, date, value, domain_table) --
    one random-walk price series per synthetic asset, one row per domain per asset
    per date."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start, end=end, freq="D")

    frames = []
    for domain, (low, high) in DOMAIN_BASE_PRICE_RANGE.items():
        for i in range(n_assets_per_domain):
            base_price = rng.uniform(low, high)
            daily_returns = rng.normal(loc=0.0002, scale=0.01, size=len(dates))
            prices = base_price * np.cumprod(1 + daily_returns)
            frames.append(
                pd.DataFrame(
                    {
                        "catalog_id": f"{domain}_synth_{i:02d}",
                        "date": dates,
                        "value": prices,
                        "domain_table": domain,
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    df = generate_synthetic_assets()
    out_path = Path(__file__).parent / "data" / "synthetic_forecast_assets.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"wrote {len(df)} rows ({df['catalog_id'].nunique()} assets) to {out_path}")


if __name__ == "__main__":
    main()
