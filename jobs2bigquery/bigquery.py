from google.cloud import bigquery

from jobs2bigquery.utils import divide_chunks


class BigQuery():
    REMOVE_DUPLICATES_QUERY = """
    CREATE OR REPLACE TABLE `{table_id}` AS (
        SELECT * EXCEPT(row_num)
        FROM (
            SELECT
                *,
                ROW_NUMBER() OVER (PARTITION BY url ORDER BY logged_at DESC) AS row_num
            FROM
                `{table_id}`
        ) t
        WHERE row_num=1
    )
    """

    def __init__(self, event):
        self.table_id = event['bq_table_id']
        self.client = bigquery.Client()

    def insert_rows(self, rows):
        if len(rows) > 1000:
            for chunk in divide_chunks(rows, 1000):
                self.insert_rows(chunk)
        else:
            errors = self.client.insert_rows_json(
                self.table_id, rows
            )
            if errors == []:
                print(f"{len(rows)} rows have been added.")
            else:
                print("Encountered errors while inserting rows: {}".format(errors))
                raise Exception(errors)

    def remove_duplicates(self):
        query = self.REMOVE_DUPLICATES_QUERY.format(table_id=self.table_id)
        query_job = self.client.query(query)
        return query_job.result()  # Wait for job to finish
