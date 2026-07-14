"""Standalone client for the Bank of Thailand Open Data API (gateway.api.bot.or.th).

Kept outside the `macro_data` package on purpose: `macro_data.sources.bot` talks to
BOT's older `apigw1.bot.or.th` gateway (auth via `X-IBM-Client-Id`) through the
catalog/schema/store pipeline. This client targets the newer `gateway.api.bot.or.th`
gateway (auth via a raw `Authorization` header) for ad-hoc, notebook-driven queries
that don't need to land in the CSV store.

BOT's developer portal issues a separate subscription key per API product, so
`BOTClient` resolves three independent keys — `BOT_CLIENT_ID` (exchange +
reference_rate), `BOT_CLIENT_ID_INTEREST` (interest), and
`BOT_CLIENT_ID_BOND_AUCTION` (bond_auction) — each optional at construction time
and only required when its namespace is actually called.

Usage::

    bot = BOTClient()  # reads all three keys from the environment
    bot.exchange.daily(start_period, end_period)
    bot.interest.daily(start_period, end_period)
    bot.bond_auction.auction(start_period, end_period)
    bot.reference_rate.daily(start_period, end_period)
"""

from .client import BOTClient

__all__ = ["BOTClient"]
