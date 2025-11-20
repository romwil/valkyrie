"""Celery application configuration for Valkyrie Worker Service."""

import os
from celery import Celery
from kombu import Exchange, Queue
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB', '0')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

# Build Redis URL
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Initialize Celery app
app = Celery('valkyrie_worker')

# Celery configuration
app.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Define queues
app.conf.task_queues = (
    Queue('enrichment', Exchange('enrichment'), routing_key='enrichment'),
    Queue('processing', Exchange('processing'), routing_key='processing'),
    Queue('priority', Exchange('priority'), routing_key='priority'),
)

# Define routes
app.conf.task_routes = {
    'worker.tasks.enrich_sales_data': {'queue': 'enrichment'},
    'worker.tasks.process_batch': {'queue': 'processing'},
    'worker.tasks.priority_enrichment': {'queue': 'priority'},
}

# Import tasks to register them
app.autodiscover_tasks(['src.worker'])

if __name__ == '__main__':
    app.start()
