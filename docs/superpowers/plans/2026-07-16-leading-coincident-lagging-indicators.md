# Leading/Coincident/Lagging Indicators Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `notebooks/leading_coincident_lagging_indicators.ipynb`, a standalone demo notebook that queries 16 US macro indicators from FRED plus a thin 3-indicator Thailand panel, tags each by Conference-Board leading/coincident/lagging classification, and plots normalized US trends shaded by NBER recession periods, per [[2026-07-16-leading-coincident-lagging-indicators-design]].

**Architecture:** One companion reference CSV (`notebooks/macro_cycle_indicators_catalog.csv`) documents the full 19-series roster with tags. The notebook itself fetches directly via `FredSource().fetch()` / `WorldBankSource().fetch()` / `yfinance` (ad-hoc `SeriesConfig` objects, no `catalog.yaml` registration, nothing persisted to `data/`), aligns the US series to a common monthly index, z-scores each within its category, and renders one 3-subplot figure (leading/coincident/lagging, shared x-axis) with NBER recession shading.

**Tech Stack:** Python, `pandas`, `matplotlib`, `yfinance`, `macro_data.sources.fred.FredSource`, `macro_data.sources.worldbank.WorldBankSource`, `macro_data.catalog.SeriesConfig`. Notebook built cell-by-cell with the `NotebookEdit` tool; verified with `jupyter nbconvert --to notebook --execute --inplace`.

## Global Constraints

- No `catalog.yaml` changes, no `data/` persistence — standalone notebook only.
- `FRED_API_KEY` is already configured in this environment's `.env` (verified live 2026-07-16) — no key-handling/failure-path code needed for the US panel, unlike other notebooks that gracefully handle a missing key.
- No BOT (Bank of Thailand) source — confirmed broken in project history.
- Kernel must be `macro-data-venv` (`"display_name": "macro-data (.venv)"`) — matches every other notebook's `metadata.kernelspec`, per CLAUDE.md's kernel note.
- Every fetch call (US and Thailand) wrapped in its own try/except — one bad series prints a warning and is dropped, never crashes the cell.
- Final verification command (run after every task that touches the notebook): `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/leading_coincident_lagging_indicators.ipynb --ExecutePreprocessor.timeout=180`, then inspect the executed JSON for `output_type: "error"` cells.
- No pytest coverage for notebooks — verification is nbconvert execution + inspecting output content, not `pytest`.

---

### Task 1: Companion reference CSV

**Files:**
- Create: `notebooks/macro_cycle_indicators_catalog.csv`

**Interfaces:**
- Produces: a 19-row CSV with columns `id,region,source,tag,frequency,name` — Task 2's roster cell reads this file by exactly this relative path (`"macro_cycle_indicators_catalog.csv"`, since nbconvert sets the kernel's cwd to the notebook's own directory — verified live: a `print(os.getcwd())` smoke test in `notebooks/` during `nbconvert --execute` returns the `notebooks/` path, not the repo root).

- [ ] **Step 1: Write the CSV**

Create `notebooks/macro_cycle_indicators_catalog.csv` with exactly this content:

```csv
id,region,source,tag,frequency,name
T10Y3M,US,fred,leading,daily,10Y-3M Treasury yield spread
ICSA,US,fred,leading,weekly,Initial jobless claims
PERMIT,US,fred,leading,monthly,Building permits (new private housing units authorized)
NEWORDER,US,fred,leading,monthly,Manufacturers' new orders: core capital goods ex-aircraft
UMCSENT,US,fred,leading,monthly,U. Michigan Consumer Sentiment Index
AWHMAN,US,fred,leading,monthly,Average weekly hours (manufacturing)
PAYEMS,US,fred,coincident,monthly,Nonfarm payroll employment
INDPRO,US,fred,coincident,monthly,Industrial production index
W875RX1,US,fred,coincident,monthly,Real personal income excluding transfer receipts
USPHCI,US,fred,coincident,monthly,Coincident Economic Activity Index (composite)
RSAFS,US,fred,coincident,monthly,Retail sales
UEMPMEAN,US,fred,lagging,monthly,Average (mean) duration of unemployment
BUSLOANS,US,fred,lagging,monthly,Commercial & industrial loans outstanding
MPRIME,US,fred,lagging,monthly,Bank prime loan rate
CPILFESL,US,fred,lagging,monthly,Core CPI (all items less food & energy)
ULCNFB,US,fred,lagging,quarterly,Unit labor cost (nonfarm business)
^SET.BK,Thailand,yfinance,leading,daily,SET Index (Thailand equities)
NY.GDP.MKTP.KD.ZG,Thailand,worldbank,coincident,annual,GDP growth (annual %)
FP.CPI.TOTL.ZG,Thailand,worldbank,lagging,annual,CPI inflation (annual %)
```

