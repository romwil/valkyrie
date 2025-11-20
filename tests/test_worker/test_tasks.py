"""Unit tests for worker tasks."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from src.worker.tasks import (
    process_enrichment_job,
    enrich_single_record,
    update_job_progress,
    handle_enrichment_error
)
from src.models import Job, Record
from tests.factories import JobFactory, RecordFactory


class TestEnrichmentWorker:
    """Test enrichment worker tasks."""

    @pytest.mark.asyncio
    async def test_process_enrichment_job(self, db_session, sample_job, mock_gemini):
        """Test processing an entire enrichment job."""
        # Create records for the job
        records = [RecordFactory(job=sample_job) for _ in range(5)]
        db_session.add_all(records)
        db_session.commit()

        # Mock the database session
        with patch("src.worker.tasks.get_db") as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session

            # Process the job
            await process_enrichment_job(sample_job.id)

        # Refresh the job
        db_session.refresh(sample_job)

        # Check job status
        assert sample_job.status == "completed"
        assert sample_job.processed_records == 5
        assert sample_job.successful_records == 5
        assert sample_job.failed_records == 0
        assert sample_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_enrich_single_record(self, db_session, sample_job, mock_gemini):
        """Test enriching a single record."""
        record = RecordFactory(job=sample_job)
        db_session.add(record)
        db_session.commit()

        # Mock the LLM service
        mock_llm_response = {
            "industry": "Technology",
            "size": "100-500",
            "revenue": "$10M-$50M",
            "description": "A leading technology company",
            "key_products": ["Software", "Services"],
            "target_market": "Enterprise",
            "competitors": ["Competitor A", "Competitor B"]
        }

        with patch("src.worker.tasks.llm_service.enrich_company") as mock_enrich:
            mock_enrich.return_value = mock_llm_response

            # Enrich the record
            result = await enrich_single_record(record, db_session)

        assert result is True
        assert record.status == "enriched"
        assert record.enriched_data == mock_llm_response
        assert record.processed_at is not None

    @pytest.mark.asyncio
    async def test_enrich_single_record_failure(self, db_session, sample_job):
        """Test handling enrichment failure for a single record."""
        record = RecordFactory(job=sample_job)
        db_session.add(record)
        db_session.commit()

        # Mock the LLM service to raise an exception
        with patch("src.worker.tasks.llm_service.enrich_company") as mock_enrich:
            mock_enrich.side_effect = Exception("API rate limit exceeded")

            # Try to enrich the record
            result = await enrich_single_record(record, db_session)

        assert result is False
        assert record.status == "failed"
        assert "rate limit" in record.error_message
        assert record.processed_at is not None

    @pytest.mark.asyncio
    async def test_update_job_progress(self, db_session, sample_job):
        """Test updating job progress during processing."""
        # Set initial job state
        sample_job.status = "processing"
        sample_job.total_records = 100
        db_session.commit()

        # Update progress
        await update_job_progress(
            job_id=sample_job.id,
            processed=50,
            successful=45,
            failed=5,
            db=db_session
        )

        db_session.refresh(sample_job)
        assert sample_job.processed_records == 50
        assert sample_job.successful_records == 45
        assert sample_job.failed_records == 5
        assert sample_job.status == "processing"

    @pytest.mark.asyncio
    async def test_handle_enrichment_error(self, db_session, sample_job):
        """Test handling job-level enrichment errors."""
        sample_job.status = "processing"
        db_session.commit()

        error_message = "Critical error: Database connection lost"

        await handle_enrichment_error(
            job_id=sample_job.id,
            error_message=error_message,
            db=db_session
        )

        db_session.refresh(sample_job)
        assert sample_job.status == "failed"
        assert sample_job.error_message == error_message
        assert sample_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_concurrent_record_processing(self, db_session, sample_job, mock_gemini):
        """Test processing multiple records concurrently."""
        # Create multiple records
        records = [RecordFactory(job=sample_job) for _ in range(10)]
        db_session.add_all(records)
        db_session.commit()

        # Mock the database session
        with patch("src.worker.tasks.get_db") as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session

            # Process with concurrency limit
            with patch("src.worker.tasks.CONCURRENT_LIMIT", 3):
                await process_enrichment_job(sample_job.id)

        # Check all records were processed
        db_session.refresh(sample_job)
        assert sample_job.processed_records == 10
        assert sample_job.status == "completed"

    @pytest.mark.asyncio
    async def test_job_cancellation(self, db_session, sample_job):
        """Test cancelling a job during processing."""
        # Create records
        records = [RecordFactory(job=sample_job) for _ in range(20)]
        db_session.add_all(records)
        db_session.commit()

        # Mock the job to be cancelled mid-processing
        async def mock_check_cancelled(job_id, db):
            # Cancel after processing 5 records
            job = db.query(Job).filter_by(id=job_id).first()
            if job.processed_records >= 5:
                job.status = "cancelled"
                db.commit()
                return True
            return False

        with patch("src.worker.tasks.check_job_cancelled", mock_check_cancelled):
            with patch("src.worker.tasks.get_db") as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = db_session

                await process_enrichment_job(sample_job.id)

        db_session.refresh(sample_job)
        assert sample_job.status == "cancelled"
        assert sample_job.processed_records >= 5
        assert sample_job.processed_records < 20

    @pytest.mark.asyncio
    async def test_retry_failed_records(self, db_session, sample_job, mock_gemini):
        """Test retrying failed records."""
        # Create some failed records
        failed_records = [
            RecordFactory(job=sample_job, set_failed_status="failed")
            for _ in range(3)
        ]
        db_session.add_all(failed_records)
        db_session.commit()

        # Mock successful retry
        with patch("src.worker.tasks.llm_service.enrich_company") as mock_enrich:
            mock_enrich.return_value = {"industry": "Technology"}

            for record in failed_records:
                # Reset status to retry
                record.status = "pending"
                record.error_message = None

            db_session.commit()

            # Process again
            with patch("src.worker.tasks.get_db") as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = db_session
                await process_enrichment_job(sample_job.id)

        # Check all records are now enriched
        for record in failed_records:
            db_session.refresh(record)
            assert record.status == "enriched"
            assert record.enriched_data is not None


class TestBackgroundTasks:
    """Test other background tasks."""

    @pytest.mark.asyncio
    async def test_cleanup_old_jobs(self, db_session):
        """Test cleaning up old completed jobs."""
        # Create old and new jobs
        from datetime import timedelta

        old_job = JobFactory(status="completed")
        old_job.completed_at = datetime.utcnow() - timedelta(days=35)

        recent_job = JobFactory(status="completed")
        recent_job.completed_at = datetime.utcnow() - timedelta(days=5)

        db_session.add_all([old_job, recent_job])
        db_session.commit()

        from src.worker.tasks import cleanup_old_jobs

        with patch("src.worker.tasks.get_db") as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session

            # Clean up jobs older than 30 days
            await cleanup_old_jobs(days=30)

        # Check old job is deleted, recent job remains
        assert db_session.query(Job).filter_by(id=old_job.id).first() is None
        assert db_session.query(Job).filter_by(id=recent_job.id).first() is not None

    @pytest.mark.asyncio
    async def test_export_job_results(self, db_session, sample_job):
        """Test exporting job results to file."""
        # Create enriched records
        records = [
            RecordFactory(job=sample_job, set_enriched_status="enriched")
            for _ in range(5)
        ]
        db_session.add_all(records)
        db_session.commit()

        from src.worker.tasks import export_job_results

        with patch("src.worker.tasks.get_db") as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session

            # Export to CSV
            export_path = await export_job_results(
                job_id=sample_job.id,
                format="csv"
            )

        assert export_path is not None
        assert export_path.endswith(".csv")

        # Verify file was created
        import os
        assert os.path.exists(export_path)

        # Clean up
        os.remove(export_path)
