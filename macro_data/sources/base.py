"""Source interface: every fetcher returns the canonical schema."""

from abc import ABC, abstractmethod

import pandas as pd

from ..catalog import SeriesConfig


class MissingKeyError(RuntimeError):
    """An API key env var required by a source is not set."""

    def __init__(self, env_var: str):
        super().__init__(
            f"environment variable {env_var} is not set "
            f"(put it in a .env file, see .env.example)"
        )
        self.env_var = env_var


class BaseSource(ABC):
    name: str = ""

    @abstractmethod
    def fetch(self, cfg: SeriesConfig, start: pd.Timestamp | None = None) -> pd.DataFrame:
        """Return canonical rows for cfg with date >= start (full history if start is None)."""
