# World Bank GEP Forecast Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone Jupyter notebook that queries World Bank Global
Economic Prospects (GEP) GDP growth forecasts for Thailand, the US, and the
World aggregate, and saves them to CSV.

**Architecture:** A single notebook calls the World Bank REST API directly
via `requests` (source `27`, indicator `NYGDPMKTPKDZ`), builds a tidy
DataFrame, plots the three trajectories, and writes the result to
`data/worldbank_gep/gdp_growth_forecast.csv`. No changes to the `macro_data`
package — this bypasses `catalog.yaml`/`pipeline.py`/`store.py` entirely, per
the design spec's scope-boundary decision.

**Tech Stack:** `pandas`, `requests`, `matplotlib` (all already project
dependencies — no new packages).

## Global Constraints

- Design spec: `docs/superpowers/specs/2026-07-16-worldbank-gep-forecast-notebook-design.md`
- Endpoint: `https://api.worldbank.org/v2/country/{codes}/indicator/NYGDPMKTPKDZ?source=27&format=json`
- Country codes: `THA`, `USA`, `1T` (World Bank's aggregate code for "World
  (WBG members)" — not ISO3 `WLD`, which returns nothing under this source)
- No changes to `macro_data/sources/worldbank.py`, `catalog.yaml`, or
  `store.py`
- Notebooks in this repo are committed only after being executed end-to-end
  (`jupyter nbconvert --to notebook --execute --inplace`), per CLAUDE.md

---

### Task 1: Build and execute the GEP forecast notebook

**Files:**
- Create: `notebooks/worldbank_gep_forecast.ipynb`

**Interfaces:**
- Consumes: nothing from other tasks (first and only task)
- Produces: `data/worldbank_gep/gdp_growth_forecast.csv` (a run artifact, not
  consumed by any other code)

- [ ] **Step 1: Create the notebook with all cells**

Create `notebooks/worldbank_gep_forecast.ipynb` as a notebook (kernel
`macro-data-venv`, matching every other notebook in `notebooks/`) with the
following cells in order.

Markdown cell 1:

```markdown
# World Bank Global Economic Prospects — GDP Growth Forecasts

The `macro_data` package's pipeline (`catalog.yaml` → `pipeline.py` →
`store.py`) assumes every series is a growing history of actuals, fetched
incrementally from `store.last_date() + 1 day` onward. World Bank's
**Global Economic Prospects (GEP)** data is the opposite: a small, fully
revised forecast vintage published a couple of times a year, where old
"forecast" years get overwritten by the next vintage rather than extended.
Forcing it through `normalize()`/`append()` would misrepresent revisions as
new history — so, like `fx_ohlcv_query.ipynb` does for OHLCV bars, this
notebook queries the API directly and stays outside the canonical store.

GEP data lives in World Bank DataBank **source 27**, reachable through the
same `api.worldbank.org/v2` endpoint the project's `worldbank` source
already calls — just with `source=27` instead of the default WDI source
(`2`). It has exactly one indicator, `NYGDPMKTPKDZ` ("GDP growth, constant
2010-19 prices"), covering 2023–2028 with every row flagged as a forecast
(`obs_status == "F"`).

Sections:
1. Fetching GEP forecasts
2. Confirming these are forecast values
3. Comparing GDP growth trajectories
4. Saving the snapshot to CSV
```

Code cell 2:

```python
import pandas as pd
import requests
import matplotlib.pyplot as plt
from pathlib import Path

pd.set_option("display.max_rows", 20)
%matplotlib inline

GEP_URL = "https://api.worldbank.org/v2/country/{codes}/indicator/NYGDPMKTPKDZ"


def fetch_gep_forecast(country_codes: list[str]) -> pd.DataFrame:
    """Query World Bank Global Economic Prospects (source=27) GDP growth forecasts."""
    resp = requests.get(
        GEP_URL.format(codes=";".join(country_codes)),
        params={"source": 27, "format": "json", "per_page": 200},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    rows = payload[1] if len(payload) > 1 and payload[1] else []
    df = pd.DataFrame(
        {
            "country": r["country"]["value"],
            "year": int(r["date"]),
            "value": r["value"],
            "obs_status": r["obs_status"],
        }
        for r in rows
    )
    return df.sort_values(["country", "year"]).reset_index(drop=True)
```

Markdown cell 3:

```markdown
## 1. Fetching GEP forecasts

Thailand (`THA`), the United States (`USA`), and the World aggregate
(`1T` — World Bank's own code for "World (WBG members)"; the ISO3 code
`WLD` used elsewhere in this project returns nothing under source 27).
```

Code cell 4:

```python
forecast = fetch_gep_forecast(["THA", "USA", "1T"])
forecast
```

Markdown cell 5:

```markdown
## 2. Confirming these are forecast values

Every row in this dataset — including years that have already
passed — carries `obs_status == "F"`, because GEP publishes a fully
model-based vintage rather than mixing in reported actuals.
```

Code cell 6:

```python
forecast["obs_status"].unique()
```

Markdown cell 7:

```markdown
## 3. Comparing GDP growth trajectories

Thailand, the US, and the World aggregate, 2023–2028.
```

Code cell 8:

```python
pivot = forecast.pivot(index="year", columns="country", values="value")

fig, ax = plt.subplots(figsize=(9, 5))
pivot.plot(ax=ax, marker="o", title="GDP growth forecast, 2023–2028 (World Bank Global Economic Prospects)")
ax.set_ylabel("GDP growth (%)")
ax.set_xlabel("Year")
plt.show()
```

Markdown cell 9:

```markdown
## 4. Saving the snapshot to CSV

This is a forecast vintage, not a growing history of actuals, so it's saved
to its own folder — `data/worldbank_gep/` — separate from `data/worldbank/`,
which holds the actuals fetched through the canonical `worldbank` source.
```

Code cell 10:

```python
gep_dir = Path("..") / "data" / "worldbank_gep"
gep_dir.mkdir(parents=True, exist_ok=True)
forecast.to_csv(gep_dir / "gdp_growth_forecast.csv", index=False)

sorted(p.name for p in gep_dir.glob("*.csv"))
```

- [ ] **Step 2: Execute the notebook end-to-end**

Run:

```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/worldbank_gep_forecast.ipynb --ExecutePreprocessor.timeout=180
```

Expected: command exits 0, no exceptions in cell outputs.

- [ ] **Step 3: Verify outputs**

Check the executed notebook's outputs:
- Cell 4's table shows 18 rows (3 countries × 6 years, 2023–2028) with
  columns `country`, `year`, `value`, `obs_status`.
- Cell 6 prints `array(['F'], dtype=object)`.
- Cell 8 renders a line chart with 3 series and no errors.
- Cell 10 prints `['gdp_growth_forecast.csv']`.

Also confirm the CSV landed on disk:

```bash
cat data/worldbank_gep/gdp_growth_forecast.csv
```

Expected: header `country,year,value,obs_status` followed by 18 data rows.

- [ ] **Step 4: Commit**

```bash
git add notebooks/worldbank_gep_forecast.ipynb data/worldbank_gep/gdp_growth_forecast.csv
git commit -m "$(cat <<'EOF'
Add World Bank GEP forecast notebook

Queries World Bank DataBank source 27 (Global Economic Prospects) for
GDP growth forecasts (THA/USA/1T, 2023-2028) directly via requests,
kept outside catalog.yaml/store.py since GEP is a revised forecast
vintage rather than a growing history of actuals (same precedent as
fx_ohlcv_query.ipynb for OHLCV bars).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
