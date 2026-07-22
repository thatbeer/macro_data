"""Pure transform: a source's normalized fetch DataFrame -> BigQuery-ready rows.

No I/O, no BigQuery dependency -- validation itself already happened inside
BaseSource.fetch() via schema.normalize().
"""

import pandas as pd

from macro_data.catalog import SeriesConfig


def annotate(
    cfg: SeriesConfig, category: str, raw: pd.DataFrame, loaded_at: pd.Timestamp
) -> pd.DataFrame:
    """raw is the normalized (date-indexed, 'value' column) frame from BaseSource.fetch().

    Returns a flat frame with columns:
    series_id, source, name, category, date, value, loaded_at.
    """
    out = raw.reset_index()[["date", "value"]].copy()
    out["series_id"] = cfg.id
    out["source"] = cfg.source
    out["name"] = cfg.name
    out["category"] = category
    out["date"] = out["date"].dt.date
    out["loaded_at"] = loaded_at
    return out[["series_id", "source", "name", "category", "date", "value", "loaded_at"]]


def group_by_category(frames: list[pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Concatenate annotated frames and split by category.

    Output frames drop the 'category' column (redundant once split into a
    per-category dict -- the dict key already encodes it) and keep exactly:
    series_id, source, name, date, value, loaded_at -- matching
    bigquery_load.SCHEMA.
    """
    if not frames:
        return {}
    combined = pd.concat(frames, ignore_index=True)
    return {
        category: group.drop(columns="category").reset_index(drop=True)
        for category, group in combined.groupby("category")
    }