- [ ] **Step 2: Verify row/tag counts**

Run:
```bash
.venv/Scripts/python.exe -c "
import pandas as pd
df = pd.read_csv('notebooks/macro_cycle_indicators_catalog.csv')
assert len(df) == 19, len(df)
assert set(df['tag']) == {'leading', 'coincident', 'lagging'}
assert df['region'].value_counts().to_dict() == {'US': 16, 'Thailand': 3}
assert df['tag'].value_counts().to_dict() == {'leading': 7, 'coincident': 6, 'lagging': 6}
print('OK', len(df), 'rows')
"
```
Expected: `OK 19 rows` with no assertion error.

- [ ] **Step 3: Commit**

```bash
git add notebooks/macro_cycle_indicators_catalog.csv
git commit -m "Add reference catalog CSV for leading/coincident/lagging indicators"
```

---

### Task 2: Notebook skeleton — intro, imports, roster, US fetch

**Files:**
- Create: `notebooks/leading_coincident_lagging_indicators.ipynb`

**Interfaces:**
- Consumes: `notebooks/macro_cycle_indicators_catalog.csv` (Task 1).
- Produces: notebook cells with ids `intro`, `imports`, `roster`, `fetch_us`, containing Python globals `FRED_SERIES` (dict, series_id → `(tag, freq)`), `us_raw` (dict, series_id → DataFrame from `FredSource.fetch`, schema `date`-indexed/`value`-columned), `us_failed` (dict, series_id → error string), `usrec` (DataFrame, NBER recession flag) — Task 3's chart cell consumes all four.

- [ ] **Step 1: Create the notebook file with its first cell**

Create `notebooks/leading_coincident_lagging_indicators.ipynb` with this exact content:

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "id": "intro",
   "metadata": {},
   "source": [
    "# Leading, Coincident & Lagging Macro Indicators\n",
    "\n",
    "Business-cycle indicators are conventionally grouped by *when* they move relative to the cycle, following the Conference Board's classification:\n",
    "\n",
    "- **Leading** — turn before the cycle (yield curve, jobless claims, building permits, new orders, consumer sentiment, manufacturing hours).\n",
    "- **Coincident** — move with the cycle (payrolls, industrial production, personal income, retail sales).\n",
    "- **Lagging** — confirm the cycle after the fact (unemployment duration, business loans, the prime rate, core CPI, unit labor cost).\n",
    "\n",
    "This notebook queries 16 US indicators from FRED (all live-verified 2026-07-16) plus a deliberately thin 3-indicator Thailand panel (SET Index, GDP growth, CPI inflation — the only keyless, reasonably current sources available for this framework), and plots each US category as a normalized trend shaded by NBER recession periods so the lead/coincident/lag relationship is visible directly in the chart.\n",
    "\n",
    "**Standalone notebook:** series are fetched directly via `FredSource`/`WorldBankSource`/`yfinance`, not through `macro_data.update()`/`catalog.yaml` — nothing here is persisted to `data/`. See `macro_cycle_indicators_catalog.csv` alongside this notebook for the full roster with tags."
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "macro-data (.venv)",
   "language": "python",
   "name": "macro-data-venv"
  },
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 2: Read the notebook (required before any NotebookEdit call)**

Use the `Read` tool on `notebooks/leading_coincident_lagging_indicators.ipynb`.

- [ ] **Step 3: Insert the imports cell**

Use `NotebookEdit` with `notebook_path=notebooks/leading_coincident_lagging_indicators.ipynb`, `cell_id="intro"`, `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

from macro_data.catalog import SeriesConfig
from macro_data.sources.fred import FredSource
from macro_data.sources.worldbank import WorldBankSource

pd.set_option("display.max_rows", 25)
%matplotlib inline
```

