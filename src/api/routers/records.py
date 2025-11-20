"""Records router for managing enrichment records."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.api.auth import get_current_active_user, User, require_operator
from src.api.schemas.records import (
    RecordUpdate, RecordResponse, RecordListResponse,
    BulkRecordUpdate, BulkRecordResponse
)
from src.api.schemas.base import PaginationParams, PaginatedResponse, SuccessResponse
from src.database import db_manager
from src.models import Record, RecordStatus, Job

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(
    record_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get record details by ID."""
    record = session.query(Record).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id} not found"
        )
    return record


@router.get("/", response_model=PaginatedResponse)
async def list_records(
    job_id: Optional[UUID] = Query(None, description="Filter by job ID"),
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    status: Optional[RecordStatus] = Query(None, description="Filter by status"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """List records with optional filtering."""
    query = session.query(Record)

    # Apply filters
    if job_id:
        query = query.filter(Record.job_id == job_id)
    if company_id:
        query = query.filter(Record.company_id == company_id)
    if status:
        query = query.filter(Record.status == status)

    # Get total count
    total = query.count()

    # Get paginated results
    records = query.order_by(Record.created_at.desc()).limit(
        pagination.page_size
    ).offset(pagination.offset).all()

    # Convert to response schema
    record_responses = []
    for record in records:
        response = RecordListResponse.model_validate(record)
        # Add company name if available
        if record.company:
            response.company_name = record.company.name
        record_responses.append(response)

    return PaginatedResponse.create(
        items=record_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.patch("/{record_id}", response_model=RecordResponse)
async def update_record(
    record_id: UUID,
    update_data: RecordUpdate,
    current_user: User = Depends(require_operator),
    session: Session = Depends(db_manager.get_session)
):
    """Update record details."""
    record = session.query(Record).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id} not found"
        )

    # Update fields
    if update_data.enriched_data is not None:
        record.enriched_data = update_data.enriched_data
    if update_data.metadata is not None:
        record.metadata.update(update_data.metadata)
    if update_data.status is not None:
        record.status = update_data.status

    session.commit()
    return record


@router.post("/bulk-update", response_model=BulkRecordResponse)
async def bulk_update_records(
    bulk_update: BulkRecordUpdate,
    current_user: User = Depends(require_operator),
    session: Session = Depends(db_manager.get_session)
):
    """Bulk update multiple records."""
    success_count = 0
    failure_count = 0
    failed_ids = []
    errors = {}

    for record_id in bulk_update.record_ids:
        try:
            record = session.query(Record).filter_by(id=record_id).first()
            if not record:
                failed_ids.append(record_id)
                errors[str(record_id)] = "Record not found"
                failure_count += 1
                continue

            # Apply updates
            if bulk_update.update_data.enriched_data is not None:
                record.enriched_data = bulk_update.update_data.enriched_data
            if bulk_update.update_data.metadata is not None:
                record.metadata.update(bulk_update.update_data.metadata)
            if bulk_update.update_data.status is not None:
                record.status = bulk_update.update_data.status

            success_count += 1

        except Exception as e:
            failed_ids.append(record_id)
            errors[str(record_id)] = str(e)
            failure_count += 1
            logger.error(f"Failed to update record {record_id}: {e}")

    session.commit()

    return BulkRecordResponse(
        success_count=success_count,
        failure_count=failure_count,
        failed_ids=failed_ids,
        errors=errors
    )


@router.post("/{record_id}/retry", response_model=RecordResponse)
async def retry_record(
    record_id: UUID,
    current_user: User = Depends(require_operator),
    session: Session = Depends(db_manager.get_session)
):
    """Retry processing a failed record."""
    record = session.query(Record).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id} not found"
        )

    if record.status != RecordStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Record is not in failed status (current: {record.status.value})"
        )

    # Reset record for retry
    record.status = RecordStatus.PENDING
    record.error_message = None

    session.commit()

    # In a real implementation, this would trigger reprocessing
    logger.info(f"Record {record_id} marked for retry")

    return record


@router.post("/job/{job_id}/retry-failed", response_model=SuccessResponse)
async def retry_failed_records(
    job_id: UUID,
    current_user: User = Depends(require_operator),
    session: Session = Depends(db_manager.get_session)
):
    """Retry all failed records in a job."""
    # Verify job exists
    job = session.query(Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Update all failed records to pending
    updated_count = session.query(Record).filter(
        and_(
            Record.job_id == job_id,
            Record.status == RecordStatus.FAILED
        )
    ).update({
        "status": RecordStatus.PENDING,
        "error_message": None
    })

    session.commit()

    return SuccessResponse(
        message=f"Marked {updated_count} failed records for retry",
        data={"updated_count": updated_count}
    )


@router.delete("/{record_id}", response_model=SuccessResponse)
async def delete_record(
    record_id: UUID,
    current_user: User = Depends(require_operator),
    session: Session = Depends(db_manager.get_session)
):
    """Delete a record."""
    record = session.query(Record).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id} not found"
        )

    # Don't allow deletion of processed records
    if record.status == RecordStatus.ENRICHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete enriched records"
        )

    session.delete(record)
    session.commit()

    return SuccessResponse(
        message="Record deleted successfully",
        data={"record_id": str(record_id)}
    )


@router.get("/job/{job_id}/export", response_model=SuccessResponse)
async def export_job_records(
    job_id: UUID,
    status: Optional[RecordStatus] = Query(None, description="Filter by status"),
    format: str = Query("csv", regex="^(csv|json)$"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Export records for a specific job."""
    # Verify job exists
    job = session.query(Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Get records
    query = session.query(Record).filter(Record.job_id == job_id)
    if status:
        query = query.filter(Record.status == status)

    records = query.all()

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No records found matching criteria"
        )

    # In a real implementation, this would generate and return a file
    # For now, return a success message
    return SuccessResponse(
        message=f"Export initiated for {len(records)} records",
        data={
            "record_count": len(records),
            "format": format,
            "status_filter": status.value if status else None
        }
    )
