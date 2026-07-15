"""Standalone client for FRED's REST API (api.stlouisfed.org), beyond the single
series/observations call already in macro_data/sources/fred.py.

Reuses the same FRED_API_KEY env var. Adds series discovery — search by text,
series metadata, the categories/tags a series belongs to — so notebooks can
find and pull any FRED series without a catalog.yaml entry first.

Note: FRED wraps each endpoint's response under a different key
(`observations`, `seriess` — FRED's real, double-s key name for series-info-
shaped responses, `categories`, `tags`); `SeriesEndpoint` handles this
per-method, it isn't uniform the way `fmp_api`'s flat-list responses are.

Usage::

    fred = FREDClient()  # reads FRED_API_KEY from the environment
    fred.series.observations("GNPCA", from_date, to_date)
    fred.series.info("GNPCA")
    fred.series.search("money stock")
    fred.series.categories("GNPCA")
    fred.series.tags("GNPCA")
"""

from .client import FREDClient

__all__ = ["FREDClient"]
