"""Shared base for FMP API namespaces (`client.economics`, `client.commodity`, ...)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..client import FMPClient


class Endpoint:
    """Base class for an FMP API category namespace.

    Subclasses expose one method per concrete endpoint, each calling
    `self._request(path, params)`. FMP uses a single API key for every
    endpoint (unlike BOT's per-product keys), so there's no `key_attr`
    indirection — every namespace just resolves `self._client.api_key`.
    """

    def __init__(self, client: "FMPClient"):
        self._client = client

    def _resolve_key(self) -> str:
        if not self._client.api_key:
            raise ValueError(
                "FMP API key not set: pass api_key= to FMPClient() or set "
                "FMP_API_KEY (see .env.example)"
            )
        return self._client.api_key

    def _request(
        self, path: str, params: dict, return_json: bool = False
    ) -> pd.DataFrame | list | dict:
        self._resolve_key()
        payload = self._client.get(path, params=params)
        if return_json:
            return payload
        return self._client.to_dataframe(payload)
