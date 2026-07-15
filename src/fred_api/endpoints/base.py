"""Shared base for FRED API namespaces (`client.series`, ...)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..client import FREDClient


class Endpoint:
    """Base class for a FRED API section namespace.

    Unlike FMP's uniform flat-list responses, FRED wraps each endpoint's
    result under a different top-level key (`observations`, `seriess`,
    `categories`, `tags`) — so `_request()` takes that key explicitly per
    call rather than assuming one shape for the whole client.
    """

    def __init__(self, client: "FREDClient"):
        self._client = client

    def _resolve_key(self) -> str:
        if not self._client.api_key:
            raise ValueError(
                "FRED API key not set: pass api_key= to FREDClient() or set "
                "FRED_API_KEY (see .env.example)"
            )
        return self._client.api_key

    def _request(
        self, path: str, params: dict, response_key: str, return_json: bool = False
    ) -> pd.DataFrame | dict:
        self._resolve_key()
        payload = self._client.get(path, params)
        if return_json:
            return payload
        return self._client.to_dataframe(payload, response_key)