This cell's id will be auto-assigned by the tool; note it from the tool's response for the next step (referred to below as `<imports_id>`).

- [ ] **Step 4: Insert the roster cell**

Use `NotebookEdit` with `cell_id=<imports_id>`, `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
roster = pd.read_csv("macro_cycle_indicators_catalog.csv")
roster
```

Note the returned id as `<roster_id>`.

- [ ] **Step 5: Insert the US fetch cell**

Use `NotebookEdit` with `cell_id=<roster_id>`, `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
FRED_SERIES = {
    "T10Y3M": ("leading", "D"),
    "ICSA": ("leading", "W"),
    "PERMIT": ("leading", "M"),
    "NEWORDER": ("leading", "M"),
    "UMCSENT": ("leading", "M"),
    "AWHMAN": ("leading", "M"),
    "PAYEMS": ("coincident", "M"),
    "INDPRO": ("coincident", "M"),
    "W875RX1": ("coincident", "M"),
    "USPHCI": ("coincident", "M"),
    "RSAFS": ("coincident", "M"),
    "UEMPMEAN": ("lagging", "M"),
    "BUSLOANS": ("lagging", "M"),
    "MPRIME": ("lagging", "M"),
    "CPILFESL": ("lagging", "M"),
    "ULCNFB": ("lagging", "Q"),
}

fred = FredSource()
us_raw = {}
us_failed = {}
for series_id, (tag, freq) in FRED_SERIES.items():
    cfg = SeriesConfig(id=series_id, source="fred", name=series_id, params={"series": series_id})
    try:
        us_raw[series_id] = fred.fetch(cfg)
    except Exception as exc:
        us_failed[series_id] = str(exc)
        print(f"failed to fetch {series_id}: {exc}")

# NBER recession indicator — used only for chart shading, not a tagged series itself
recession_cfg = SeriesConfig(id="USREC", source="fred", name="USREC", params={"series": "USREC"})
usrec = fred.fetch(recession_cfg)

print(f"fetched {len(us_raw)}/{len(FRED_SERIES)} US series" + (f"; failed: {list(us_failed)}" if us_failed else ""))
```

Note the returned id as `<fetch_us_id>` (used by Task 3).

- [ ] **Step 6: Execute and verify**

Run:
```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/leading_coincident_lagging_indicators.ipynb --ExecutePreprocessor.timeout=180
```
Expected: exits 0, no `[NbConvertApp] ... Error` in output.

Then verify the fetch actually got all 16 series with no failures and confirm the roster table rendered:
```bash
.venv/Scripts/python.exe -c "
import json
nb = json.load(open('notebooks/leading_coincident_lagging_indicators.ipynb', encoding='utf-8'))
cells = {c.get('id'): c for c in nb['cells']}
fetch_cell = [c for c in nb['cells'] if c['cell_type']=='code' and 'FRED_SERIES' in ''.join(c['source'])][0]
text = ''.join(o.get('text', '') for o in fetch_cell['outputs'] if o.get('output_type')=='stream')
print(text)
assert 'fetched 16/16 US series' in text, text
errors = [c for c in nb['cells'] if c['cell_type']=='code' for o in c.get('outputs', []) if o.get('output_type')=='error']
assert not errors, errors
print('OK: no fetch failures, no cell errors')
"
```
Expected: prints the fetch summary line and `OK: no fetch failures, no cell errors`. If any series fails (e.g. a transient FRED rate limit), re-run Step 6 once before treating it as a real problem — the design's error-isolation is meant for occasional single-series failures, not a systematic block.

- [ ] **Step 7: Commit**

```bash
git add notebooks/leading_coincident_lagging_indicators.ipynb
git commit -m "Add intro, roster, and US FRED fetch cells for leading/coincident/lagging notebook"
```

---

### Task 3: Normalized trend charts, commentary, US snapshot table

**Files:**
- Modify: `notebooks/leading_coincident_lagging_indicators.ipynb`

**Interfaces:**
- Consumes: `FRED_SERIES`, `us_raw`, `usrec` from Task 2's `fetch_us` cell.
- Produces: notebook cells `trend_charts`, `commentary`, `snapshot_table`. `snapshot_table` cell produces a `snapshot` DataFrame (not consumed elsewhere, but its row count is asserted in verification).

- [ ] **Step 1: Read the notebook**

