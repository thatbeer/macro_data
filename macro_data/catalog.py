"""Declarative series catalog loaded from catalog.yaml."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class CatalogError(ValueError):
    """Raised when catalog.yaml is malformed."""


_KNOWN_KEYS = {"id", "source", "name"}


@dataclass(frozen=True)
class SeriesConfig:
    id: str
    source: str
    name: str = ""
    params: dict = field(default_factory=dict)


def load_catalog(path: Path) -> list[SeriesConfig]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("series"), list):
        raise CatalogError(f"{path}: expected a top-level 'series' list")

    entries: list[SeriesConfig] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw["series"]):
        if not isinstance(entry, dict):
            raise CatalogError(f"{path}: series[{i}] is not a mapping")
        for key in ("id", "source"):
            if key not in entry:
                raise CatalogError(f"{path}: series[{i}] missing required key '{key}'")
        if entry["id"] in seen:
            raise CatalogError(f"{path}: duplicate series id '{entry['id']}'")
        seen.add(entry["id"])
        params = {k: v for k, v in entry.items() if k not in _KNOWN_KEYS}
        entries.append(
            SeriesConfig(
                id=entry["id"],
                source=entry["source"],
                name=entry.get("name", ""),
                params=params,
            )
        )
    return entries
