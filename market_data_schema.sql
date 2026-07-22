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