Use `Read` on `notebooks/leading_coincident_lagging_indicators.ipynb` (required before `NotebookEdit`; also needed to find `<fetch_us_id>` if not already known from Task 2).

- [ ] **Step 2: Insert the trend-chart cell**

Use `NotebookEdit` with `cell_id=<fetch_us_id>`, `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
WINDOW_START = "1992-01-01"


def to_monthly(df, freq):
    s = df["value"]
    if freq in ("D", "W"):
        return s.resample("MS").mean()
    if freq == "Q":
        return s.resample("MS").ffill()
    return s.resample("MS").last()


us_monthly = {
    series_id: to_monthly(df, FRED_SERIES[series_id][1])
    for series_id, df in us_raw.items()
}
usrec_monthly = usrec["value"].resample("MS").max()

categories = {"leading": [], "coincident": [], "lagging": []}
for series_id, (tag, _freq) in FRED_SERIES.items():
    if series_id in us_monthly:
        categories[tag].append(series_id)

category_frames = {
    tag: pd.DataFrame({sid: us_monthly[sid] for sid in ids}).dropna(how="all")
    for tag, ids in categories.items()
}


def zscore(frame, start=WINDOW_START):
    windowed = frame.loc[start:]
    return (windowed - windowed.mean()) / windowed.std()


zscored = {tag: zscore(frame) for tag, frame in category_frames.items()}


def recession_spans(flags):
    flags = flags.dropna()
    spans = []
    span_start = None
    for date, val in flags.items():
        if val >= 0.5 and span_start is None:
            span_start = date
        elif val < 0.5 and span_start is not None:
            spans.append((span_start, date))
            span_start = None
    if span_start is not None:
        spans.append((span_start, flags.index[-1]))
    return spans


rec_spans = recession_spans(usrec_monthly.loc[WINDOW_START:])

tag_titles = {
    "leading": "Leading indicators",
    "coincident": "Coincident indicators",
    "lagging": "Lagging indicators",
}

fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
for ax, tag in zip(axes, ["leading", "coincident", "lagging"]):
    frame = zscored[tag]
    for col in frame.columns:
        ax.plot(frame.index, frame[col], linewidth=1.5, label=col)
    for span_start, span_end in rec_spans:
        ax.axvspan(span_start, span_end, color="grey", alpha=0.15, linewidth=0)
    ax.set_title(tag_titles[tag], fontsize=11)
    ax.set_ylabel("z-score")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.legend(fontsize=7, ncol=3, loc="upper left")
    ax.grid(alpha=0.2)

axes[-1].set_xlabel("Date")
fig.suptitle(
    "US leading / coincident / lagging indicators, normalized (z-score), shaded = NBER recession",
    y=0.995,
)
plt.tight_layout()
plt.show()
```

Note the returned id as `<trend_charts_id>`.

- [ ] **Step 3: Insert the commentary markdown cell**

Use `NotebookEdit` with `cell_id=<trend_charts_id>`, `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## Reading the chart

Historically, **leading** indicators such as the yield curve spread and jobless claims tend to turn several months to over a year before a recession begins. **Coincident** indicators — payrolls, industrial production — move together with the cycle, which is why they're used to date recessions after the fact. **Lagging** indicators such as unemployment duration and business loan balances typically keep deteriorating for months *after* a recession has already ended, since employers and lenders adjust slowly. The shaded bands mark NBER recession months; watch how the three panels above cross zero at different points around each band.
```

Note the returned id as `<commentary_id>`.

- [ ] **Step 4: Insert the US snapshot table cell**

Use `NotebookEdit` with `cell_id=<commentary_id>`, `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
snapshot_rows = []
for series_id, (tag, freq) in FRED_SERIES.items():
    if series_id not in us_raw:
        continue
    s = us_raw[series_id]["value"]
    snapshot_rows.append(
        {
            "series": series_id,
            "tag": tag,
            "latest_value": s.iloc[-1],
            "as_of": s.index[-1].date(),
        }
    )

snapshot = pd.DataFrame(snapshot_rows).set_index("series").sort_values(["tag", "series"])
snapshot
```

Note the returned id as `<snapshot_table_id>` (used by Task 4).

- [ ] **Step 5: Execute and verify**

Run:
```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/leading_coincident_lagging_indicators.ipynb --ExecutePreprocessor.timeout=180
```
Expected: exits 0, no errors.

