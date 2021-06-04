import base64
import json

from jobs2bigquery import bigquery
from jobs2bigquery.joblistings import GreenHouseListing


def ingest_pubsub(event, context):
    if '@type' in event and event['@type'] == 'type.googleapis.com/google.pubsub.v1.PubsubMessage':
        data = str(base64.b64decode(event['data']), 'utf-8')
        event = json.loads(data)

    bq = bigquery.BigQuery(event)

    gh_lists = event['lists']['greenhouse']
    for company_id in gh_lists:
        results = GreenHouseListing(company_id).get_jobs()
        bq.insert_rows(results)

    # results = some_function_to_get_rows

    # bq.insert_listings(results)
