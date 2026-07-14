"""Policy Rate service (PolicyRate) -> `client.policy_rate`."""

from __future__ import annotations

import pandas as pd

from .base import Endpoint


class PolicyRateEndpoint(Endpoint):
    service = "PolicyRate/v3"
    key_attr = "interest_key"

    def current(self, return_json: bool = False) -> pd.DataFrame | dict:
        """Current policy rate and latest MPC announcement (`/policy_rate/`).

        Unlike every other endpoint on this client, the live API ignores
        start_period/end_period and always returns the current rate — so
        this method takes no date arguments.
        """
        api_key = self._resolve_key()
        payload = self._client.get(f"{self.service}/policy_rate/", params={}, api_key=api_key)
        if return_json:
            return payload
        result = payload.get("result", {})
        return pd.DataFrame(
            [
                {
                    "rate": result.get("data"),
                    "announcement_date": result.get("announcement_date"),
                    "effective_datetime": result.get("effective_datetime"),
                    "news_text_en": result.get("news_text_en"),
                    "news_text_th": result.get("news_text_th"),
                }
            ]
        )
