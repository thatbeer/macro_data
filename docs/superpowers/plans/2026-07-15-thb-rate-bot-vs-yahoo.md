# THB Rate: BOT vs. Yahoo Finance Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `notebooks/thb_rate_bot_vs_yahoo.ipynb`, comparing BOT's daily average USD/THB reference rate against Yahoo Finance's `THB=X` spot quote over the last 1 year.

**Architecture:** A single new notebook, built incrementally cell-by-cell, using only the public `macro_data` package surface (`update`, `load`) to fetch/read both series, then pandas for alignment/stats and matplotlib for charts. No new package code, no new tests (notebooks in this repo aren't covered by `pytest`).

**Tech Stack:** Python, pandas, matplotlib, the existing `macro_data` package, Jupyter (`nbconvert --execute --inplace` for verification).

## Global Constraints

- **Amendment (2026-07-15):** the original plan used `macro_data`'s catalog series `usd_thb_bot` (source `bot`, old `apigw1.bot.or.th` gateway) for the BOT side. That gateway is confirmed dead — `apigw1.bot.or.th` doesn't resolve in DNS at all (`NameResolutionError`), discovered when Task 1 was first attempted. The plan below uses the standalone `bot_api` client's `reference_rate.daily()` (new gateway `gateway.api.bot.or.th`, confirmed live in `BOT_query.ipynb` §5) instead. `usd_thb_bot` and `catalog.yaml` are not touched by this plan.
- Yahoo side goes through `macro_data`'s public surface only: `from macro_data import update, load` — never reach into `macro_data.sources`/`macro_data.pipeline` directly (per `CLAUDE.md`). Yahoo series id: `usd_thb` (source `yahoo`, ticker `THB=X`), already in `catalog.yaml`.
- BOT side goes through the standalone `bot_api` client (`src/bot_api`), the same way `notebooks/BOT_query.ipynb` does: `sys.path.insert(0, str(Path("..") / "src"))` before `from bot_api import BOTClient`, and `load_dotenv(Path("..") / ".env")` to pick up `BOT_CLIENT_ID`. `ReferenceRateEndpoint` uses `key_attr="api_key"` (the default), i.e. `BOT_CLIENT_ID`, not `BOT_CLIENT_ID_INTEREST` — confirmed in `src/bot_api/endpoints/reference_rate.py` (no `key_attr` override) and `src/bot_api/endpoints/base.py:32`.
- `bot_client.reference_rate.daily(start_period, end_period)` takes `YYYY-MM-DD` strings and returns a DataFrame with columns `period` (parsed datetime) and `rate` (**string**, not float — cast with `.astype(float)`, confirmed in `BOT_query.ipynb` §5's `compare["rate"] = compare["rate"].astype(float)`). Confirmed in `src/bot_api/endpoints/reference_rate.py:36-43` and `src/bot_api/client.py:105-114` (`to_dataframe`).
- **`reference_rate.daily()` enforces an undocumented 31-day limit per call** — a range longer than 31 days returns HTTP 400 `{"message": "Exceed limit period. Limit period is 31 days"}` (confirmed empirically 2026-07-15 hitting the live gateway directly; the `bot-api-standalone-client` memory previously only documented this limit for `bond_auction`, not `reference_rate`). Fetching 365 days requires chunking into ≤31-day windows and concatenating.
- `load(series_id)` (macro_data) returns a DataFrame indexed by `date` (ascending, deduped) with one column, `value` — confirmed in `macro_data/store.py:15-19`.
- No try/except on the Yahoo side: `update()` already isolates per-series failures into its returned status dict (`pipeline.py`); let any downstream `load()` failure raise naturally. No try/except on the BOT side either: a single ad-hoc `reference_rate.daily()` call either succeeds or raises (matches `BOT_query.ipynb`'s un-wrapped calls, e.g. §1, §5) — if `BOT_CLIENT_ID` is missing, let `ValueError` from `Endpoint._resolve_key()` propagate.
- Do not persist the merged/derived comparison to `data/` — this notebook is analysis-only (matches `usd_thb_trend_and_indices.ipynb`).
- Notebook kernel metadata must match the project's pinned kernel exactly:
  ```json
  "kernelspec": {
    "display_name": "macro-data (.venv)",
    "language": "python",
    "name": "macro-data-venv"
  }
  ```
  with `"nbformat": 4, "nbformat_minor": 5`.
- Verify each task by running (from repo root):
  `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/thb_rate_bot_vs_yahoo.ipynb --ExecutePreprocessor.timeout=180`
  A non-zero exit or `Traceback` in the command output means the task failed — fix before committing.
- Commit only `notebooks/thb_rate_bot_vs_yahoo.ipynb` in each task (it will contain populated outputs after the verify step — that's expected and matches how the other notebooks are committed).
- `NotebookEdit`'s `insert` mode has no parameter to set the *new* cell's own id — it only takes the id of the cell to insert **after**. The new cell's id is assigned automatically. So after every insert step in Tasks 2-3, use the **Read** tool on the notebook to see the id the tool just assigned (it appears as `<cell id="...">` in Read's output) before using it as the `cell_id` target for the next insert. Do not assume or invent an id.

---

### Task 1: Notebook skeleton — intro, setup, fetch, load, restrict to last 1 year

**Files:**
- Create: `notebooks/thb_rate_bot_vs_yahoo.ipynb`

**Interfaces:**
- Produces: notebook cells with ids `intro` (markdown) and `setup` (code). The `setup` cell defines module-level names `bot_client`, `yahoo_status`, `bot`, `yahoo_full`, `yahoo` — later tasks read `bot` (DataFrame indexed by `date`, column `rate` as float64, last 365 days from BOT directly) and `yahoo` (DataFrame indexed by `date`, column `value`, sliced to Yahoo's own last 365 days).

- [ ] **Step 1: Create the notebook file**

Use the Write tool to create `d:\MyOffice\AXONS\Macro_data\notebooks\thb_rate_bot_vs_yahoo.ipynb` with exactly this content:

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "id": "intro",
   "metadata": {},
   "source": [
    "# THB Rate: BOT vs. Yahoo Finance\n",
    "\n",
    "Compares Bank of Thailand's officially published USD/THB rate against Yahoo Finance's `THB=X` spot quote over the last 1 year.\n",
    "\n",
    "**Why not BOT's literal \"Spot Rate\" endpoint?** `src/bot_api`'s `spot_rate.daily()` (`Stat-SpotRate/v2/SPOTRATE`) is the BOT endpoint literally named \"spot rate,\" but it's confirmed discontinued: it authenticates and returns the right shape, but every value field is blank (BOT's own response metadata marks the table discontinued, `last_updated: 2024-12-27` — see `notebooks/BOT_query.ipynb` §9).\n",
    "\n",
    "**Why not the catalog's `usd_thb_bot` series?** That series also targets a BOT rate (`mid_rate`), but goes through `macro_data.sources.bot`, which calls the *old* `apigw1.bot.or.th` gateway — and that gateway is now fully dead (its hostname doesn't even resolve in DNS).\n",
    "\n",
    "This notebook instead uses the standalone `bot_api` client's `reference_rate.daily()` — BOT's **weighted-average interbank reference rate** (THB/USD), on BOT's *new* gateway (`gateway.api.bot.or.th`), confirmed live in `notebooks/BOT_query.ipynb` §5.\n",
    "\n",
    "Sections:\n",
    "1. Aligning the two series\n",
    "2. Comparison table\n",
    "3. BOT vs. Yahoo: THB rate over the last year\n",
    "4. Difference and correlation"
   ]
  },
  {
   "cell_type": "code",
   "id": "setup",
   "metadata": {},
   "execution_count": null,
   "outputs": [],
   "source": [
    "import sys\n",
    "from pathlib import Path\n",
    "\n",
    "sys.path.insert(0, str(Path(\"..\") / \"src\"))\n",
    "\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "from dotenv import load_dotenv\n",
    "\n",
    "from bot_api import BOTClient\n",
    "from macro_data import update, load\n",
    "\n",
    "load_dotenv(Path(\"..\") / \".env\")\n",
    "pd.set_option(\"display.max_rows\", 20)\n",
    "%matplotlib inline\n",
    "\n",
    "bot_client = BOTClient()\n",
    "\n",
    "\n",
    "def fetch_bot_reference_rate(client, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:\n",
    "    \"\"\"reference_rate.daily() caps each call at a 31-day window; page through and concatenate.\"\"\"\n",
    "    frames = []\n",
    "    chunk_start = start\n",
    "    while chunk_start <= end:\n",
    "        chunk_end = min(chunk_start + pd.Timedelta(days=30), end)\n",
    "        frames.append(\n",
    "            client.reference_rate.daily(chunk_start.strftime(\"%Y-%m-%d\"), chunk_end.strftime(\"%Y-%m-%d\"))\n",
    "        )\n",
    "        chunk_start = chunk_end + pd.Timedelta(days=1)\n",
    "    return pd.concat(frames, ignore_index=True)\n",
    "\n",
    "\n",
    "end_date = pd.Timestamp.today().normalize()\n",
    "start_date = end_date - pd.Timedelta(days=365)\n",
    "\n",
    "bot = fetch_bot_reference_rate(bot_client, start_date, end_date)\n",
    "bot = bot.set_index(\"period\").rename_axis(\"date\").sort_index()\n",
    "bot[\"rate\"] = bot[\"rate\"].astype(float)\n",
    "\n",
    "yahoo_status = update(\"yahoo\")  # refreshes all yahoo series; we only use usd_thb below\n",
    "print(\"yahoo:\", yahoo_status)\n",
    "\n",
    "yahoo_full = load(\"usd_thb\")\n",
    "cutoff_yahoo = yahoo_full.index.max() - pd.Timedelta(days=365)\n",
    "yahoo = yahoo_full[yahoo_full.index >= cutoff_yahoo]\n",
    "\n",
    "print(f\"BOT reference_rate: {len(bot)} rows, {bot.index.min().date()} to {bot.index.max().date()}\")\n",
    "print(f\"Yahoo usd_thb: {len(yahoo)} rows, {yahoo.index.min().date()} to {yahoo.index.max().date()}\")"
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
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.14.5"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 2: Execute and verify**

Run: `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/thb_rate_bot_vs_yahoo.ipynb --ExecutePreprocessor.timeout=180`

Expected: command exits 0, no `Traceback` in output. Then inspect the executed notebook's `setup` cell output (e.g. `python -c "import json; nb=json.load(open('notebooks/thb_rate_bot_vs_yahoo.ipynb', encoding='utf-8')); print(nb['cells'][1]['outputs'])"`) and confirm:
- No `ValueError`/`HTTPError`/`ConnectionError` traceback from the `bot_client.reference_rate.daily(...)` call. If it raises `ValueError: BOT API key not set for 'Stat-ReferenceRate/v2'`, stop and tell the user — `.env` needs `BOT_CLIENT_ID` (per `CLAUDE.md` this is expected-if-unconfigured, not a bug to fix in the notebook). If it raises a connection/DNS error again, stop — that would mean the *new* gateway is also unreachable, a bigger problem worth surfacing before continuing.
- Both row-count print lines (`BOT reference_rate: ...`, `Yahoo usd_thb: ...`) show non-zero row counts.

- [ ] **Step 3: Commit**

```bash
git add notebooks/thb_rate_bot_vs_yahoo.ipynb
git commit -m "Add THB rate notebook: skeleton, fetch, and load (BOT vs Yahoo)"
```

---

### Task 2: Align the two series and build the comparison table

**Files:**
- Modify: `notebooks/thb_rate_bot_vs_yahoo.ipynb` (insert 4 cells after the `setup` cell)

**Interfaces:**
- Consumes: `bot` (DataFrame indexed by `date`, column `rate`) and `yahoo` (DataFrame indexed by `date`, column `value`) from Task 1's `setup` cell.
- Produces: a code cell (referred to below as the "align" cell) defines `merged` (DataFrame indexed by `date`, columns `bot_ref_rate`, `yahoo_close`) via inner join. A later code cell (the "table" cell) defines `comparison` (== `merged` plus `abs_diff`, `pct_diff` columns) — Task 3 reads `comparison` and `merged`.

- [ ] **Step 1: Read the notebook to confirm the `setup` cell's id**

Use the Read tool on `d:\MyOffice\AXONS\Macro_data\notebooks\thb_rate_bot_vs_yahoo.ipynb`. Confirm the second cell (the code cell) still has `id="setup"` (Task 1 set this explicitly in the raw JSON, so it should be unchanged).

- [ ] **Step 2: Insert the "Aligning the two series" markdown cell**

Use the NotebookEdit tool: `notebook_path="d:\MyOffice\AXONS\Macro_data\notebooks\thb_rate_bot_vs_yahoo.ipynb"`, `cell_id="setup"`, `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## 1. Aligning the two series

BOT publishes its reference rate on business days only; Yahoo's `THB=X` trades most calendar days (it's an OTC spot quote, not exchange-cleared). Inner-joining on date keeps only the days both sources published a value.
```

- [ ] **Step 3: Read the notebook to find the new markdown cell's id**

Read the notebook again. The cell immediately after `setup` is the markdown cell just inserted — note its `id` (call it `<align_md_id>` below).

- [ ] **Step 4: Insert the alignment code cell**

NotebookEdit: `cell_id=<align_md_id>` (from Step 3), `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
merged = pd.merge(
    bot.rename(columns={"rate": "bot_ref_rate"}),
    yahoo.rename(columns={"value": "yahoo_close"}),
    left_index=True,
    right_index=True,
    how="inner",
)

print(f"BOT dates: {len(bot)}, Yahoo dates: {len(yahoo)}, matched (inner join): {len(merged)}")
merged.tail()
```

- [ ] **Step 5: Read the notebook to find the align code cell's id**

Read the notebook again. Note the `id` of the code cell just inserted (call it `<align_code_id>`).

- [ ] **Step 6: Insert the "Comparison table" markdown cell**

NotebookEdit: `cell_id=<align_code_id>` (from Step 5), `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## 2. Comparison table

`abs_diff` is Yahoo's close minus BOT's reference rate (positive means Yahoo quotes more THB per USD than BOT's official average that day); `pct_diff` is the same difference as a percentage of BOT's rate.
```

- [ ] **Step 7: Read the notebook to find this markdown cell's id**

Read the notebook again. Note the `id` of the markdown cell just inserted (call it `<table_md_id>`).

- [ ] **Step 8: Insert the comparison table code cell**

NotebookEdit: `cell_id=<table_md_id>` (from Step 7), `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
comparison = merged.copy()
comparison["abs_diff"] = comparison["yahoo_close"] - comparison["bot_ref_rate"]
comparison["pct_diff"] = comparison["abs_diff"] / comparison["bot_ref_rate"] * 100

comparison.tail(10)
```

- [ ] **Step 9: Read the notebook to find the table code cell's id**

Read the notebook again. Note the `id` of the code cell just inserted (call it `<table_code_id>`) — Task 3 needs this id to insert after it.

- [ ] **Step 10: Execute and verify**

Run: `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/thb_rate_bot_vs_yahoo.ipynb --ExecutePreprocessor.timeout=180`

Expected: exits 0, no `Traceback`. The alignment cell's printed line shows `matched (inner join): N` where `N > 0` and `N <= min(len(bot), len(yahoo))`. The comparison table cell's output has columns `bot_ref_rate`, `yahoo_close`, `abs_diff`, `pct_diff`.

- [ ] **Step 11: Commit**

```bash
git add notebooks/thb_rate_bot_vs_yahoo.ipynb
git commit -m "Add alignment and comparison table to THB rate notebook"
```

Note the final `<table_code_id>` value used above (from Step 9) — Task 3 needs it as the anchor for its first insert.

---

### Task 3: Charts, difference stats, and closing notes

**Files:**
- Modify: `notebooks/thb_rate_bot_vs_yahoo.ipynb` (insert 5 cells after the comparison-table code cell, i.e. the last cell in the notebook at the start of this task)

**Interfaces:**
- Consumes: `merged`, `comparison` DataFrames from Task 2.
- Produces: final complete notebook (no further tasks depend on this one).

- [ ] **Step 1: Read the notebook to confirm the anchor cell id**

Read `d:\MyOffice\AXONS\Macro_data\notebooks\thb_rate_bot_vs_yahoo.ipynb`. The last cell should be the comparison-table code cell (`comparison.tail(10)` as its final line) — this is `<table_code_id>` from Task 2 Step 9. If Task 2 was done in the same session its id is already known; otherwise read it fresh here.

- [ ] **Step 2: Insert the overlay-chart markdown cell**

NotebookEdit: `cell_id=<table_code_id>` (from Step 1), `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## 3. BOT vs. Yahoo: THB rate over the last year
```

- [ ] **Step 3: Read the notebook to find this markdown cell's id**

Read the notebook again. Note the `id` of the markdown cell just inserted (call it `<chart_md_id>`).

- [ ] **Step 4: Insert the overlay-chart code cell**

NotebookEdit: `cell_id=<chart_md_id>` (from Step 3), `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
fig, ax = plt.subplots(figsize=(11, 5))
merged["bot_ref_rate"].plot(ax=ax, label="BOT weighted-average interbank reference rate")
merged["yahoo_close"].plot(ax=ax, label="Yahoo Finance THB=X (close)")
ax.set_title("USD/THB — BOT vs. Yahoo Finance, last 1 year")
ax.set_ylabel("THB per USD")
ax.legend()
ax.grid(alpha=0.3)
plt.show()
```

- [ ] **Step 5: Read the notebook to find the chart code cell's id**

Read the notebook again. Note the `id` of the code cell just inserted (call it `<chart_code_id>`).

- [ ] **Step 6: Insert the "Difference and correlation" markdown cell**

NotebookEdit: `cell_id=<chart_code_id>` (from Step 5), `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## 4. Difference and correlation
```

- [ ] **Step 7: Read the notebook to find this markdown cell's id**

Read the notebook again. Note the `id` of the markdown cell just inserted (call it `<diff_md_id>`).

- [ ] **Step 8: Insert the difference-chart-and-stats code cell**

NotebookEdit: `cell_id=<diff_md_id>` (from Step 7), `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
diff = comparison["abs_diff"]

fig, ax = plt.subplots(figsize=(11, 4))
diff.plot(ax=ax, color="tab:red")
ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
ax.set_title("Yahoo close minus BOT reference rate")
ax.set_ylabel("THB")
ax.grid(alpha=0.3)
plt.show()

stats = pd.Series(
    {
        "mean_diff": diff.mean(),
        "std_diff": diff.std(),
        "max_abs_diff": diff.abs().max(),
        "correlation": comparison["bot_ref_rate"].corr(comparison["yahoo_close"]),
    },
    name="BOT vs. Yahoo (last 1 year)",
)
stats
```

- [ ] **Step 9: Read the notebook to find the diff code cell's id**

Read the notebook again. Note the `id` of the code cell just inserted (call it `<diff_code_id>`).

- [ ] **Step 10: Insert the closing notes markdown cell**

NotebookEdit: `cell_id=<diff_code_id>` (from Step 9), `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## Notes

- BOT's reference rate is a once-daily official calculation — a weighted average of interbank USD/THB trades $\geq$1M, published every business day at 6pm BKK — while Yahoo's `THB=X` close is a continuously-quoted market snapshot at day-end. A small, fairly consistent gap between the two is expected behavior, not a data error.
- BOT's actual "Spot Rate" API (`Stat-SpotRate/SPOTRATE`) is discontinued — see `BOT_query.ipynb` §9. The catalog's `usd_thb_bot` series (`mid_rate`) was also considered, but its gateway (`apigw1.bot.or.th`) is now fully unreachable (DNS resolution failure). This notebook uses the interbank reference rate via the standalone `bot_api` client instead, which is confirmed live.
- This notebook doesn't persist the merged comparison to `data/` — same spirit as `usd_thb_trend_and_indices.ipynb`, reading from the existing store and writing nothing new.
```

- [ ] **Step 11: Final execute and verify**

Run: `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/thb_rate_bot_vs_yahoo.ipynb --ExecutePreprocessor.timeout=180`

Expected: exits 0, no `Traceback`. Confirm the full notebook now has 11 cells (6 markdown, 5 code) and every code cell has non-error outputs (spot-check with `python -c "import json; nb=json.load(open('notebooks/thb_rate_bot_vs_yahoo.ipynb', encoding='utf-8')); print([c['cell_type'] for c in nb['cells']]); print(any('traceback' in str(o).lower() for c in nb['cells'] for o in c.get('outputs', [])))"` — last line must print `False`).

- [ ] **Step 12: Commit**

```bash
git add notebooks/thb_rate_bot_vs_yahoo.ipynb
git commit -m "Add charts and closing notes to THB rate notebook"
```
