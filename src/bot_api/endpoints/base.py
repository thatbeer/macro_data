"""Shared base for BOT API service namespaces (`client.exchange`, `client.interest`, ...)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..client import BOTClient

_ENV_VAR_BY_KEY_ATTR = {
    "api_key": "BOT_CLIENT_ID",
    "interest_key": "BOT_CLIENT_ID_INTEREST",
    "bond_auction_key": "BOT_CLIENT_ID_BOND_AUCTION",
}


class Endpoint:
    """Base class for a BOT API service namespace.

    Subclasses set `service` (the path segment before the endpoint name, e.g.
    `"Stat-ExchangeRate/v2"`) and `key_attr` (which `BOTClient` attribute holds
    the subscription key for this service's product — defaults to `"api_key"`),
    and expose one method per concrete endpoint, each calling
    `self._request(endpoint, params)`. A namespace whose response isn't a
    `data_detail` time series (e.g. `PolicyRateEndpoint`) can call
    `self._resolve_key()` directly instead of `self._request()`.
    """

    service: str = ""
    key_attr: str = "api_key"

    def __init__(self, client: "BOTClient"):
        self._client = client

    def _resolve_key(self) -> str:
        api_key = getattr(self._client, self.key_attr)
        if not api_key:
            env_var = _ENV_VAR_BY_KEY_ATTR[self.key_attr]
            raise ValueError(
                f"BOT API key not set for '{self.service}': pass {self.key_attr}= to "
                f"BOTClient() or set {env_var} (see .env.example)"
            )
        return api_key

    def _request(
        self,
        endpoint: str,
        params: dict,
        return_json: bool = False,
        date_field: str = "period",
    ) -> pd.DataFrame | dict:
        api_key = self._resolve_key()
        payload = self._client.get(f"{self.service}/{endpoint}/", params=params, api_key=api_key)
        if return_json:
            return payload
        return self._client.to_dataframe(payload, date_field=date_field)
