"""Job service for managing enrichment jobs."""

import csv
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.models import Job, Record, Company, JobStatus, RecordStatus, AuditLog
from src.api.schemas.jobs import JobCreate, JobUpdate, JobConfiguration
from src.database import db_manager

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing enrichment jobs."""

    @staticmethod
    async def create_job(
        job_data: JobCreate,
        user_id: str,
        session: Session
    ) -> Job:
        """Create a new enrichment job."""
        try:
            # Validate input file exists
            input_path = Path(job_data.input_file)
            if not input_path.exists():
                raise ValueError(f"Input file not found: {job_data.input_file}")

            # Create job
            job = Job(
                input_file=job_data.input_file,
                configuration=job_data.configuration.model_dump(),
                metadata=job_data.metadata
            )
            session.add(job)
            session.flush()

            # Log action
            AuditLog.log_action(
                session=session,
                action="job_created",
                details={"input_file": job_data.input_file},
                job_id=job.id,
                user_id=user_id
            )

            # Parse CSV and create records
            records_created = await JobService._create_records_from_csv(
                session, job, input_path
            )

            job.total_records = records_created
            session.commit()

            logger.info(f"Created job {job.id} with {records_created} records")
            return job

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create job: {e}")
            raise

    @staticmethod
    async def _create_records_from_csv(
        session: Session,
        job: Job,
        csv_path: Path
    ) -> int:
        """Parse CSV file and create record entries."""
        records_created = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Extract company name (required field)
                company_name = row.get('company_name') or row.get('company') or row.get('name')
                if not company_name:
                    logger.warning(f"Skipping row without company name: {row}")
                    continue

                # Find or create company
                domain = row.get('domain') or row.get('website')
                company = await JobService._find_or_create_company(
                    session, company_name, domain
                )

                # Create record
                record = Record(
                    job_id=job.id,
                    company_id=company.id,
                    original_data=row,
                    metadata={"row_number": records_created + 1}
                )
                session.add(record)
                records_created += 1

                # Commit in batches
                if records_created % 100 == 0:
                    session.flush()

        return records_created

    @staticmethod
    async def _find_or_create_company(
        session: Session,
        name: str,
        domain: Optional[str] = None
    ) -> Company:
        """Find existing company or create new one."""
        # Try to find by domain first
        if domain:
            company = session.query(Company).filter_by(domain=domain).first()
            if company:
                return company

        # Try to find by name
        company = session.query(Company).filter(
            func.lower(Company.name) == func.lower(name)
        ).first()

        if company:
            return company

        # Create new company
        company = Company(name=name, domain=domain)
        session.add(company)
        session.flush()
        return company

    @staticmethod
    async def get_job(job_id: UUID, session: Session) -> Optional[Job]:
        """Get job by ID."""
        return session.query(Job).filter_by(id=job_id).first()

    @staticmethod
    async def list_jobs(
        session: Session,
        status: Optional[JobStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Job], int]:
        """List jobs with optional filtering."""
        query = session.query(Job)

        if status:
            query = query.filter(Job.status == status)

        total = query.count()
        jobs = query.order_by(Job.created_at.desc()).limit(limit).offset(offset).all()

        return jobs, total

    @staticmethod
    async def update_job(
        job_id: UUID,
        update_data: JobUpdate,
        user_id: str,
        session: Session
    ) -> Optional[Job]:
        """Update job details."""
        job = await JobService.get_job(job_id, session)
        if not job:
            return None

        # Update fields
        if update_data.status is not None:
            old_status = job.status
            job.status = update_data.status

            # Update timestamps based on status
            if update_data.status == JobStatus.PROCESSING and not job.started_at:
                job.started_at = datetime.utcnow()
            elif update_data.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                job.completed_at = datetime.utcnow()

            # Log status change
            AuditLog.log_action(
                session=session,
                action="job_status_changed",
                details={
                    "old_status": old_status.value,
                    "new_status": update_data.status.value
                },
                job_id=job_id,
                user_id=user_id
            )

        if update_data.metadata is not None:
            job.metadata.update(update_data.metadata)

        session.commit()
        return job

    @staticmethod
    async def cancel_job(
        job_id: UUID,
        user_id: str,
        session: Session
    ) -> Optional[Job]:
        """Cancel a job."""
        job = await JobService.get_job(job_id, session)
        if not job:
            return None

        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel job in {job.status.value} status")

        # Update job status
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()

        # Cancel pending records
        session.query(Record).filter(
            and_(
                Record.job_id == job_id,
                Record.status == RecordStatus.PENDING
            )
        ).update({"status": RecordStatus.SKIPPED})

        # Log action
        AuditLog.log_action(
            session=session,
            action="job_cancelled",
            details={"reason": "User requested cancellation"},
            job_id=job_id,
            user_id=user_id
        )

        session.commit()
        logger.info(f"Cancelled job {job_id}")
        return job

    @staticmethod
    async def get_job_statistics(job_id: UUID, session: Session) -> Dict[str, Any]:
        """Get detailed statistics for a job."""
        stats = session.query(
            func.count(Record.id).label('total_records'),
            func.count(Record.id).filter(Record.status == RecordStatus.ENRICHED).label('processed_records'),
            func.count(Record.id).filter(Record.status == RecordStatus.PENDING).label('pending_records'),
            func.count(Record.id).filter(Record.status == RecordStatus.FAILED).label('failed_records'),
            func.avg(Record.processing_time_ms).label('avg_processing_time_ms'),
            func.min(Record.processing_time_ms).label('min_processing_time_ms'),
            func.max(Record.processing_time_ms).label('max_processing_time_ms')
        ).filter(Record.job_id == job_id).first()

        # Calculate estimated completion time
        estimated_completion = None
        if stats.pending_records > 0 and stats.avg_processing_time_ms:
            remaining_time_seconds = (stats.pending_records * stats.avg_processing_time_ms) / 1000
            estimated_completion = datetime.utcnow() + timedelta(seconds=remaining_time_seconds)

        return {
            'total_records': stats.total_records or 0,
            'processed_records': stats.processed_records or 0,
            'pending_records': stats.pending_records or 0,
            'failed_records': stats.failed_records or 0,
            'success_rate': round((stats.processed_records / stats.total_records * 100) if stats.total_records > 0 else 0, 2),
            'avg_processing_time_ms': round(stats.avg_processing_time_ms or 0, 2),
            'min_processing_time_ms': stats.min_processing_time_ms,
            'max_processing_time_ms': stats.max_processing_time_ms,
            'estimated_completion_time': estimated_completion
        }

    @staticmethod
    async def export_job_results(
        job_id: UUID,
        session: Session,
        output_format: str = "csv"
    ) -> str:
        """Export job results to file."""
        job = await JobService.get_job(job_id, session)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Generate output filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = f"/tmp/job_{job_id}_results_{timestamp}.{output_format}"

        # Get all records with enriched data
        records = session.query(Record).filter(
            and_(
                Record.job_id == job_id,
                Record.status == RecordStatus.ENRICHED
            )
        ).all()

        if output_format == "csv":
            await JobService._export_to_csv(records, output_file)
        elif output_format == "json":
            await JobService._export_to_json(records, output_file)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        # Update job with output file
        job.output_file = output_file
        session.commit()

        return output_file

    @staticmethod
    async def _export_to_csv(records: List[Record], output_file: str):
        """Export records to CSV."""
        if not records:
            return

        # Collect all unique fields
        all_fields = set()
        for record in records:
            all_fields.update(record.original_data.keys())
            if record.enriched_data:
                all_fields.update(record.enriched_data.keys())

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
            writer.writeheader()

            for record in records:
                row = record.original_data.copy()
                if record.enriched_data:
                    row.update(record.enriched_data)
                writer.writerow(row)

    @staticmethod
    async def _export_to_json(records: List[Record], output_file: str):
        """Export records to JSON."""
        data = []
        for record in records:
            item = {
                "id": str(record.id),
                "original_data": record.original_data,
                "enriched_data": record.enriched_data,
                "processing_time_ms": record.processing_time_ms,
                "processed_at": record.processed_at.isoformat() if record.processed_at else None
            }
            data.append(item)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
