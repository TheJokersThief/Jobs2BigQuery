import base64
import json

from jobs2bigquery import bigquery
from jobs2bigquery.joblistings import GreenHouseListing, LeverListing, HireHiveListing


def ingest_pubsub(event, context):
    if '@type' in event and event['@type'] == 'type.googleapis.com/google.pubsub.v1.PubsubMessage':
        data = str(base64.b64decode(event['data']), 'utf-8')
        event = json.loads(data)

    bq = bigquery.BigQuery(event)

    gh_lists = event['lists']['greenhouse']
    for company_id in gh_lists:
        results = GreenHouseListing(company_id).get_jobs()
        if len(results) > 0:
            bq.insert_rows(results)

    lever_lists = event['lists']['lever']
    for company_id in lever_lists:
        results = LeverListing(company_id).get_jobs()
        if len(results) > 0:
            bq.insert_rows(results)

    hirehive_lists = event['lists']['hirehive']
    for company_id in hirehive_lists:
        results = HireHiveListing(company_id).get_jobs()
        if len(results) > 0:
            bq.insert_rows(results)
