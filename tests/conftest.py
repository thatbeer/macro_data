import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
FORECASTING = ROOT / "forecasting"
for path in (SRC, FORECASTING):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
