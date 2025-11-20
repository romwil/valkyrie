"""Analytics router for job statistics and processing metrics."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.api.auth import get_current_active_user, User
from src.api.schemas.analytics import (
    SystemMetrics, JobMetrics, CompanyMetrics, TimeSeriesData
)
from src.database import db_manager
from src.models import Job, Record, Company, AuditLog, JobStatus, RecordStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get overall system metrics."""
    # Get job statistics
    job_stats = session.query(
        func.count(Job.id).label('total_jobs'),
        func.count(Job.id).filter(Job.status == JobStatus.PENDING).label('pending_jobs'),
        func.count(Job.id).filter(Job.status == JobStatus.PROCESSING).label('processing_jobs'),
        func.count(Job.id).filter(Job.status == JobStatus.COMPLETED).label('completed_jobs'),
        func.count(Job.id).filter(Job.status == JobStatus.FAILED).label('failed_jobs')
    ).first()
    
    # Get record statistics
    record_stats = session.query(
        func.count(Record.id).label('total_records'),
        func.count(Record.id).filter(Record.status == RecordStatus.ENRICHED).label('enriched_records'),
        func.count(Record.id).filter(Record.status == RecordStatus.PENDING).label('pending_records'),
        func.count(Record.id).filter(Record.status == RecordStatus.FAILED).label('failed_records')
    ).first()
    
    # Get company statistics
    company_stats = session.query(
        func.count(Company.id).label('total_companies'),
        func.count(Company.id).filter(Company.mdm_flag == True).label('mdm_companies')
    ).first()
    
    # Calculate rates
    job_success_rate = round(
        (job_stats.completed_jobs / job_stats.total_jobs * 100) 
        if job_stats.total_jobs > 0 else 0, 2
    )
    
    enrichment_rate = round(
        (record_stats.enriched_records / record_stats.total_records * 100) 
        if record_stats.total_records > 0 else 0, 2
    )
    
    return SystemMetrics(
        total_jobs=job_stats.total_jobs or 0,
        active_jobs=(job_stats.pending_jobs or 0) + (job_stats.processing_jobs or 0),
        completed_jobs=job_stats.completed_jobs or 0,
        failed_jobs=job_stats.failed_jobs or 0,
        job_success_rate=job_success_rate,
        total_records=record_stats.total_records or 0,
        enriched_records=record_stats.enriched_records or 0,
        pending_records=record_stats.pending_records or 0,
        failed_records=record_stats.failed_records or 0,
        enrichment_rate=enrichment_rate,
        total_companies=company_stats.total_companies or 0,
        mdm_companies=company_stats.mdm_companies or 0
    )


@router.get("/jobs/{job_id}", response_model=JobMetrics)
async def get_job_metrics(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get detailed metrics for a specific job."""
    # Verify job exists
    job = session.query(Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    # Get record statistics
    record_stats = session.query(
        func.count(Record.id).label('total_records'),
        func.count(Record.id).filter(Record.status == RecordStatus.ENRICHED).label('enriched'),
        func.count(Record.id).filter(Record.status == RecordStatus.PENDING).label('pending'),
        func.count(Record.id).filter(Record.status == RecordStatus.PROCESSING).label('processing'),
        func.count(Record.id).filter(Record.status == RecordStatus.FAILED).label('failed')
    ).filter(Record.job_id == job_id).first()
    
    # Get unique companies count
    unique_companies = session.query(func.count(func.distinct(Record.company_id))).filter(
        Record.job_id == job_id
    ).scalar() or 0
    
    # Calculate processing time
    processing_time = None
    if job.started_at and job.completed_at:
        processing_time = (job.completed_at - job.started_at).total_seconds()
    elif job.started_at:
        processing_time = (datetime.utcnow() - job.started_at).total_seconds()
    
    # Calculate rates
    success_rate = round(
        (record_stats.enriched / record_stats.total_records * 100) 
        if record_stats.total_records > 0 else 0, 2
    )
    
    progress = round(
        ((record_stats.enriched + record_stats.failed) / record_stats.total_records * 100) 
        if record_stats.total_records > 0 else 0, 2
    )
    
    return JobMetrics(
        job_id=str(job_id),
        status=job.status.value,
        total_records=record_stats.total_records or 0,
        enriched_records=record_stats.enriched or 0,
        pending_records=record_stats.pending or 0,
        processing_records=record_stats.processing or 0,
        failed_records=record_stats.failed or 0,
        unique_companies=unique_companies,
        success_rate=success_rate,
        progress=progress,
        processing_time_seconds=processing_time,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None
    )


@router.get("/companies/{company_id}", response_model=CompanyMetrics)
async def get_company_metrics(
    company_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get detailed metrics for a specific company."""
    # Verify company exists
    company = session.query(Company).filter_by(id=company_id).first()
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company {company_id} not found"
        )
    
    # Get record statistics
    record_stats = session.query(
        func.count(Record.id).label('total_records'),
        func.count(Record.id).filter(Record.status == RecordStatus.ENRICHED).label('enriched'),
        func.count(Record.id).filter(Record.status == RecordStatus.FAILED).label('failed')
    ).filter(Record.company_id == company_id).first()
    
    # Get job count
    job_count = session.query(func.count(func.distinct(Record.job_id))).filter(
        Record.company_id == company_id
    ).scalar() or 0
    
    # Get enrichment history (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    enrichment_history = session.query(
        func.date(Record.updated_at).label('date'),
        func.count(Record.id).label('count')
    ).filter(
        and_(
            Record.company_id == company_id,
            Record.status == RecordStatus.ENRICHED,
            Record.updated_at >= thirty_days_ago
        )
    ).group_by(func.date(Record.updated_at)).all()
    
    # Format enrichment history
    history_data = [
        {"date": str(item.date), "count": item.count}
        for item in enrichment_history
    ]
    
    # Calculate enrichment rate
    enrichment_rate = round(
        (record_stats.enriched / record_stats.total_records * 100) 
        if record_stats.total_records > 0 else 0, 2
    )
    
    return CompanyMetrics(
        company_id=str(company_id),
        company_name=company.name,
        mdm_flag=company.mdm_flag,
        total_records=record_stats.total_records or 0,
        enriched_records=record_stats.enriched or 0,
        failed_records=record_stats.failed or 0,
        enrichment_rate=enrichment_rate,
        job_count=job_count,
        enrichment_history=history_data,
        last_enriched_at=company.last_enriched_at.isoformat() if company.last_enriched_at else None,
        created_at=company.created_at.isoformat()
    )


