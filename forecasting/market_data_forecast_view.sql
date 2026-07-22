-- forecast_assets: unifies every daily, price-like asset in market_data onto one
-- shape for AIML-ML-Multi-Forecast-Engine. See
-- docs/superpowers/specs/2026-07-22-forecast-layer-integration-design.md.
--
-- Replace `your-gcp-project` with your actual GCP project id, matching
-- market_data_schema.sql. Not applied by any script in this repo -- run by
-- hand (bq query / BigQuery console) once market_data_schema.sql has been
-- applied to a real project.

CREATE VIEW `your-gcp-project.market_data.forecast_assets` AS

SELECT
  catalog_id,
  rate_date AS date,
  rate AS value,
  'fx_rates' AS domain_table
FROM `your-gcp-project.market_data.fx_rates`

UNION ALL

SELECT
  catalog_id,
  trade_date AS date,
  close AS value,
  'commodity_futures' AS domain_table
FROM `your-gcp-project.market_data.commodity_futures`

UNION ALL

SELECT
  s.catalog_id,
  DATE(b.bar_start_ts) AS date,
  b.close AS value,
  'bars_ohlcv' AS domain_table
FROM `your-gcp-project.market_data.bars_ohlcv` AS b
INNER JOIN `your-gcp-project.market_data.symbols` AS s
  ON b.symbol_id = s.symbol_id
WHERE b.`interval` = 'daily';
