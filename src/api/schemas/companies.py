"""Company-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.api.schemas.base import BaseSchema


class CompanyCreate(BaseModel):
    """Schema for creating a company."""
    name: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    mdm_flag: bool = Field(False, description="Master Data Management flag")
    industry: Optional[str] = Field(None, max_length=100)
    employee_count: Optional[int] = Field(None, ge=0)
    revenue_range: Optional[str] = Field(None, max_length=50)
    headquarters_location: Optional[str] = Field(None, max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('domain')
    def validate_domain(cls, v):
        if v and not v.strip():
            return None
        return v.lower() if v else None


class CompanyUpdate(BaseModel):
    """Schema for updating a company."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    mdm_flag: Optional[bool] = None
    industry: Optional[str] = Field(None, max_length=100)
    employee_count: Optional[int] = Field(None, ge=0)
    revenue_range: Optional[str] = Field(None, max_length=50)
    headquarters_location: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = None
    enrichment_data: Optional[Dict[str, Any]] = None


class CompanyResponse(BaseSchema):
    """Schema for company response."""
    id: UUID
    name: str
    domain: Optional[str]
    mdm_flag: bool
    industry: Optional[str]
    employee_count: Optional[int]
    revenue_range: Optional[str]
    headquarters_location: Optional[str]
    metadata: Dict[str, Any]
    enrichment_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_enriched_at: Optional[datetime]
    record_count: Optional[int] = None


class CompanyListResponse(BaseSchema):
    """Schema for company list response."""
    id: UUID
    name: str
    domain: Optional[str]
    mdm_flag: bool
    industry: Optional[str]
    created_at: datetime
    record_count: Optional[int] = None


class CompanyMerge(BaseModel):
    """Schema for merging companies."""
    source_company_ids: List[UUID] = Field(..., min_items=1, max_items=10)
    target_company_id: UUID
    merge_enrichment_data: bool = Field(True, description="Merge enrichment data")
    update_records: bool = Field(True, description="Update associated records")
