"""Jobs router for enrichment job management."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session

from src.api.auth import get_current_active_user, User, can_create_jobs
from src.api.schemas.jobs import (
    JobCreate, JobUpdate, JobResponse, JobListResponse, JobStatistics
)
from src.api.schemas.base import PaginationParams, PaginatedResponse, SuccessResponse
from src.api.services.job_service import JobService
from src.database import db_manager
from src.models import JobStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(can_create_jobs),
    session: Session = Depends(db_manager.get_session)
):
    """Create a new enrichment job."""
    try:
        job = await JobService.create_job(
            job_data=job_data,
            user_id=current_user.id,
            session=session
        )
        return job
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )


@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job_from_upload(
    file: UploadFile = File(...),
    configuration: Optional[str] = None,
    current_user: User = Depends(can_create_jobs),
    session: Session = Depends(db_manager.get_session)
):
    """Create a new job by uploading a CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )

    try:
        # Save uploaded file
        import tempfile
        import shutil

        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # Parse configuration if provided
        import json
        config = {}
        if configuration:
            try:
                config = json.loads(configuration)
            except json.JSONDecodeError:
                raise ValueError("Invalid configuration JSON")

        # Create job
        job_data = JobCreate(
            input_file=tmp_path,
            configuration=config,
            metadata={"original_filename": file.filename}
        )

        job = await JobService.create_job(
            job_data=job_data,
            user_id=current_user.id,
            session=session
        )
        return job

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create job from upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job from upload"
        )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get job details by ID."""
    job = await JobService.get_job(job_id, session)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return job


@router.get("/", response_model=PaginatedResponse)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """List jobs with optional filtering."""
    jobs, total = await JobService.list_jobs(
        session=session,
        status=status,
        limit=pagination.page_size,
        offset=pagination.offset
    )

    # Convert to response schema
    job_responses = [JobListResponse.model_validate(job) for job in jobs]

    return PaginatedResponse.create(
        items=job_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    update_data: JobUpdate,
    current_user: User = Depends(can_create_jobs),
    session: Session = Depends(db_manager.get_session)
):
    """Update job details."""
    job = await JobService.update_job(
        job_id=job_id,
        update_data=update_data,
        user_id=current_user.id,
        session=session
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return job


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(can_create_jobs),
    session: Session = Depends(db_manager.get_session)
):
    """Cancel a running job."""
    try:
        job = await JobService.cancel_job(
            job_id=job_id,
            user_id=current_user.id,
            session=session
        )

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        return job

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{job_id}/statistics", response_model=JobStatistics)
async def get_job_statistics(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get detailed statistics for a job."""
    # Verify job exists
    job = await JobService.get_job(job_id, session)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    stats = await JobService.get_job_statistics(job_id, session)
    return JobStatistics(**stats)


@router.post("/{job_id}/export")
async def export_job_results(
    job_id: UUID,
    output_format: str = Query("csv", regex="^(csv|json)$"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Export job results to file."""
    try:
        output_file = await JobService.export_job_results(
            job_id=job_id,
            session=session,
            output_format=output_format
        )

        return SuccessResponse(
            message="Job results exported successfully",
            data={"output_file": output_file}
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to export job results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export job results"
        )


@router.post("/{job_id}/start", response_model=JobResponse)
async def start_job_processing(
    job_id: UUID,
    current_user: User = Depends(can_create_jobs),
    session: Session = Depends(db_manager.get_session)
):
    """Start processing a pending job."""
    # Get job
    job = await JobService.get_job(job_id, session)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not in pending status (current: {job.status.value})"
        )

    # Update job status to processing
    update_data = JobUpdate(status=JobStatus.PROCESSING)
    job = await JobService.update_job(
        job_id=job_id,
        update_data=update_data,
        user_id=current_user.id,
        session=session
    )

    # In a real implementation, this would trigger the actual processing
    # For now, we just update the status
    logger.info(f"Started processing job {job_id}")

    return job
