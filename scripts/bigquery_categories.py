"""series_id -> BigQuery staging category lookup.

Only series with source in {bot, yahoo, fred} need an entry here --
World Bank series are out of scope for the BigQuery loader.
"""

CATEGORY_BY_SERIES = {
    # --- fx ---
    "usd_thb": "fx",
    "eur_usd": "fx",
    "usd_dxy": "fx",
    "eur_thb": "fx",
    "jpy_thb": "fx",
    "gbp_thb": "fx",
    "usd_thb_bot": "fx",
    # --- commodities ---
    "gold_usd": "commodities",
    "brent_oil": "commodities",
    "wti_oil": "commodities",
    "silver_usd": "commodities",
    "copper_usd": "commodities",
    "natural_gas": "commodities",
    # --- rates ---
    "us_3m_yield": "rates",
    "us_5y_yield": "rates",
    "us_10y_yield": "rates",
    "us_30y_yield": "rates",
    # --- macro ---
    "fed_funds_rate": "macro",
    "us_cpi": "macro",
    # --- equities ---
    "sp500": "equities",
    "set_index": "equities",
}


def category_for(series_id: str) -> str:
    """Return the BigQuery staging category for series_id.

    Raises KeyError if series_id has no mapping -- a new catalog series
    with an in-scope source must be added here explicitly, it should
    never silently drop out of the BigQuery loader.
    """
    try:
        return CATEGORY_BY_SERIES[series_id]
    except KeyError:
        raise KeyError(
            f"no BigQuery category mapped for series '{series_id}' "
            f"(add it to CATEGORY_BY_SERIES in bigquery_categories.py)"
        ) from None
