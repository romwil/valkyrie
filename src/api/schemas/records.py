"""Record-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field

from src.api.schemas.base import BaseSchema
from src.models import RecordStatus


class RecordUpdate(BaseModel):
    """Schema for updating a record."""
    enriched_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[RecordStatus] = None


class RecordResponse(BaseSchema):
    """Schema for record response."""
    id: UUID
    job_id: UUID
    company_id: Optional[UUID]
    status: RecordStatus
    original_data: Dict[str, Any]
    enriched_data: Optional[Dict[str, Any]]
    llm_response: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    error_message: Optional[str]
    retry_count: int
    processing_time_ms: Optional[int]
    created_at: datetime
    processed_at: Optional[datetime]


class RecordListResponse(BaseSchema):
    """Schema for record list response."""
    id: UUID
    job_id: UUID
    company_id: Optional[UUID]
    status: RecordStatus
    company_name: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]


class BulkRecordUpdate(BaseModel):
    """Schema for bulk record updates."""
    record_ids: List[UUID] = Field(..., min_items=1, max_items=1000)
    update_data: RecordUpdate


class BulkRecordResponse(BaseModel):
    """Response for bulk operations."""
    success_count: int
    failure_count: int
    failed_ids: List[UUID]
    errors: Dict[str, str]
