import base64
import json
import os

from google.cloud import pubsub_v1

from jobs2bigquery import bigquery
from jobs2bigquery.custom_jobsites.intel import IntelListing
from jobs2bigquery.custom_jobsites.google import GoogleListing
from jobs2bigquery.joblistings import (
    GreenHouseListing, LeverListing, HireHiveListing, SmartRecruiterListing,
    WorkableListing, WorkdayListing, RecruiteeListing, ComeetListing
)
from jobs2bigquery.utils import divide_chunks

PROCESSORS = {
    "greenhouse": GreenHouseListing,
    "lever": LeverListing,
    "hirehive": HireHiveListing,
    "workable": WorkableListing,
    "workday": WorkdayListing,
    "smartrecruiters": SmartRecruiterListing,
    "recruitee": RecruiteeListing,
    "comeet": ComeetListing,

    "intel": IntelListing,
    "google": GoogleListing,
}


def ingest_pubsub(event, context):
    if '@type' in event and event['@type'] == 'type.googleapis.com/google.pubsub.v1.PubsubMessage':
        data = str(base64.b64decode(event['data']), 'utf-8')
        event = json.loads(data)

    if event.get('split_work', False):
        return split_work(event)
    return process_single_workload(event)


def split_work(event) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_name = 'projects/{project_id}/topics/{topic}'.format(
        project_id=os.getenv('GOOGLE_CLOUD_PROJECT'),
        topic=os.getenv('TOPIC_NAME'),
    )

    for list_name, list_cls in PROCESSORS.items():
        if list_name in event['lists']:
            for chunk in divide_chunks(event['lists'][list_name], 5):
                chunk_payload = event.copy()

                # Don't split the new payload
                chunk_payload['split_work'] = False

                # Reset lists and add only our chunk
                chunk_payload['lists'] = {}
                chunk_payload['lists'][list_name] = chunk
                publisher.publish(topic_name, bytes(json.dumps(chunk_payload), 'utf-8'))


def process_single_workload(event) -> None:
    bq = bigquery.BigQuery(event)

    for list_name, list_cls in PROCESSORS.items():
        if list_name in event['lists']:
            process_list(bq, event, list_name, list_cls)

    if event.get('trim_duplicates', False):
        bq.remove_duplicates()
        print("Removed duplicate entries")


def process_list(bq, event, list_name, list_type_cls) -> None:
    list_items = event['lists'][list_name]
    for item in list_items:

        if type(item) == list:
            results = list_type_cls(*item).get_jobs()
        else:
            results = list_type_cls(item).get_jobs()
        if len(results) > 0:
            bq.insert_rows(results)
