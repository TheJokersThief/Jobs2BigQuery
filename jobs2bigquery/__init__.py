import base64
import json

def ingest_pubsub(event, context):
    if '@type' in event and event['@type'] == 'type.googleapis.com/google.pubsub.v1.PubsubMessage':
        data = str(base64.b64decode(event['data']), 'utf-8')
        event = json.loads(data)

    # bq = bigquery.BigQuery(event)

    # results = some_function_to_get_rows

    # bq.insert_listings(results)