@router.get("/time-series/jobs")
async def get_job_time_series(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get time series data for job creation and completion."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get job creation data
    created_data = session.query(
        func.date(Job.created_at).label('date'),
        func.count(Job.id).label('count')
    ).filter(
        Job.created_at >= start_date
    ).group_by(func.date(Job.created_at)).all()
    
    # Get job completion data
    completed_data = session.query(
        func.date(Job.completed_at).label('date'),
        func.count(Job.id).label('count')
    ).filter(
        and_(
            Job.completed_at >= start_date,
            Job.status == JobStatus.COMPLETED
        )
    ).group_by(func.date(Job.completed_at)).all()
    
    return {
        "period_days": days,
        "jobs_created": [
            {"date": str(item.date), "count": item.count}
            for item in created_data
        ],
        "jobs_completed": [
            {"date": str(item.date), "count": item.count}
            for item in completed_data
        ]
    }


@router.get("/time-series/enrichments")
async def get_enrichment_time_series(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get time series data for record enrichments."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get enrichment data by status
    enrichment_data = session.query(
        func.date(Record.updated_at).label('date'),
        Record.status,
        func.count(Record.id).label('count')
    ).filter(
        Record.updated_at >= start_date
    ).group_by(
        func.date(Record.updated_at),
        Record.status
    ).all()
    
    # Organize data by status
    status_data = {}
    for item in enrichment_data:
        status = item.status.value
        if status not in status_data:
            status_data[status] = []
        status_data[status].append({
            "date": str(item.date),
            "count": item.count
        })
    
    return {
        "period_days": days,
        "enrichment_data": status_data
    }
cat >> /root/valkyrie/src/api/routers/analytics.py << 'EOF'
    else:  # jobs
        # Top companies by job count
        results = session.query(
            Company.id,
            Company.name,
            Company.mdm_flag,
            func.count(func.distinct(Record.job_id)).label('count')
        ).join(
            Record, Company.id == Record.company_id
        ).group_by(
            Company.id, Company.name, Company.mdm_flag
        ).order_by(
            func.count(func.distinct(Record.job_id)).desc()
        ).limit(limit).all()
    
    # Format results
    return {
        "metric": metric,
        "companies": [
            {
                "company_id": str(item.id),
                "company_name": item.name,
                "mdm_flag": item.mdm_flag,
                "count": item.count
            }
            for item in results
        ]
    }


@router.get("/audit-log")
async def get_audit_log(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get recent audit log entries."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = session.query(AuditLog).filter(
        AuditLog.created_at >= start_date
    )
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    return {
        "period_days": days,
        "action_filter": action,
        "total_entries": len(logs),
        "entries": [
            {
                "id": str(log.id),
                "action": log.action,
                "details": log.details,
                "user_id": log.user_id,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    }


@router.get("/processing-speed")
async def get_processing_speed_metrics(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get processing speed metrics."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get completed jobs with processing times
    jobs = session.query(Job).filter(
        and_(
            Job.status == JobStatus.COMPLETED,
            Job.completed_at >= start_date,
            Job.started_at.isnot(None),
            Job.completed_at.isnot(None)
        )
    ).all()
    
    if not jobs:
        return {
            "period_days": days,
            "total_jobs": 0,
            "average_processing_time_seconds": 0,
            "average_records_per_second": 0,
            "fastest_job": None,
            "slowest_job": None
        }
    
    # Calculate metrics
    processing_times = []
    records_per_second = []
    
    for job in jobs:
        processing_time = (job.completed_at - job.started_at).total_seconds()
        processing_times.append(processing_time)
        
        # Get record count for job
        record_count = session.query(func.count(Record.id)).filter(
            Record.job_id == job.id
        ).scalar() or 0
        
        if processing_time > 0 and record_count > 0:
            records_per_second.append(record_count / processing_time)
    
    # Find fastest and slowest jobs
    fastest_idx = processing_times.index(min(processing_times))
    slowest_idx = processing_times.index(max(processing_times))
    
    return {
        "period_days": days,
        "total_jobs": len(jobs),
        "average_processing_time_seconds": round(sum(processing_times) / len(processing_times), 2),
        "average_records_per_second": round(sum(records_per_second) / len(records_per_second), 2) if records_per_second else 0,
        "fastest_job": {
            "job_id": str(jobs[fastest_idx].id),
            "processing_time_seconds": round(processing_times[fastest_idx], 2)
        },
        "slowest_job": {
            "job_id": str(jobs[slowest_idx].id),
            "processing_time_seconds": round(processing_times[slowest_idx], 2)
        }
    }
