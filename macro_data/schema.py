"""Canonical series schema: date-indexed DataFrame with one float 'value' column."""

import pandas as pd


class SchemaError(ValueError):
    """Raised when a fetcher result cannot be coerced into the canonical schema."""


def empty() -> pd.DataFrame:
    idx = pd.DatetimeIndex([], name="date")
    return pd.DataFrame({"value": pd.Series([], dtype="float64")}, index=idx)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a raw fetcher result (columns 'date' and 'value') into the canonical frame.

    Sorts by date, drops rows with non-numeric values, keeps the last row for
    duplicate dates, and strips any timezone.
    """
    missing = {"date", "value"} - set(df.columns)
    if missing:
        raise SchemaError(f"missing required column(s): {sorted(missing)}")

    out = df[["date", "value"]].copy()
    out["date"] = pd.to_datetime(out["date"])
    if isinstance(out["date"].dtype, pd.DatetimeTZDtype):
        out["date"] = out["date"].dt.tz_localize(None)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["date", "value"])
    out = out.drop_duplicates(subset="date", keep="last").sort_values("date")
    out = out.set_index("date")
    out["value"] = out["value"].astype("float64")
    return out
