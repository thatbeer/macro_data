"""Series section (series, series/observations, series/search, ...) -> `client.series`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class SeriesEndpoint(Endpoint):
    def observations(
        self,
        series_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
        return_json: bool = False,
    ) -> pd.DataFrame | dict:
        """Observed values for a series (`/series/observations`)."""
        params: dict = {"series_id": series_id}
        if from_date:
            params["observation_start"] = from_date
        if to_date:
            params["observation_end"] = to_date
        return self._request("series/observations", params, "observations", return_json)

    def info(self, series_id: str, return_json: bool = False) -> pd.DataFrame | dict:
        """Metadata for a series — title, units, frequency, ... (`/series`)."""
        return self._request("series", {"series_id": series_id}, "seriess", return_json)

    def search(self, search_text: str, return_json: bool = False) -> pd.DataFrame | dict:
        """Full-text search across FRED's series catalog (`/series/search`)."""
        return self._request("series/search", {"search_text": search_text}, "seriess", return_json)

    def categories(self, series_id: str, return_json: bool = False) -> pd.DataFrame | dict:
        """Categories a series belongs to (`/series/categories`)."""
        return self._request("series/categories", {"series_id": series_id}, "categories", return_json)

    def tags(self, series_id: str, return_json: bool = False) -> pd.DataFrame | dict:
        """Tags attached to a series (`/series/tags`)."""
        return self._request("series/tags", {"series_id": series_id}, "tags", return_json)
