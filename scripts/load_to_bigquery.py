"""Fetch BOT/Yahoo/FRED series directly from their APIs and load them into
BigQuery staging tables, independent of macro_data's local CSV store.

Usage: python scripts/load_to_bigquery.py
Requires GCP_PROJECT and BQ_DATASET in the environment (see .env.example).
"""

import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

from macro_data.catalog import load_catalog
from macro_data.sources.bot import BotSource
from macro_data.sources.fred import FredSource
from macro_data.sources.yahoo import YahooSource

from bigquery_categories import category_for
from bigquery_load import load_category_table
from bigquery_transform import annotate, group_by_category

load_dotenv()

logger = logging.getLogger("load_to_bigquery")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "catalog.yaml"

SOURCES = {"yahoo": YahooSource, "fred": FredSource, "bot": BotSource}


def run(catalog_path=None, client=None, project=None, dataset=None) -> dict:
    project = project or os.environ.get("GCP_PROJECT")
    if not project:
        raise RuntimeError(
            "GCP_PROJECT is not set (put it in a .env file, see .env.example)"
        )
    dataset = dataset or os.environ.get("BQ_DATASET")
    if not dataset:
        raise RuntimeError(
            "BQ_DATASET is not set (put it in a .env file, see .env.example)"
        )

    configs = [c for c in load_catalog(catalog_path or CATALOG_PATH) if c.source in SOURCES]
    loaded_at = pd.Timestamp.now(tz="UTC")

    fetch_status: dict[str, str] = {}
    annotated: list[pd.DataFrame] = []
    instances = {}
    for cfg in configs:
        try:
            category = category_for(cfg.id)
            if cfg.source not in instances:
                instances[cfg.source] = SOURCES[cfg.source]()
            raw = instances[cfg.source].fetch(cfg, start=None)
            frame = annotate(cfg, category, raw, loaded_at)
            annotated.append(frame)
            fetch_status[cfg.id] = f"fetched ({len(frame)} rows)"
        except Exception as exc:  # noqa: BLE001 - one bad series must not stop the rest
            logger.warning("series %s failed: %s", cfg.id, exc)
            fetch_status[cfg.id] = f"failed: {exc}"

    by_category = group_by_category(annotated)

    if client is None:
        client = bigquery.Client(project=project)

    load_status: dict[str, str] = {}
    for category, df in by_category.items():
        try:
            rows = load_category_table(client, project, dataset, category, df)
            load_status[category] = f"loaded ({rows} rows)"
        except Exception as exc:  # noqa: BLE001 - one bad table must not stop the rest
            logger.warning("category %s failed to load: %s", category, exc)
            load_status[category] = f"failed: {exc}"

    return {"fetch": fetch_status, "load": load_status}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run()
    for series_id, status in result["fetch"].items():
        print(f"[fetch] {series_id}: {status}")
    for category, status in result["load"].items():
        print(f"[load] {category}: {status}")
