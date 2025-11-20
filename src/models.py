"""SQLAlchemy models for Project Valkyrie database.

This module defines all database models for the LLM-driven data action platform.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey,
    CheckConstraint, UniqueConstraint, Index, Enum, JSON, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

Base = declarative_base()


class JobStatus(enum.Enum):
    """Enumeration for job status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecordStatus(enum.Enum):
    """Enumeration for record status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    ENRICHED = "enriched"
    FAILED = "failed"
    SKIPPED = "skipped"


class Job(Base):
    """Model for tracking enrichment job batches."""
    __tablename__ = 'jobs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    input_file = Column(String(500), nullable=False)
    output_file = Column(String(500))
    total_records = Column(Integer, nullable=False, default=0)
    processed_records = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    configuration = Column(JSONB, default=dict)
    metadata = Column(JSONB, default=dict)
    error_details = Column(JSONB, default=list)

    # Relationships
    records = relationship("Record", back_populates="job", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="job", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('processed_records <= total_records', name='chk_processed_records'),
        CheckConstraint('error_count >= 0', name='chk_error_count'),
        CheckConstraint('started_at IS NULL OR started_at >= created_at', name='chk_dates'),
        CheckConstraint(
            '(completed_at IS NULL) OR (started_at IS NOT NULL AND completed_at >= started_at)',
            name='chk_completion'
        ),
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_created_at', 'created_at'),
        Index('idx_jobs_updated_at', 'updated_at'),
        Index('idx_jobs_input_file', 'input_file'),
    )

    @property
    def completion_percentage(self) -> float:
        """Calculate job completion percentage."""
        if self.total_records == 0:
            return 0.0
        return round((self.processed_records / self.total_records) * 100, 2)

    @property
    def processing_time_seconds(self) -> Optional[float]:
        """Calculate processing time in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status.value}, completion={self.completion_percentage}%)>"


class Company(Base):
    """Model for master data management of companies."""
    __tablename__ = 'companies'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True)
    mdm_flag = Column(Boolean, nullable=False, default=False)
    metadata = Column(JSONB, default=dict)
    enrichment_data = Column(JSONB, default=dict)
    industry = Column(String(100))
    employee_count = Column(Integer)
    revenue_range = Column(String(50))
    headquarters_location = Column(String(255))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_enriched_at = Column(DateTime(timezone=True))

    # Relationships
    records = relationship("Record", back_populates="company")

    # Constraints
    __table_args__ = (
        CheckConstraint('employee_count IS NULL OR employee_count >= 0', name='chk_employee_count'),
        Index('idx_companies_name_trgm', 'name'),
        Index('idx_companies_domain', 'domain'),
        Index('idx_companies_mdm_flag', 'mdm_flag'),
        Index('idx_companies_metadata', 'metadata', postgresql_using='gin'),
        Index('idx_companies_industry', 'industry'),
        Index('idx_companies_updated_at', 'updated_at'),
    )

    def merge_enrichment_data(self, new_data: Dict[str, Any]) -> None:
        """Merge new enrichment data with existing data."""
        if not self.enrichment_data:
            self.enrichment_data = {}
        self.enrichment_data.update(new_data)
        self.last_enriched_at = datetime.utcnow()

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.name}, domain={self.domain})>"


class Record(Base):
    """Model for individual records within processing jobs."""
    __tablename__ = 'records'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='SET NULL'))
    original_data = Column(JSONB, nullable=False)
    enriched_data = Column(JSONB, default=dict)
    llm_response = Column(JSONB, default=dict)
    status = Column(Enum(RecordStatus), nullable=False, default=RecordStatus.PENDING)
    processed_at = Column(DateTime(timezone=True))
    processing_time_ms = Column(Integer)
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    job = relationship("Job", back_populates="records")
    company = relationship("Company", back_populates="records")
    audit_logs = relationship("AuditLog", back_populates="record", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('retry_count >= 0', name='chk_retry_count'),
        CheckConstraint('processing_time_ms IS NULL OR processing_time_ms >= 0', name='chk_processing_time'),
        Index('idx_records_job_id', 'job_id'),
        Index('idx_records_company_id', 'company_id'),
        Index('idx_records_status', 'status'),
        Index('idx_records_job_status', 'job_id', 'status'),
        Index('idx_records_processed_at', 'processed_at'),
        Index('idx_records_original_data', 'original_data', postgresql_using='gin'),
        Index('idx_records_enriched_data', 'enriched_data', postgresql_using='gin'),
        Index('idx_records_retry_count', 'retry_count'),
    )

    def mark_processed(self, enriched_data: Dict[str, Any], llm_response: Dict[str, Any]) -> None:
        """Mark record as successfully processed."""
        self.status = RecordStatus.ENRICHED
        self.enriched_data = enriched_data
        self.llm_response = llm_response
        self.processed_at = datetime.utcnow()
        if self.created_at:
            self.processing_time_ms = int((self.processed_at - self.created_at).total_seconds() * 1000)

    def mark_failed(self, error_message: str) -> None:
        """Mark record as failed."""
        self.status = RecordStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1

    def __repr__(self):
        return f"<Record(id={self.id}, job_id={self.job_id}, status={self.status.value})>"


