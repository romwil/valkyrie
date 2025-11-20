"""Async tasks for LLM processing in Valkyrie Worker Service."""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm import Session

from .main import app
from .processors import (
    GeminiProcessor,
    EnrichmentProcessor,
    BatchProcessor
)
from ..database import get_db
from ..models import (
    Job,
    ProcessedRecord,
    JobStatus,
    RecordStatus
)

logger = logging.getLogger(__name__)


class BaseTask(Task):
    """Base task with database session management."""

    def __init__(self):
        self._db = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = next(get_db())
        return self._db

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up database session after task completion."""
        if self._db is not None:
            self._db.close()
            self._db = None


@app.task(base=BaseTask, bind=True, name='worker.tasks.enrich_sales_data')
def enrich_sales_data(self, job_id: int, record_ids: List[int]) -> Dict[str, Any]:
    """Enrich sales data records using Gemini LLM.

    Args:
        job_id: ID of the job being processed
        record_ids: List of record IDs to process

    Returns:
        Dict with processing results
    """
    try:
        logger.info(f"Starting enrichment for job {job_id} with {len(record_ids)} records")

        # Update job status
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        self.db.commit()

        # Initialize processors
        gemini_processor = GeminiProcessor()
        enrichment_processor = EnrichmentProcessor(gemini_processor)

        # Process records
        processed_count = 0
        error_count = 0

        for record_id in record_ids:
            try:
                record = self.db.query(ProcessedRecord).filter(
                    ProcessedRecord.id == record_id
                ).first()

                if not record:
                    logger.warning(f"Record {record_id} not found")
                    continue

                # Update record status
                record.status = RecordStatus.PROCESSING
                self.db.commit()

                # Enrich the record
                enriched_data = enrichment_processor.enrich_record(
                    record.original_data
                )

                # Update record with enriched data
                record.enriched_data = enriched_data
                record.status = RecordStatus.COMPLETED
                record.processed_at = datetime.utcnow()
                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing record {record_id}: {str(e)}")
                record.status = RecordStatus.FAILED
                record.error_message = str(e)
                error_count += 1

            finally:
                self.db.commit()

        # Update job completion
        job.processed_records = processed_count
        job.failed_records = error_count
        job.completed_at = datetime.utcnow()
        job.status = JobStatus.COMPLETED if error_count == 0 else JobStatus.PARTIAL
        self.db.commit()

        return {
            'job_id': job_id,
            'processed': processed_count,
            'errors': error_count,
            'status': job.status.value
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Task timeout for job {job_id}")
        if job:
            job.status = JobStatus.FAILED
            job.error_message = "Task timeout exceeded"
            self.db.commit()
        raise

    except Exception as e:
        logger.error(f"Task failed for job {job_id}: {str(e)}")
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            self.db.commit()
        raise


@app.task(base=BaseTask, bind=True, name='worker.tasks.process_batch')
def process_batch(self, job_id: int, batch_size: int = 100) -> Dict[str, Any]:
    """Process a batch of records for a job.

    Args:
        job_id: ID of the job being processed
        batch_size: Number of records to process in batch

    Returns:
        Dict with batch processing results
    """
    try:
        logger.info(f"Processing batch for job {job_id}, size: {batch_size}")

        # Get unprocessed records for the job
        records = self.db.query(ProcessedRecord).filter(
            ProcessedRecord.job_id == job_id,
            ProcessedRecord.status == RecordStatus.PENDING
        ).limit(batch_size).all()

        if not records:
            logger.info(f"No pending records for job {job_id}")
            return {
                'job_id': job_id,
                'processed': 0,
                'message': 'No pending records'
            }

        record_ids = [r.id for r in records]

        # Process the batch
        batch_processor = BatchProcessor()
        results = batch_processor.process_batch(self, job_id, record_ids)

        return results

    except Exception as e:
        logger.error(f"Batch processing failed for job {job_id}: {str(e)}")
        raise


@app.task(base=BaseTask, bind=True, name='worker.tasks.priority_enrichment')
def priority_enrichment(self, record_id: int, enrichment_config: Dict[str, Any]) -> Dict[str, Any]:
    """Priority enrichment for individual records with custom configuration.

    Args:
        record_id: ID of the record to enrich
        enrichment_config: Custom configuration for enrichment

    Returns:
        Dict with enrichment results
    """
    try:
        logger.info(f"Priority enrichment for record {record_id}")

        record = self.db.query(ProcessedRecord).filter(
            ProcessedRecord.id == record_id
        ).first()

        if not record:
            raise ValueError(f"Record {record_id} not found")

        # Initialize processor with custom config
        gemini_processor = GeminiProcessor(config=enrichment_config)
        enrichment_processor = EnrichmentProcessor(gemini_processor)

        # Process with priority
        record.status = RecordStatus.PROCESSING
        self.db.commit()

        enriched_data = enrichment_processor.enrich_record(
            record.original_data,
            priority=True
        )

        # Update record
        record.enriched_data = enriched_data
        record.status = RecordStatus.COMPLETED
        record.processed_at = datetime.utcnow()
        self.db.commit()

        return {
            'record_id': record_id,
            'status': 'completed',
            'enriched_fields': list(enriched_data.keys())
        }

    except Exception as e:
        logger.error(f"Priority enrichment failed for record {record_id}: {str(e)}")
        if record:
            record.status = RecordStatus.FAILED
            record.error_message = str(e)
            self.db.commit()
        raise


@app.task(name='worker.tasks.health_check')
def health_check() -> Dict[str, str]:
    """Health check task for monitoring."""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'worker': 'valkyrie-worker'
    }
