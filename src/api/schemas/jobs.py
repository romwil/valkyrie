"""Job-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.api.schemas.base import BaseSchema
from src.models import JobStatus


class JobConfiguration(BaseModel):
    """Job configuration parameters."""
    batch_size: int = Field(100, ge=1, le=1000, description="Records per batch")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    timeout_seconds: int = Field(300, ge=30, le=3600, description="Timeout per record")
    llm_model: str = Field("gemini-pro", description="LLM model to use")
    temperature: float = Field(0.7, ge=0, le=1, description="LLM temperature")
    enrichment_fields: List[str] = Field(
        default_factory=lambda: ["industry", "employee_count", "revenue_range"],
        description="Fields to enrich"
    )


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    input_file: str = Field(..., description="Path to input CSV file")
    configuration: JobConfiguration = Field(
        default_factory=JobConfiguration,
        description="Job configuration"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class JobUpdate(BaseModel):
    """Schema for updating a job."""
    status: Optional[JobStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class JobResponse(BaseSchema):
    """Schema for job response."""
    id: UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    input_file: str
    output_file: Optional[str]
    total_records: int
    processed_records: int
    error_count: int
    completion_percentage: float
    processing_time_seconds: Optional[float]
    configuration: Dict[str, Any]
    metadata: Dict[str, Any]


class JobListResponse(BaseSchema):
    """Schema for job list response."""
    id: UUID
    status: JobStatus
    created_at: datetime
    input_file: str
    total_records: int
    processed_records: int
    completion_percentage: float


class JobStatistics(BaseModel):
    """Job statistics response."""
    total_records: int
    processed_records: int
    pending_records: int
    failed_records: int
    success_rate: float
    avg_processing_time_ms: float
    estimated_completion_time: Optional[datetime]
