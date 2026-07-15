"""Shared base for yfinance_api namespaces (`client.history`, `client.info`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import YFinanceClient


class Endpoint:
    """Base class for a yfinance_api namespace.

    Kept for structural consistency with bot_api/fmp_api/fred_api even
    though there's no key resolution needed here — yfinance requires no
    API key.
    """

    def __init__(self, client: "YFinanceClient"):
        self._client = client
