# Oil Prices Query Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `wti_oil` catalog series and build `notebooks/oil_prices_query.ipynb`, querying Brent and WTI crude oil prices via `macro_data` and plotting them together.

**Architecture:** One `catalog.yaml` addition (no code change — the yahoo source already handles any ticker) plus one new notebook using the existing `macro_data` public surface (`update`, `load`). No new package code, no new tests.

**Tech Stack:** Python, pandas, matplotlib, the existing `macro_data` package, Jupyter (`nbconvert --execute --inplace` for verification).

## Global Constraints

- `catalog.yaml` changes are additive only — do not reorder or edit existing entries.
- Data access goes through `macro_data`'s public surface only: `from macro_data import update, load` — never reach into `macro_data.sources`/`macro_data.pipeline` directly (per `CLAUDE.md`).
- `load(series_id)` returns a DataFrame indexed by `date` (ascending, deduped) with one column, `value` — confirmed in `macro_data/store.py:15-19`.
- No try/except: `update()` already isolates per-series failures into its returned status dict (`pipeline.py`); let any downstream `load()` failure raise naturally.
- Existing tests (`tests/test_catalog.py`, `tests/test_pipeline.py`) build their own synthetic `catalog.yaml` in a `tmp_path` fixture — they don't read the real repo-root `catalog.yaml` — so adding `wti_oil` cannot break them. Confirmed by grep: no test hardcodes a series count against the real file.
- Notebook kernel metadata must match the project's pinned kernel exactly:
  ```json
  "kernelspec": {
    "display_name": "macro-data (.venv)",
    "language": "python",
    "name": "macro-data-venv"
  }
  ```
  with `"nbformat": 4, "nbformat_minor": 5`.
- Verify notebook changes by running (from repo root):
  `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/oil_prices_query.ipynb --ExecutePreprocessor.timeout=180`
  A non-zero exit or `Traceback` in the command output means the task failed — fix before committing.
- `NotebookEdit`'s `insert` mode has no parameter to set the *new* cell's own id — it only takes the id of the cell to insert **after**; the tool's own response reports the id it assigned. Use that reported id (not an invented one) as the `cell_id` for the next insert.

---

### Task 1: Add `wti_oil` to the catalog

**Files:**
- Modify: `catalog.yaml`

**Interfaces:**
- Produces: a new `SeriesConfig` with `id="wti_oil"`, `source="yahoo"`, discoverable via `macro_data.list_series()` — Task 2's notebook calls `load("wti_oil")` after fetching it.

- [ ] **Step 1: Add the catalog entry**

Read `d:\MyOffice\AXONS\Macro_data\catalog.yaml`, then use Edit to insert this entry immediately after the existing `brent_oil` entry (after its `name:` line, before the `sp500` entry):

```yaml
  - id: wti_oil
    source: yahoo
    ticker: "CL=F"
    name: "WTI crude futures (USD/bbl)"
```

- [ ] **Step 2: Verify the catalog parses and includes the new series**

Run: `python -c "from macro_data import list_series; ids = [s.id for s in list_series()]; assert 'wti_oil' in ids, ids; print('ok:', ids)"`

Expected: prints `ok: [...]` with `wti_oil` present in the list, no traceback.

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `python -m pytest -q`

Expected: `76 passed` (same count as before this change — this is a config-only addition, no test should reference it).

- [ ] **Step 4: Commit**

```bash
git add catalog.yaml
git commit -m "Add wti_oil series to catalog"
```

---

### Task 2: Build the notebook — intro, fetch, load, chart

**Files:**
- Create: `notebooks/oil_prices_query.ipynb`

**Interfaces:**
- Consumes: `wti_oil` catalog entry from Task 1.
- Produces: final complete notebook (no further tasks depend on this one).

- [ ] **Step 1: Create the notebook file**

