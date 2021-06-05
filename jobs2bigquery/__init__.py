import base64
import json

from jobs2bigquery import bigquery
from jobs2bigquery.joblistings import GreenHouseListing, LeverListing, HireHiveListing

PROCESSORS = {
    "greenhouse": GreenHouseListing,
    "lever": LeverListing,
    "hirehive": HireHiveListing,
}


def ingest_pubsub(event, context):
    if '@type' in event and event['@type'] == 'type.googleapis.com/google.pubsub.v1.PubsubMessage':
        data = str(base64.b64decode(event['data']), 'utf-8')
        event = json.loads(data)

    bq = bigquery.BigQuery(event)

    for list_name, list_cls in PROCESSORS.items():
        if list_name in event['lists']:
            process_list(bq, event, list_name, list_cls)


def process_list(bq, event, list_name, list_type_cls):
    list_items = event['lists'][list_name]
    for company_id in list_items:
        results = list_type_cls(company_id).get_jobs()
        if len(results) > 0:
            bq.insert_rows(results)
