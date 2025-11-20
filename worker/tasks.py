# Celery tasks for Valkyrie Worker
import os
import logging
from celery import Celery
from celery.utils.log import get_task_logger

# Configure logging
logger = get_task_logger(__name__)

# Initialize Celery
app = Celery(
    'valkyrie_worker',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

@app.task(bind=True, name='worker.process_data')
def process_data(self, data):
    """Process data asynchronously"""
    logger.info(f"Processing data: {data}")
    try:
        # Add your data processing logic here
        result = {"status": "processed", "data": data}
        return result
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)

@app.task(bind=True, name='worker.generate_report')
def generate_report(self, report_type, params):
    """Generate reports asynchronously"""
    logger.info(f"Generating {report_type} report with params: {params}")
    try:
        # Add your report generation logic here
        result = {
            "status": "completed",
            "report_type": report_type,
            "params": params
        }
        return result
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise self.retry(exc=e, countdown=120, max_retries=3)

@app.task(name='worker.health_check')
def health_check():
    """Health check task"""
    return {"status": "healthy", "timestamp": os.environ.get('HOSTNAME', 'unknown')}

if __name__ == '__main__':
    app.start()