Use the Write tool to create `d:\MyOffice\AXONS\Macro_data\notebooks\oil_prices_query.ipynb` with exactly this content:

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "id": "intro",
   "metadata": {},
   "source": [
    "# Oil Prices Query — Brent vs. WTI\n",
    "\n",
    "Queries the two major crude oil benchmarks through the `macro_data` package: **Brent** (`brent_oil`, Yahoo ticker `BZ=F`) and **WTI** (`wti_oil`, Yahoo ticker `CL=F`), then plots them together. Both are already quoted in USD/bbl, so no normalization is needed to compare them on one chart.\n",
    "\n",
    "This is a simple fetch → load → plot notebook (same style as `data_gathering_demo.ipynb` §2/§4) — no trend analysis (moving averages, volatility) or spread calculation."
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
    "yahoo_status = update(\"yahoo\")  # refreshes all yahoo series, including brent_oil and wti_oil\n",
    "print(\"yahoo:\", yahoo_status)"
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

- [ ] **Step 2: Execute and verify the skeleton**

Run: `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/oil_prices_query.ipynb --ExecutePreprocessor.timeout=180`

Expected: exits 0, no `Traceback`. Inspect the `setup` cell's output (`python -c "import json; nb=json.load(open('notebooks/oil_prices_query.ipynb', encoding='utf-8')); print(nb['cells'][1]['outputs'])"`) and confirm the `yahoo:` line shows `brent_oil` and `wti_oil` both with a success status (`up-to-date` or `updated (N rows)`) — not `failed: ...`.

- [ ] **Step 3: Read the notebook to confirm the `setup` cell's id**

Read `d:\MyOffice\AXONS\Macro_data\notebooks\oil_prices_query.ipynb`. Confirm the second cell still has `id="setup"`.

- [ ] **Step 4: Insert the "Load & recent values" markdown cell**

NotebookEdit: `notebook_path="d:\MyOffice\AXONS\Macro_data\notebooks\oil_prices_query.ipynb"`, `cell_id="setup"`, `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## Load & recent values
```

- [ ] **Step 5: Insert the load code cell**

Use the id NotebookEdit reported for the cell inserted in Step 4 as `cell_id`. NotebookEdit: `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
brent = load("brent_oil")
wti = load("wti_oil")

print("Brent (BZ=F):")
display(brent.tail())
print("WTI (CL=F):")
display(wti.tail())
```

- [ ] **Step 6: Insert the "Chart" markdown cell**

Use the id NotebookEdit reported for the cell inserted in Step 5 as `cell_id`. NotebookEdit: `edit_mode="insert"`, `cell_type="markdown"`, `new_source`:

```markdown
## Chart
```

- [ ] **Step 7: Insert the chart code cell**

Use the id NotebookEdit reported for the cell inserted in Step 6 as `cell_id`. NotebookEdit: `edit_mode="insert"`, `cell_type="code"`, `new_source`:

```python
fig, ax = plt.subplots(figsize=(11, 5))
brent["value"].plot(ax=ax, label="Brent (BZ=F)")
wti["value"].plot(ax=ax, label="WTI (CL=F)")
ax.set_title("Crude oil futures — Brent vs. WTI")
ax.set_ylabel("USD per barrel")
ax.legend()
ax.grid(alpha=0.3)
plt.show()
```

- [ ] **Step 8: Final execute and verify**

Run: `python -m jupyter nbconvert --to notebook --execute --inplace notebooks/oil_prices_query.ipynb --ExecutePreprocessor.timeout=180`

Expected: exits 0, no `Traceback`. The notebook should now have 6 cells total (`intro`, `setup`, load markdown, load code, chart markdown, chart code — 3 markdown, 3 code). Spot-check with `python -c "import json; nb=json.load(open('notebooks/oil_prices_query.ipynb', encoding='utf-8')); print([c['cell_type'] for c in nb['cells']]); print(any('traceback' in str(o).lower() for c in nb['cells'] for o in c.get('outputs', [])))"` — last line must print `False`, and the cell-type list must show 6 entries.

- [ ] **Step 9: Commit**

```bash
git add notebooks/oil_prices_query.ipynb
git commit -m "Add oil prices query notebook (Brent vs WTI)"
```
