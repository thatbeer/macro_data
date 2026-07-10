"""Macro data store: fetch economics data into local CSVs, load into pandas.

Usage:
    from macro_data import update_all, load
    update_all()
    df = load("usd_thb")
"""

from .pipeline import list_series, load, update, update_all

__all__ = ["update_all", "update", "load", "list_series"]
