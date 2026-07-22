# Market Data Schema (BigQuery DDL) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `market_data_schema.sql`, a static BigQuery DDL file defining the 12-table catalog-driven schema from `project_design.md` §4/§8, as a standalone artifact independent of the existing CSV pipeline and the existing `scripts/bigquery_load.py` staging tables.

**Architecture:** Single SQL file at the repo root. One `CREATE SCHEMA` for a new `market_data` dataset, followed by 12 `CREATE TABLE` statements in FK-dependency order (dimension/reference tables first, fact tables last), each with `NOT ENFORCED` primary/foreign keys and the partitioning/clustering from the design doc.

**Tech Stack:** BigQuery Standard SQL DDL only — no Python, no dependencies, no execution tooling.

## Global Constraints

- Single self-contained file: `market_data_schema.sql` at the repo root.
- Dataset name is `market_data` — must not reuse or reference the existing `{GCP_PROJECT}.{BQ_DATASET}` staging dataset from `scripts/bigquery_load.py`.
- Project id is the literal placeholder `your-gcp-project` throughout (not an env var — this file is a static, hand-reviewed artifact, not applied by any script).
- Every table has `PRIMARY KEY (...) NOT ENFORCED`; every FK column has `FOREIGN KEY (...) REFERENCES ... NOT ENFORCED`.
- `CREATE TABLE` statements are ordered so every FK target already exists (BigQuery validates the referenced table/column exists at creation time, even for `NOT ENFORCED` constraints).
- `bars_ohlcv`'s `interval` column must stay backtick-quoted (`` `interval` ``) everywhere it appears — `INTERVAL` is a BigQuery reserved keyword.
- No apply/deploy script, no pytest integration — this file is not exercised by `python -m pytest`.

---

### Task 1: Create `market_data_schema.sql`

**Files:**
- Create: `market_data_schema.sql` (repo root)

**Interfaces:**
- Produces: a BigQuery dataset `your-gcp-project.market_data` containing tables `data_sources`, `exchanges`, `data_catalog`, `symbols`, `ingestion_batches`, `ticks`, `bars_ohlcv`, `economic_indicators`, `fx_rates`, `commodity_futures`, `weather_observations`, `holidays`. No other task or file in this repo depends on this output (standalone artifact).

- [ ] **Step 1: Write the schema file**

Create `market_data_schema.sql` at the repo root with this exact content:

```sql
-- Market data platform — BigQuery schema DDL.
-- See project_design.md (repo root) §4/§8 for the source design this
-- implements, including the rationale for NOT ENFORCED keys and the
-- partitioning/clustering choices below.
--
-- Replace `your-gcp-project` with your actual GCP project ID before
-- running this (e.g. via `bq query --use_legacy_sql=false < market_data_schema.sql`
-- or the BigQuery console). This file is not applied by any script in
-- this repo — it's a static artifact for manual review/deployment.

CREATE SCHEMA IF NOT EXISTS `your-gcp-project.market_data`
OPTIONS (location = 'US');

-- Reference/dimension tables (no FKs) -----------------------------------

CREATE TABLE `your-gcp-project.market_data.data_sources` (
  source_id STRING NOT NULL,
  name STRING NOT NULL,
  type STRING NOT NULL,
  vendor STRING,
  PRIMARY KEY (source_id) NOT ENFORCED
);

CREATE TABLE `your-gcp-project.market_data.exchanges` (
  exchange_id STRING NOT NULL,
  code STRING NOT NULL,
  name STRING NOT NULL,
  timezone STRING NOT NULL,
  PRIMARY KEY (exchange_id) NOT ENFORCED
);

-- Catalog layer -----------------------------------------------------------

CREATE TABLE `your-gcp-project.market_data.data_catalog` (
  catalog_id STRING NOT NULL,
  source_id STRING NOT NULL,
  domain STRING NOT NULL,
  name STRING NOT NULL,
  frequency STRING,
  unit STRING,
  PRIMARY KEY (catalog_id) NOT ENFORCED,
  FOREIGN KEY (source_id) REFERENCES `your-gcp-project.market_data.data_sources`(source_id) NOT ENFORCED
);

CREATE TABLE `your-gcp-project.market_data.symbols` (
  symbol_id STRING NOT NULL,
  catalog_id STRING NOT NULL,
  exchange_id STRING NOT NULL,
  ticker STRING NOT NULL,
  asset_class STRING NOT NULL,
  PRIMARY KEY (symbol_id) NOT ENFORCED,
  FOREIGN KEY (catalog_id) REFERENCES `your-gcp-project.market_data.data_catalog`(catalog_id) NOT ENFORCED,
  FOREIGN KEY (exchange_id) REFERENCES `your-gcp-project.market_data.exchanges`(exchange_id) NOT ENFORCED
);

CREATE TABLE `your-gcp-project.market_data.ingestion_batches` (
  batch_id STRING NOT NULL,
  catalog_id STRING NOT NULL,
  ingested_at TIMESTAMP NOT NULL,
  status STRING NOT NULL,
  PRIMARY KEY (batch_id) NOT ENFORCED,
  FOREIGN KEY (catalog_id) REFERENCES `your-gcp-project.market_data.data_catalog`(catalog_id) NOT ENFORCED
)
PARTITION BY DATE(ingested_at)
OPTIONS (
  partition_expiration_days = 730
);

-- Lane 1 — live tick feeds -------------------------------------------------

CREATE TABLE `your-gcp-project.market_data.ticks` (
  symbol_id STRING NOT NULL,
  event_ts TIMESTAMP NOT NULL,
  price FLOAT64 NOT NULL,
  size FLOAT64,
  side STRING,
  FOREIGN KEY (symbol_id) REFERENCES `your-gcp-project.market_data.symbols`(symbol_id) NOT ENFORCED
)
PARTITION BY DATE(event_ts)
CLUSTER BY symbol_id;

-- `interval` is a BigQuery reserved keyword (the INTERVAL data type) and
-- must stay backtick-quoted wherever it's used as a column name.
CREATE TABLE `your-gcp-project.market_data.bars_ohlcv` (
  symbol_id STRING NOT NULL,
  bar_start_ts TIMESTAMP NOT NULL,
  `interval` STRING NOT NULL,
  open FLOAT64 NOT NULL,
  high FLOAT64 NOT NULL,
  low FLOAT64 NOT NULL,
  close FLOAT64 NOT NULL,
  volume FLOAT64,
  FOREIGN KEY (symbol_id) REFERENCES `your-gcp-project.market_data.symbols`(symbol_id) NOT ENFORCED
)
PARTITION BY DATE(bar_start_ts)
CLUSTER BY symbol_id, `interval`;

-- Lane 2 — external data API domains ---------------------------------------

CREATE TABLE `your-gcp-project.market_data.economic_indicators` (
  catalog_id STRING NOT NULL,
  batch_id STRING,
  country STRING,
  obs_date DATE NOT NULL,
  value FLOAT64 NOT NULL,
  FOREIGN KEY (catalog_id) REFERENCES `your-gcp-project.market_data.data_catalog`(catalog_id) NOT ENFORCED,
  FOREIGN KEY (batch_id) REFERENCES `your-gcp-project.market_data.ingestion_batches`(batch_id) NOT ENFORCED
)
CLUSTER BY catalog_id;

CREATE TABLE `your-gcp-project.market_data.fx_rates` (
  catalog_id STRING NOT NULL,
  batch_id STRING,
  currency_pair STRING NOT NULL,
  rate_date DATE NOT NULL,
  rate FLOAT64 NOT NULL,
  FOREIGN KEY (catalog_id) REFERENCES `your-gcp-project.market_data.data_catalog`(catalog_id) NOT ENFORCED,
  FOREIGN KEY (batch_id) REFERENCES `your-gcp-project.market_data.ingestion_batches`(batch_id) NOT ENFORCED
)
PARTITION BY DATE(rate_date)
CLUSTER BY currency_pair;

CREATE TABLE `your-gcp-project.market_data.commodity_futures` (
  catalog_id STRING NOT NULL,
  batch_id STRING,
  contract_code STRING NOT NULL,
  expiry_date DATE,
  trade_date DATE NOT NULL,
  close FLOAT64 NOT NULL,
  FOREIGN KEY (catalog_id) REFERENCES `your-gcp-project.market_data.data_catalog`(catalog_id) NOT ENFORCED,
  FOREIGN KEY (batch_id) REFERENCES `your-gcp-project.market_data.ingestion_batches`(batch_id) NOT ENFORCED
)
PARTITION BY DATE(trade_date)
CLUSTER BY contract_code;

CREATE TABLE `your-gcp-project.market_data.weather_observations` (
  catalog_id STRING NOT NULL,
  batch_id STRING,
  station_id STRING NOT NULL,
  obs_date DATE NOT NULL,
  temp_avg FLOAT64,
  precipitation FLOAT64,
  FOREIGN KEY (catalog_id) REFERENCES `your-gcp-project.market_data.data_catalog`(catalog_id) NOT ENFORCED,
  FOREIGN KEY (batch_id) REFERENCES `your-gcp-project.market_data.ingestion_batches`(batch_id) NOT ENFORCED
)
PARTITION BY DATE(obs_date)
CLUSTER BY station_id;

-- Lane 3 — reference data ---------------------------------------------------

CREATE TABLE `your-gcp-project.market_data.holidays` (
  catalog_id STRING NOT NULL,
  batch_id STRING,
  exchange_id STRING NOT NULL,
  holiday_date DATE NOT NULL,
  name STRING NOT NULL,
  FOREIGN KEY (catalog_id) REFERENCES `your-gcp-project.market_data.data_catalog`(catalog_id) NOT ENFORCED,
  FOREIGN KEY (batch_id) REFERENCES `your-gcp-project.market_data.ingestion_batches`(batch_id) NOT ENFORCED,
  FOREIGN KEY (exchange_id) REFERENCES `your-gcp-project.market_data.exchanges`(exchange_id) NOT ENFORCED
)
CLUSTER BY exchange_id;
```