Then verify the chart rendered (image output present) and the snapshot table has all 16 rows:
```bash
.venv/Scripts/python.exe -c "
import json
nb = json.load(open('notebooks/leading_coincident_lagging_indicators.ipynb', encoding='utf-8'))
chart_cell = [c for c in nb['cells'] if c['cell_type']=='code' and 'fig, axes = plt.subplots(3, 1' in ''.join(c['source'])][0]
assert any(o.get('output_type')=='display_data' and 'image/png' in o.get('data', {}) for o in chart_cell['outputs']), chart_cell['outputs']
snapshot_cell = [c for c in nb['cells'] if c['cell_type']=='code' and 'snapshot_rows' in ''.join(c['source'])][0]
text_out = [o for o in snapshot_cell['outputs'] if o.get('output_type')=='execute_result']
assert text_out, snapshot_cell['outputs']
html = text_out[0]['data'].get('text/html', [''])[0]
assert html.count('<tr>') - 1 == 16, 'expected 16 data rows, got ' + str(html.count('<tr>') - 1)
errors = [c for c in nb['cells'] if c['cell_type']=='code' for o in c.get('outputs', []) if o.get('output_type')=='error']
assert not errors, errors
print('OK: chart rendered, snapshot table has 16 rows, no cell errors')
"
```
Expected: `OK: chart rendered, snapshot table has 16 rows, no cell errors`.

- [ ] **Step 6: Commit**

```bash
git add notebooks/leading_coincident_lagging_indicators.ipynb
git commit -m "Add normalized trend charts, commentary, and US snapshot table"
```

---

### Task 4: Thailand panel, scope note, final verification

**Files:**
- Modify: `notebooks/leading_coincident_lagging_indicators.ipynb`

**Interfaces:**
- Consumes: nothing from earlier tasks except the notebook file itself and its last cell id (`<snapshot_table_id>`).
- Produces: final notebook state — cells `thailand_intro`, `thailand_fetch`, `thailand_chart_table`, `scope_note`.

- [ ] **Step 1: Read the notebook**

Use `Read` on `notebooks/leading_coincident_lagging_indicators.ipynb`.

- [ ] **Step 2: Insert the Thailand intro markdown cell**

Use `NotebookEdit` with `cell_id=<snapshot_table_id>`, `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## Thailand panel — deliberately thin

FRED's Thailand coverage was searched live for monthly leading/coincident/lagging-style series (composite leading index, industrial production, interest-rate spreads, etc.) and returned nothing both monthly and current — only stale World Bank mirror series (several last updated 2019–2024) or annual-only data. The Bank of Thailand API gateway this project previously used for Thailand series is also known to be broken as of 2026-07-15.

The three series below are the honest ceiling of what's available without a paid feed: a genuinely current daily equity index as a leading proxy, and two annual World Bank series (GDP growth, CPI inflation) as coincident/lagging proxies respectively. This is not parity with the 16-series, mostly-monthly US panel above — it's presented at its real, thinner resolution rather than stretched to look equivalent.
```

Note the returned id as `<thailand_intro_id>`.

- [ ] **Step 3: Insert the Thailand fetch cell**

Use `NotebookEdit` with `cell_id=<thailand_intro_id>`, `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
wb = WorldBankSource()

set_index_hist = yf.Ticker("^SET.BK").history(period="5y")
set_index_hist.index = set_index_hist.index.tz_localize(None)

gdp_growth_cfg = SeriesConfig(
    id="th_gdp_growth",
    source="worldbank",
    name="Thailand GDP growth",
    params={"indicator": "NY.GDP.MKTP.KD.ZG", "country": "THA"},
)
cpi_inflation_cfg = SeriesConfig(
    id="th_cpi_inflation",
    source="worldbank",
    name="Thailand CPI inflation",
    params={"indicator": "FP.CPI.TOTL.ZG", "country": "THA"},
)

th_series = {}
th_failed = {}
for label, cfg in [("gdp_growth", gdp_growth_cfg), ("cpi_inflation", cpi_inflation_cfg)]:
    try:
        th_series[label] = wb.fetch(cfg)
    except Exception as exc:
        th_failed[label] = str(exc)
        print(f"failed to fetch {label}: {exc}")

print(f"fetched Thailand World Bank series: {list(th_series)}" + (f"; failed: {list(th_failed)}" if th_failed else ""))
```

