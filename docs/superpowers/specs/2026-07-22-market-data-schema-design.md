# Market Data Schema (BigQuery DDL) — Design

**Date:** 2026-07-22
**Status:** Approved

## Purpose

`project_design.md` (repo root) is a draft architecture doc for a much
larger GCP-based market data platform — streaming ingestion, batch
ingestion via Composer, a Cloud Run query API, IAM, etc. That platform is
too large for one spec; this design scopes only its first, foundational
piece: the BigQuery schema itself (`project_design.md` §4/§8), delivered as
the static DDL file its own appendix names: `market_data_schema.sql`.

Nothing else from the design doc — streaming pipeline, Composer DAG
factory, Cloud Run API, IAM — is in scope here. Each is a separate future
spec.

## Requirements

- One self-contained SQL file, `market_data_schema.sql`, at the repo root.
- Defines a new BigQuery dataset, `market_data`, independent of the
  existing `{GCP_PROJECT}.{BQ_DATASET}` staging tables used by
  `scripts/bigquery_load.py` (flat `series_id`/`source`/`date`/`value`
  tables). No collision, no shared tables, no migration.
- Covers all 12 tables from `project_design.md` §4's ERD: `data_sources`,
  `data_catalog`, `ingestion_batches`, `exchanges`, `symbols`, `ticks`,
  `bars_ohlcv`, `economic_indicators`, `fx_rates`, `commodity_futures`,
  `weather_observations`, `holidays`.
- `PRIMARY KEY (...) NOT ENFORCED` / `FOREIGN KEY (...) REFERENCES (...)
  NOT ENFORCED` on every table, per §4/§8 — for optimizer hints and
  BI-tool join inference, not constraint enforcement.
- Partitioning and clustering exactly as specified in §4's table:
  day-partition + cluster on `ticks`, `bars_ohlcv`, `fx_rates`,
  `commodity_futures`, `weather_observations`; cluster-only (no partition)
  on `economic_indicators`; day-partition with a 730-day partition
  expiration on `ingestion_batches`.
- Two corrections applied on top of the literal ERD (per explicit
  decision — see below), everything else follows §4 as written.

### Corrections to the source ERD

The ERD in §4 has two gaps against the doc's own prose elsewhere:

1. **`bars_ohlcv` is missing `high`/`low`.** The ERD lists only
   `open`/`close`/`volume`, despite the table being named for the standard
   OHLCV shape. Adding `high FLOAT64 NOT NULL` and `low FLOAT64 NOT NULL`.
2. **Domain fact tables are missing `batch_id`.** §5 states "every row [is]
   traceable to a `catalog_id` and `batch_id`," but the ERD only gives
   `economic_indicators`, `fx_rates`, `commodity_futures`,
   `weather_observations`, and `holidays` a `catalog_id` column — no
   `batch_id`. Adding a nullable `batch_id FOREIGN KEY REFERENCES
   ingestion_batches(batch_id) NOT ENFORCED` to each. `ticks`/`bars_ohlcv`
   deliberately keep no `batch_id`, matching §6's documented exception
   (streaming lineage is tracked by periodic sampling, not a batch id per
   row).

`holidays` also isn't listed in §4's partitioning/clustering table at all
(low-volume reference data). It gets no partition, but `CLUSTER BY
exchange_id` is added since every realistic query filters holidays by
exchange — an addition beyond the source doc, called out explicitly here
rather than silently assumed.

## Non-goals

- No apply/deploy tooling. This file is a static artifact, reviewed by
  hand — not executed by any script or test in this repo. Deployment
  automation is out of scope for this phase (matches `project_design.md`
  §1's own non-goals around Cloud Run/IAM automation).
- No data migration from the existing `scripts/bigquery_load.py` staging
  tables — the two schemas coexist independently.
- No streaming pipeline, Composer DAG factory, Cloud Run query API, IAM
  model, or materialized views — all separate future specs per
  `project_design.md` §9.

## Schema

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

Tables are ordered so every `FOREIGN KEY` reference resolves against an
already-created table: BigQuery validates that a referenced table/column
exists at `CREATE TABLE` time even though the constraint itself is `NOT
ENFORCED`.

## Testing

None — this is a static SQL file, not exercised by the Python test suite
or any script in this repo (matches the "DDL file only" scope decision).
Correctness is reviewed by hand at PR time; `bars_ohlcv`'s `` `interval` ``
column is the one syntax detail worth double-checking on first real run
against BigQuery, since it's easy to accidentally unquote later.

## Out of scope

- Applying/deploying the DDL (no script, no CI check).
- Migrating or reconciling with the existing `scripts/bigquery_load.py`
  staging tables.
- Streaming pipeline (`ticks_streaming_pipeline.py`), Composer DAG
  factory, Cloud Run query API, IAM model, materialized views,
  release-calendar-aware triggering — each tracked as a separate future
  spec per `project_design.md` §9.
