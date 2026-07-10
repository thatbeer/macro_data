"""Bank of Thailand API fetcher. Needs free client id: https://apiportal.bot.or.th"""

import os

import pandas as pd
import requests

from .. import schema
from ..catalog import SeriesConfig
from .base import BaseSource, MissingKeyError

DEFAULT_START = "2000-01-01"


class BotSource(BaseSource):
    name = "bot"

    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        client_id = os.environ.get("BOT_CLIENT_ID")
        if not client_id:
            raise MissingKeyError("BOT_CLIENT_ID")

        params = dict(cfg.params.get("query", {}))
        params["start_period"] = (
            start.strftime("%Y-%m-%d") if start is not None else DEFAULT_START
        )
        params["end_period"] = pd.Timestamp.today().strftime("%Y-%m-%d")

        resp = requests.get(
            cfg.params["url"],
            params=params,
            headers={"X-IBM-Client-Id": client_id},
            timeout=30,
        )
        resp.raise_for_status()
        detail = (
            resp.json().get("result", {}).get("data", {}).get("data_detail", []) or []
        )
        if not detail:
            return schema.empty()
        date_field = cfg.params.get("date_field", "period")
        value_field = cfg.params["value_field"]
        df = pd.DataFrame(detail).rename(
            columns={date_field: "date", value_field: "value"}
        )
        return schema.normalize(df)