class AuditLog(Base):
    """Model for comprehensive audit trail of system actions."""
    __tablename__ = 'audit_log'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.id', ondelete='CASCADE'))
    record_id = Column(UUID(as_uuid=True), ForeignKey('records.id', ondelete='CASCADE'))
    action = Column(String(100), nullable=False)
    details = Column(JSONB, default=dict)
    user_id = Column(String(255))
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="audit_logs")
    record = relationship("Record", back_populates="audit_logs")

    # Constraints
    __table_args__ = (
        CheckConstraint("action != ''", name='chk_action_not_empty'),
        Index('idx_audit_log_job_id', 'job_id'),
        Index('idx_audit_log_record_id', 'record_id'),
        Index('idx_audit_log_action', 'action'),
        Index('idx_audit_log_created_at', 'created_at'),
        Index('idx_audit_log_user_id', 'user_id'),
    )

    @classmethod
    def log_action(cls, session, action: str, details: Dict[str, Any] = None,
                   job_id: Optional[str] = None, record_id: Optional[str] = None,
                   user_id: Optional[str] = None, ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None) -> 'AuditLog':
        """Create a new audit log entry."""
        log_entry = cls(
            action=action,
            details=details or {},
            job_id=job_id,
            record_id=record_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        session.add(log_entry)
        return log_entry

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, created_at={self.created_at})>"


# Helper functions for common queries

def get_job_statistics(session, job_id: str) -> Dict[str, Any]:
    """Get comprehensive statistics for a job."""
    from sqlalchemy import func

    stats = session.query(
        func.count(Record.id).label('total_records'),
        func.count(Record.id).filter(Record.status == RecordStatus.ENRICHED).label('processed_records'),
        func.count(Record.id).filter(Record.status == RecordStatus.PENDING).label('pending_records'),
        func.count(Record.id).filter(Record.status == RecordStatus.FAILED).label('failed_records'),
        func.avg(Record.processing_time_ms).label('avg_processing_time_ms')
    ).filter(Record.job_id == job_id).first()

    return {
        'total_records': stats.total_records or 0,
        'processed_records': stats.processed_records or 0,
        'pending_records': stats.pending_records or 0,
        'failed_records': stats.failed_records or 0,
        'success_rate': round((stats.processed_records / stats.total_records * 100) if stats.total_records > 0 else 0, 2),
        'avg_processing_time_ms': round(stats.avg_processing_time_ms or 0, 2)
    }


def find_or_create_company(session, name: str, domain: Optional[str] = None) -> Company:
    """Find existing company or create new one."""
    # First try to find by domain if provided
    if domain:
        company = session.query(Company).filter_by(domain=domain).first()
        if company:
            return company

    # Try to find by exact name match
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


def update_job_statistics(session, job_id: str) -> None:
    """Update job statistics based on current records."""
    stats = get_job_statistics(session, job_id)
    job = session.query(Job).filter_by(id=job_id).first()

    if job:
        job.total_records = stats['total_records']
        job.processed_records = stats['processed_records']
        job.error_count = stats['failed_records']

        # Update job status based on completion
        if stats['processed_records'] == stats['total_records'] and stats['total_records'] > 0:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
        elif stats['failed_records'] > 0 and (stats['processed_records'] + stats['failed_records']) == stats['total_records']:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
