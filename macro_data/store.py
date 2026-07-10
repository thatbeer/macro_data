"""CSV persistence: one file per series at <data_dir>/<source>/<series_id>.csv."""

import os
from pathlib import Path

import pandas as pd

from . import schema


def path_for(data_dir: Path, source: str, series_id: str) -> Path:
    return Path(data_dir) / source / f"{series_id}.csv"


def load(data_dir: Path, source: str, series_id: str) -> pd.DataFrame:
    path = path_for(data_dir, source, series_id)
    if not path.exists():
        raise FileNotFoundError(f"no data for series '{series_id}' at {path}")
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    df["value"] = df["value"].astype("float64")
    return df


def last_date(data_dir: Path, source: str, series_id: str):
    try:
        df = load(data_dir, source, series_id)
    except FileNotFoundError:
        return None
    return None if df.empty else df.index.max()


def append(data_dir: Path, source: str, series_id: str, new: pd.DataFrame) -> int:
    """Merge new rows into the series file. Incoming values win on duplicate dates.

    Returns the number of net new rows (dates not previously stored).
    """
    if new.empty:
        return 0
    try:
        existing = load(data_dir, source, series_id)
    except FileNotFoundError:
        existing = schema.empty()

    combined = pd.concat([existing, new])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()

    path = path_for(data_dir, source, series_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    combined.to_csv(tmp, date_format="%Y-%m-%d")
    os.replace(tmp, path)  # atomic on the same filesystem, including Windows
    return len(combined) - len(existing)
