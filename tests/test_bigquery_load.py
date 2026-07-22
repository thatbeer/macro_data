from unittest.mock import MagicMock

import pandas as pd
from google.cloud import bigquery

from bigquery_load import SCHEMA, load_category_table


def _df():
    return pd.DataFrame(
        {
            "series_id": ["usd_thb"],
            "source": ["yahoo"],
            "name": ["USD/THB exchange rate"],
            "date": [pd.Timestamp("2024-01-01").date()],
            "value": [35.1],
            "loaded_at": [pd.Timestamp("2026-07-22T00:00:00Z")],
        }
    )


def test_load_category_table_truncates_and_loads():
    client = MagicMock()
    job = MagicMock()
    client.load_table_from_dataframe.return_value = job
    df = _df()

    rows = load_category_table(client, "my-project", "my_dataset", "fx", df)

    assert rows == 1
    job.result.assert_called_once()
    client.load_table_from_dataframe.assert_called_once()
    call_args = client.load_table_from_dataframe.call_args
    assert call_args.args[0] is df
    assert call_args.args[1] == "my-project.my_dataset.fx"
    job_config = call_args.kwargs["job_config"]
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert job_config.create_disposition == bigquery.CreateDisposition.CREATE_IF_NEEDED
    assert job_config.schema == SCHEMA
