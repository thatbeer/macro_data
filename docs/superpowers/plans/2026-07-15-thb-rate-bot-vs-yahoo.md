# THB Rate: BOT vs. Yahoo Finance Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `notebooks/thb_rate_bot_vs_yahoo.ipynb`, comparing BOT's daily average USD/THB reference rate against Yahoo Finance's `THB=X` spot quote over the last 1 year.

**Architecture:** A single new notebook, built incrementally cell-by-cell, using only the public `macro_data` package surface (`update`, `load`) to fetch/read both series, then pandas for alignment/stats and matplotlib for charts. No new package code, no new tests (notebooks in this repo aren't covered by `pytest`).

**Tech Stack:** Python, pandas, matplotlib, the existing `macro_data` package, Jupyter (`nbconvert --execute --inplace` for verification).

## Global Constraints

- Data access goes through `macro_data`'s public surface only: `from macro_data import update, load` — never reach into `macro_data.sources`/`macro_data.pipeline` directly (per `CLAUDE.md`).
- BOT series id: `usd_thb_bot` (source `bot`, field `mid_rate`). Yahoo series id: `usd_thb` (source `yahoo`, ticker `THB=X`). Both already exist in `catalog.yaml` — do not edit `catalog.yaml`.
- `load(series_id)` returns a DataFrame indexed by `date` (ascending, deduped) with one column, `value` — confirmed in `macro_data/store.py:15-19`.
- No new try/except: `update()` already isolates per-series failures into its returned status dict (`pipeline.py`); let any downstream `load()` failure raise naturally.
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
- Produces: notebook cells with ids `intro` (markdown) and `setup` (code). The `setup` cell defines module-level names `bot_status`, `yahoo_status`, `bot_full`, `yahoo_full`, `bot`, `yahoo` — later tasks read `bot` and `yahoo` (each a DataFrame indexed by `date` with column `value`, sliced to the last 365 days of that series' own history).

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
    "**Why not BOT's literal \"Spot Rate\" endpoint?** `src/bot_api`'s `spot_rate.daily()` (`Stat-SpotRate/v2/SPOTRATE`) is the BOT endpoint literally named \"spot rate,\" but it's confirmed discontinued: it authenticates and returns the right shape, but every value field is blank (BOT's own response metadata marks the table discontinued, `last_updated: 2024-12-27` — see `notebooks/BOT_query.ipynb` §9). This notebook instead uses the catalog's `usd_thb_bot` series — BOT's **daily average reference rate** (`mid_rate`), the closest live, officially-published daily USD/THB figure BOT offers.\n",
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
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "\n",
    "from macro_data import update, load\n",
    "\n",
    "pd.set_option(\"display.max_rows\", 20)\n",
    "%matplotlib inline\n",
    "\n",
    "bot_status = update(\"bot\")      # catalog's only bot series: usd_thb_bot\n",
    "yahoo_status = update(\"yahoo\")  # refreshes all yahoo series; we only use usd_thb below\n",
    "\n",
    "print(\"bot:\", bot_status)\n",
    "print(\"yahoo:\", yahoo_status)\n",
    "\n",
    "bot_full = load(\"usd_thb_bot\")\n",
    "yahoo_full = load(\"usd_thb\")\n",
    "\n",
    "cutoff_bot = bot_full.index.max() - pd.Timedelta(days=365)\n",
    "cutoff_yahoo = yahoo_full.index.max() - pd.Timedelta(days=365)\n",
    "\n",
    "bot = bot_full[bot_full.index >= cutoff_bot]\n",
    "yahoo = yahoo_full[yahoo_full.index >= cutoff_yahoo]\n",
    "\n",
    "print(f\"BOT usd_thb_bot: {len(bot)} rows, {bot.index.min().date()} to {bot.index.max().date()}\")\n",
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
- The `bot:` line shows `usd_thb_bot` with a status of `up-to-date`, `updated N rows`, or similar success — **not** `failed: ...`. If it shows `failed: environment variable BOT_CLIENT_ID is not set`, stop and tell the user — `.env` needs `BOT_CLIENT_ID` (per `CLAUDE.md` this is expected-if-unconfigured, not a bug to fix in the notebook).
- Both row-count print lines show non-zero row counts.

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
- Consumes: `bot`, `yahoo` DataFrames from Task 1's `setup` cell (indexed by `date`, column `value`).
- Produces: a code cell (referred to below as the "align" cell) defines `merged` (DataFrame indexed by `date`, columns `bot_mid_rate`, `yahoo_close`) via inner join. A later code cell (the "table" cell) defines `comparison` (== `merged` plus `abs_diff`, `pct_diff` columns) — Task 3 reads `comparison` and `merged`.

- [ ] **Step 1: Read the notebook to confirm the `setup` cell's id**

Use the Read tool on `d:\MyOffice\AXONS\Macro_data\notebooks\thb_rate_bot_vs_yahoo.ipynb`. Confirm the second cell (the code cell) still has `id="setup"` (Task 1 set this explicitly in the raw JSON, so it should be unchanged).

- [ ] **Step 2: Insert the "Aligning the two series" markdown cell**

Use the NotebookEdit tool: `notebook_path="d:\MyOffice\AXONS\Macro_data\notebooks\thb_rate_bot_vs_yahoo.ipynb"`, `cell_id="setup"`, `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## 1. Aligning the two series

BOT publishes `mid_rate` on business days only; Yahoo's `THB=X` trades most calendar days (it's an OTC spot quote, not exchange-cleared). Inner-joining on date keeps only the days both sources published a value.
```

- [ ] **Step 3: Read the notebook to find the new markdown cell's id**

Read the notebook again. The cell immediately after `setup` is the markdown cell just inserted — note its `id` (call it `<align_md_id>` below).

- [ ] **Step 4: Insert the alignment code cell**

NotebookEdit: `cell_id=<align_md_id>` (from Step 3), `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
merged = pd.merge(
    bot.rename(columns={"value": "bot_mid_rate"}),
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

`abs_diff` is Yahoo's close minus BOT's mid_rate (positive means Yahoo quotes more THB per USD than BOT's official average that day); `pct_diff` is the same difference as a percentage of BOT's rate.
```

- [ ] **Step 7: Read the notebook to find this markdown cell's id**

Read the notebook again. Note the `id` of the markdown cell just inserted (call it `<table_md_id>`).

- [ ] **Step 8: Insert the comparison table code cell**

NotebookEdit: `cell_id=<table_md_id>` (from Step 7), `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
comparison = merged.copy()
comparison["abs_diff"] = comparison["yahoo_close"] - comparison["bot_mid_rate"]
comparison["pct_diff"] = comparison["abs_diff"] / comparison["bot_mid_rate"] * 100

comparison.tail(10)
```

- [ ] **Step 9: Read the notebook to find the table code cell's id**

Read the notebook again. Note the `id` of the code cell just inserted (call it `<table_code_id>`) — Task 3 needs this id to insert after it.

- [ ] **Step 10: Execute and verify**

Run: `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/thb_rate_bot_vs_yahoo.ipynb --ExecutePreprocessor.timeout=180`

Expected: exits 0, no `Traceback`. The alignment cell's printed line shows `matched (inner join): N` where `N > 0` and `N <= min(len(bot), len(yahoo))`. The comparison table cell's output has columns `bot_mid_rate`, `yahoo_close`, `abs_diff`, `pct_diff`.

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
merged["bot_mid_rate"].plot(ax=ax, label="BOT daily average reference rate (mid_rate)")
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
ax.set_title("Yahoo close minus BOT mid_rate")
ax.set_ylabel("THB")
ax.grid(alpha=0.3)
plt.show()

stats = pd.Series(
    {
        "mean_diff": diff.mean(),
        "std_diff": diff.std(),
        "max_abs_diff": diff.abs().max(),
        "correlation": comparison["bot_mid_rate"].corr(comparison["yahoo_close"]),
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

- BOT's `mid_rate` is a once-daily official survey average (banks report their rates to BOT, which computes the average); Yahoo's `THB=X` close is a continuously-quoted market snapshot at day-end. A small, fairly consistent gap between the two is expected behavior, not a data error.
- BOT's actual "Spot Rate" API (`Stat-SpotRate/SPOTRATE`) is discontinued — see `BOT_query.ipynb` §9 — which is why this notebook compares against the daily average reference rate (`mid_rate`) instead.
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