- [ ] **Step 2: Verify table count and dependency order**

Run (Bash or PowerShell):

```bash
grep -c "^CREATE TABLE" market_data_schema.sql
```

Expected: `12`

Then confirm ordering by eye: `data_sources` and `exchanges` must appear before `data_catalog`; `data_catalog` before `symbols` and `ingestion_batches`; `symbols` before `ticks`/`bars_ohlcv`; `data_catalog`+`ingestion_batches` before `economic_indicators`/`fx_rates`/`commodity_futures`/`weather_observations`/`holidays`; `exchanges` before `holidays`.

- [ ] **Step 3: Verify the two ERD corrections are present**

```bash
grep -c "batch_id STRING," market_data_schema.sql
grep -A6 "CREATE TABLE .*bars_ohlcv" market_data_schema.sql | grep -E "high FLOAT64 NOT NULL|low FLOAT64 NOT NULL"
```

Expected: first command prints `5` (one `batch_id` column in each of `economic_indicators`, `fx_rates`, `commodity_futures`, `weather_observations`, `holidays`); second command prints both the `high` and `low` lines.

- [ ] **Step 4: Verify `interval` stays backtick-quoted**

```bash
grep -n "interval" market_data_schema.sql
```

Expected: every occurrence of the word `interval` on a column-name line is wrapped in backticks (`` `interval` ``) — none appear bare as a bare identifier.

- [ ] **Step 5: Verify `NOT ENFORCED` key count**

```bash
grep -c "NOT ENFORCED" market_data_schema.sql
```

Expected: `23` — 1 mention in the header comment's prose, plus 22 actual key clauses: 5 `PRIMARY KEY (...) NOT ENFORCED` (on `data_sources`, `exchanges`, `data_catalog`, `symbols`, `ingestion_batches` — the 7 fact tables have no single-column PK) + 17 `FOREIGN KEY (...) REFERENCES ... NOT ENFORCED` (1 on `data_catalog`, 2 on `symbols`, 1 on `ingestion_batches`, 1 on `ticks`, 1 on `bars_ohlcv`, 2 each on `economic_indicators`/`fx_rates`/`commodity_futures`/`weather_observations`, 3 on `holidays`).

- [ ] **Step 6: Commit**

```bash
git add market_data_schema.sql
git commit -m "$(cat <<'EOF'
Add BigQuery DDL for the market data platform schema

Implements project_design.md's §4/§8 schema as a standalone,
hand-reviewed DDL file in a new market_data dataset, independent of
the existing CSV pipeline and scripts/bigquery_load.py staging
tables. See docs/superpowers/specs/2026-07-22-market-data-schema-design.md
for the design and the two corrections applied on top of the source
ERD (bars_ohlcv high/low, batch_id lineage on domain fact tables).
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** all 12 tables, the dataset-creation statement, both ERD corrections (`bars_ohlcv` high/low, `batch_id` on the 5 domain fact tables), the `holidays` clustering addition, `NOT ENFORCED` keys, and the FK-dependency ordering are all present in Task 1 — the spec's entire scope is one file, so one task covers it fully.
- **Placeholder scan:** no TBD/TODO; `your-gcp-project` is a documented, intentional placeholder (per Global Constraints), not an unresolved item.
- **Type consistency:** column names/types in Task 1's DDL match the spec's `## Schema` section verbatim (copied directly from the approved spec) — no drift between spec and plan.
