"""BigQuery I/O: truncate-and-reload one category's staging table."""

import pandas as pd
from google.cloud import bigquery

SCHEMA = [
    bigquery.SchemaField("series_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("value", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
]


def load_category_table(
    client, project: str, dataset: str, category: str, df: pd.DataFrame
) -> int:
    """Truncate-and-reload `{project}.{dataset}.{category}` with df's rows.

    Returns the number of rows loaded.
    """
    table_id = f"{project}.{dataset}.{category}"
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    return len(df)
