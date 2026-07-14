"""Standalone client for the Bank of Thailand Open Data API (gateway.api.bot.or.th).

Kept outside the `macro_data` package on purpose: `macro_data.sources.bot` talks to
BOT's older `apigw1.bot.or.th` gateway (auth via `X-IBM-Client-Id`) through the
catalog/schema/store pipeline. This client targets the newer `gateway.api.bot.or.th`
gateway (auth via a raw `Authorization` header) for ad-hoc, notebook-driven queries
that don't need to land in the CSV store.

BOT's developer portal issues a separate subscription key per API product, so
`BOTClient` resolves three independent keys — `BOT_CLIENT_ID` (exchange +
reference_rate), `BOT_CLIENT_ID_INTEREST` (interest, thb_implied_rate,
external_interest_rate, deposit_rate, spot_rate, swap_point,
interbank_txn_rate, bibor, policy_rate — all under BOT's "Interest Rates"
plan), and `BOT_CLIENT_ID_BOND_AUCTION` (bond_auction) — each optional at
construction time and only required when its namespace is actually called.

Usage::

    bot = BOTClient()  # reads all three keys from the environment
    bot.exchange.daily(start_period, end_period)
    bot.interest.daily(start_period, end_period)
    bot.bond_auction.auction(start_period, end_period)
    bot.reference_rate.daily(start_period, end_period)
    bot.thb_implied_rate.daily(start_period, end_period)
    bot.external_interest_rate.daily(start_period, end_period)
    bot.deposit_rate.daily(start_period, end_period)
    bot.spot_rate.daily(start_period, end_period)
    bot.swap_point.daily(start_period, end_period)
    bot.interbank_txn_rate.daily(start_period, end_period)
    bot.bibor.daily(start_period, end_period)
    bot.policy_rate.current()
"""

from .client import BOTClient

__all__ = ["BOTClient"]
