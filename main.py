from jobs2bigquery import ingest_pubsub

def execute_jobs2bigquery(event, context):
    return ingest_pubsub(event, context)
