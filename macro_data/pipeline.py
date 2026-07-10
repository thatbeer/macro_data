"""Update orchestration: catalog -> fetchers -> store, with per-series error isolation."""

import logging
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from . import store
from .catalog import SeriesConfig, load_catalog
from .sources.bot import BotSource
from .sources.fred import FredSource
from .sources.worldbank import WorldBankSource
from .sources.yahoo import YahooSource

load_dotenv()

logger = logging.getLogger("macro_data")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "catalog.yaml"
DATA_DIR = PROJECT_ROOT / "data"

SOURCES = {
    cls.name: cls for cls in (YahooSource, FredSource, WorldBankSource, BotSource)
}


def list_series(catalog_path=None) -> list[SeriesConfig]:
    return load_catalog(catalog_path or CATALOG_PATH)


def load(series_id: str, catalog_path=None, data_dir=None) -> pd.DataFrame:
    for cfg in list_series(catalog_path):
        if cfg.id == series_id:
            return store.load(data_dir or DATA_DIR, cfg.source, series_id)
    raise KeyError(f"series '{series_id}' not found in catalog")


def update_all(catalog_path=None, data_dir=None) -> dict[str, str]:
    return _run(list_series(catalog_path), data_dir or DATA_DIR)


def update(source_name: str, catalog_path=None, data_dir=None) -> dict[str, str]:
    selected = [c for c in list_series(catalog_path) if c.source == source_name]
    return _run(selected, data_dir or DATA_DIR)


def _run(configs: list[SeriesConfig], data_dir: Path) -> dict[str, str]:
    results: dict[str, str] = {}
    instances = {}
    for cfg in configs:
        try:
            if cfg.source not in SOURCES:
                raise KeyError(f"unknown source '{cfg.source}'")
            if cfg.source not in instances:
                instances[cfg.source] = SOURCES[cfg.source]()
            results[cfg.id] = _update_series(instances[cfg.source], cfg, data_dir)
        except Exception as exc:  # noqa: BLE001 - one bad series must not stop the rest
            logger.warning("series %s failed: %s", cfg.id, exc)
            results[cfg.id] = f"failed: {exc}"
    return results


def _update_series(source, cfg: SeriesConfig, data_dir: Path) -> str:
    last = store.last_date(data_dir, cfg.source, cfg.id)
    start = None if last is None else last + pd.Timedelta(days=1)
    new = source.fetch(cfg, start=start)
    added = store.append(data_dir, cfg.source, cfg.id, new)
    return f"updated ({added} rows)" if added else "up-to-date"