Note the returned id as `<thailand_fetch_id>`.

- [ ] **Step 4: Insert the Thailand chart + table cell**

Use `NotebookEdit` with `cell_id=<thailand_fetch_id>`, `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(set_index_hist.index, set_index_hist["Close"], linewidth=1.5, color="tab:blue")
ax.set_title("SET Index (Thailand) — leading proxy, last 5 years")
ax.set_ylabel("Index level")
ax.grid(alpha=0.2)
plt.show()

th_rows = [
    {
        "series": "SET Index",
        "tag": "leading",
        "latest_value": set_index_hist["Close"].iloc[-1],
        "as_of": set_index_hist.index[-1].date(),
    }
]
if "gdp_growth" in th_series:
    s = th_series["gdp_growth"]["value"]
    th_rows.append(
        {"series": "GDP growth (%)", "tag": "coincident", "latest_value": s.iloc[-1], "as_of": s.index[-1].date()}
    )
if "cpi_inflation" in th_series:
    s = th_series["cpi_inflation"]["value"]
    th_rows.append(
        {"series": "CPI inflation (%)", "tag": "lagging", "latest_value": s.iloc[-1], "as_of": s.index[-1].date()}
    )

pd.DataFrame(th_rows).set_index("series")
```

Note the returned id as `<thailand_chart_table_id>`.

- [ ] **Step 5: Insert the closing scope/limitations markdown cell**

Use `NotebookEdit` with `cell_id=<thailand_chart_table_id>`, `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## Scope & limitations

- **Standalone, not tracked:** nothing in this notebook is written to `catalog.yaml` or `data/` — re-running it re-fetches everything from source.
- **US-centric by data availability, not choice:** FRED has no current monthly leading/coincident/lagging-style panel for Thailand; the 3-series Thailand panel above is annual/thin where the US panel is monthly-to-daily.
- **No forecasting:** charts are descriptive (what happened before past recessions), not a recession-probability model.
- **No BOT (Bank of Thailand) source used** — confirmed broken elsewhere in this project as of 2026-07-15.
```

- [ ] **Step 6: Full execution and final verification**

Run:
```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/leading_coincident_lagging_indicators.ipynb --ExecutePreprocessor.timeout=180
```
Expected: exits 0, no errors, full notebook (all 11 cells) runs top to bottom.

Then verify the Thailand table has exactly 3 rows and confirm there are zero error outputs anywhere in the notebook:
```bash
.venv/Scripts/python.exe -c "
import json
nb = json.load(open('notebooks/leading_coincident_lagging_indicators.ipynb', encoding='utf-8'))
assert len(nb['cells']) == 11, f'expected 11 cells, got {len(nb[\"cells\"])}'
th_cell = [c for c in nb['cells'] if c['cell_type']=='code' and 'th_rows' in ''.join(c['source'])][0]
text_out = [o for o in th_cell['outputs'] if o.get('output_type')=='execute_result']
assert text_out, th_cell['outputs']
html = text_out[0]['data'].get('text/html', [''])[0]
assert html.count('<tr>') - 1 == 3, 'expected 3 Thailand rows, got ' + str(html.count('<tr>') - 1)
errors = [c for c in nb['cells'] if c['cell_type']=='code' for o in c.get('outputs', []) if o.get('output_type')=='error']
assert not errors, errors
print('OK: 11 cells, 3 Thailand rows, no cell errors anywhere')
"
```
Expected: `OK: 11 cells, 3 Thailand rows, no cell errors anywhere`.

- [ ] **Step 7: Commit**

```bash
git add notebooks/leading_coincident_lagging_indicators.ipynb
git commit -m "Add Thailand panel and scope note to leading/coincident/lagging notebook"
```

---

## Post-plan check

After Task 4, re-read `docs/superpowers/specs/2026-07-16-leading-coincident-lagging-indicators-design.md` section by section and confirm every notebook section (1–8) has a corresponding cell: intro (1), roster (2), fetch_us (3), trend_charts (4), commentary (5), snapshot_table (6), thailand_intro/thailand_fetch/thailand_chart_table (7), scope_note (8). All 8 sections are covered by the 11 cells built across Tasks 2–4.
