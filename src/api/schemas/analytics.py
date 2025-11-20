"""Analytics-related Pydantic schemas."""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field

from src.models import JobStatus, RecordStatus


class TimeRange(BaseModel):
    """Time range for analytics queries."""
    start_date: date
    end_date: date

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class JobAnalytics(BaseModel):
    """Job analytics response."""
    total_jobs: int
    jobs_by_status: Dict[JobStatus, int]
    total_records_processed: int
    average_completion_time_seconds: float
    success_rate: float
    daily_job_counts: List[Dict[str, Any]]


class ProcessingMetrics(BaseModel):
    """Processing metrics response."""
    total_records: int
    records_by_status: Dict[RecordStatus, int]
    average_processing_time_ms: float
    median_processing_time_ms: float
    p95_processing_time_ms: float
    hourly_throughput: List[Dict[str, Any]]
    error_rate: float
    retry_statistics: Dict[str, Any]


class CompanyAnalytics(BaseModel):
    """Company analytics response."""
    total_companies: int
    mdm_companies: int
    companies_by_industry: Dict[str, int]
    companies_by_employee_range: Dict[str, int]
    enrichment_coverage: float
    top_companies_by_records: List[Dict[str, Any]]


class SystemMetrics(BaseModel):
    """System-wide metrics."""
    active_jobs: int
    queued_records: int
    processing_rate_per_minute: float
    llm_api_calls_today: int
    llm_api_errors_today: int
    database_size_mb: float
    system_health: str
    alerts: List[Dict[str, Any]]


class DashboardData(BaseModel):
    """Dashboard data combining multiple metrics."""
    job_analytics: JobAnalytics
    processing_metrics: ProcessingMetrics
    company_analytics: CompanyAnalytics
    system_metrics: SystemMetrics
    recent_jobs: List[Dict[str, Any]]
    recent_errors: List[Dict[str, Any]]
