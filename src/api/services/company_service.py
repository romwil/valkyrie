"""Company service for managing company data and MDM."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from fuzzywuzzy import fuzz

from src.models import Company, Record, AuditLog
from src.api.schemas.companies import CompanyCreate, CompanyUpdate, CompanyMerge

logger = logging.getLogger(__name__)


class CompanyService:
    """Service for managing company data."""

    @staticmethod
    async def create_company(
        company_data: CompanyCreate,
        user_id: str,
        session: Session
    ) -> Company:
        """Create a new company."""
        # Check for existing company with same domain
        if company_data.domain:
            existing = session.query(Company).filter_by(domain=company_data.domain).first()
            if existing:
                raise ValueError(f"Company with domain {company_data.domain} already exists")

        # Create company
        company = Company(
            name=company_data.name,
            domain=company_data.domain,
            mdm_flag=company_data.mdm_flag,
            industry=company_data.industry,
            employee_count=company_data.employee_count,
            revenue_range=company_data.revenue_range,
            headquarters_location=company_data.headquarters_location,
            metadata=company_data.metadata
        )

        session.add(company)
        session.flush()

        # Log action
        AuditLog.log_action(
            session=session,
            action="company_created",
            details={"company_name": company.name, "mdm_flag": company.mdm_flag},
            user_id=user_id
        )

        session.commit()
        logger.info(f"Created company {company.id}: {company.name}")
        return company

    @staticmethod
    async def get_company(company_id: UUID, session: Session) -> Optional[Company]:
        """Get company by ID."""
        return session.query(Company).filter_by(id=company_id).first()

    @staticmethod
    async def list_companies(
        session: Session,
        mdm_only: bool = False,
        search: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Company], int]:
        """List companies with optional filtering."""
        query = session.query(Company)

        # Apply filters
        if mdm_only:
            query = query.filter(Company.mdm_flag == True)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Company.name.ilike(search_term),
                    Company.domain.ilike(search_term)
                )
            )

        if industry:
            query = query.filter(Company.industry == industry)

        # Get total count
        total = query.count()

        # Get paginated results
        companies = query.order_by(Company.name).limit(limit).offset(offset).all()

        # Add record count for each company
        for company in companies:
            company.record_count = session.query(Record).filter_by(company_id=company.id).count()

        return companies, total

    @staticmethod
    async def update_company(
        company_id: UUID,
        update_data: CompanyUpdate,
        user_id: str,
        session: Session
    ) -> Optional[Company]:
        """Update company details."""
        company = await CompanyService.get_company(company_id, session)
        if not company:
            return None

        # Track changes for audit
        changes = {}

        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if hasattr(company, field) and getattr(company, field) != value:
                changes[field] = {
                    "old": getattr(company, field),
                    "new": value
                }
                setattr(company, field, value)

        if changes:
            # Log changes
            AuditLog.log_action(
                session=session,
                action="company_updated",
                details={"changes": changes},
                user_id=user_id
            )

        session.commit()
        return company

    @staticmethod
    async def delete_company(
        company_id: UUID,
        user_id: str,
        session: Session
    ) -> bool:
        """Delete a company."""
        company = await CompanyService.get_company(company_id, session)
        if not company:
            return False

        # Check if company has associated records
        record_count = session.query(Record).filter_by(company_id=company_id).count()
        if record_count > 0:
            raise ValueError(f"Cannot delete company with {record_count} associated records")

        # Log action
        AuditLog.log_action(
            session=session,
            action="company_deleted",
            details={"company_name": company.name},
            user_id=user_id
        )

        session.delete(company)
        session.commit()
        return True

    @staticmethod
    async def toggle_mdm_flag(
        company_id: UUID,
        user_id: str,
        session: Session
    ) -> Optional[Company]:
        """Toggle MDM flag for a company."""
        company = await CompanyService.get_company(company_id, session)
        if not company:
            return None

        old_value = company.mdm_flag
        company.mdm_flag = not company.mdm_flag

        # Log action
        AuditLog.log_action(
            session=session,
            action="mdm_flag_toggled",
            details={
                "company_name": company.name,
                "old_value": old_value,
                "new_value": company.mdm_flag
            },
            user_id=user_id
        )

        session.commit()
        logger.info(f"Toggled MDM flag for company {company.id}: {old_value} -> {company.mdm_flag}")
        return company

    @staticmethod
    async def find_similar_companies(
        company_name: str,
        session: Session,
        threshold: int = 80,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find companies with similar names."""
        all_companies = session.query(Company).all()

        similar_companies = []
        for company in all_companies:
            # Calculate similarity score
            score = fuzz.ratio(company_name.lower(), company.name.lower())

            if score >= threshold:
                similar_companies.append({
                    "company": company,
                    "similarity_score": score
                })

        # Sort by similarity score
        similar_companies.sort(key=lambda x: x["similarity_score"], reverse=True)

        return similar_companies[:limit]

    @staticmethod
    async def merge_companies(
        merge_data: CompanyMerge,
        user_id: str,
        session: Session
    ) -> Company:
        """Merge multiple companies into one."""
        # Get target company
        target_company = await CompanyService.get_company(merge_data.target_company_id, session)
        if not target_company:
            raise ValueError(f"Target company {merge_data.target_company_id} not found")

        # Get source companies
        source_companies = []
        for source_id in merge_data.source_company_ids:
            if source_id == merge_data.target_company_id:
                continue  # Skip if source is same as target

            source = await CompanyService.get_company(source_id, session)
            if source:
                source_companies.append(source)

        if not source_companies:
            raise ValueError("No valid source companies found for merge")

        # Merge enrichment data if requested
        if merge_data.merge_enrichment_data:
            merged_data = target_company.enrichment_data or {}
            for source in source_companies:
                if source.enrichment_data:
                    # Merge data, preferring non-null values
                    for key, value in source.enrichment_data.items():
                        if value and (key not in merged_data or not merged_data[key]):
                            merged_data[key] = value

            target_company.enrichment_data = merged_data

        # Update records if requested
        if merge_data.update_records:
            for source in source_companies:
                # Update all records to point to target company
                session.query(Record).filter_by(company_id=source.id).update(
                    {"company_id": target_company.id}
                )

        # Log merge action
        AuditLog.log_action(
            session=session,
            action="companies_merged",
            details={
                "target_company": target_company.name,
                "source_companies": [s.name for s in source_companies],
                "merge_enrichment_data": merge_data.merge_enrichment_data,
                "update_records": merge_data.update_records
            },
            user_id=user_id
        )

        # Delete source companies
        for source in source_companies:
            session.delete(source)

        session.commit()
        logger.info(f"Merged {len(source_companies)} companies into {target_company.name}")
        return target_company

    @staticmethod
    async def get_company_statistics(company_id: UUID, session: Session) -> Dict[str, Any]:
        """Get detailed statistics for a company."""
        company = await CompanyService.get_company(company_id, session)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Get record statistics
        record_stats = session.query(
            func.count(Record.id).label('total_records'),
            func.count(Record.id).filter(Record.status == 'enriched').label('enriched_records'),
            func.count(Record.id).filter(Record.status == 'pending').label('pending_records'),
            func.count(Record.id).filter(Record.status == 'failed').label('failed_records')
        ).filter(Record.company_id == company_id).first()

        # Get job count
        job_count = session.query(func.count(func.distinct(Record.job_id))).filter(
            Record.company_id == company_id
        ).scalar()

        return {
            "company_id": str(company_id),
            "company_name": company.name,
            "mdm_flag": company.mdm_flag,
            "total_records": record_stats.total_records or 0,
            "enriched_records": record_stats.enriched_records or 0,
            "pending_records": record_stats.pending_records or 0,
            "failed_records": record_stats.failed_records or 0,
            "enrichment_rate": round(
                (record_stats.enriched_records / record_stats.total_records * 100) 
                if record_stats.total_records > 0 else 0, 2
            ),
            "job_count": job_count or 0,
            "last_enriched_at": company.last_enriched_at.isoformat() if company.last_enriched_at else None,
            "created_at": company.created_at.isoformat(),
            "updated_at": company.updated_at.isoformat()
        }

    @staticmethod
    async def bulk_update_mdm_flags(
        company_ids: List[UUID],
        mdm_flag: bool,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """Bulk update MDM flags for multiple companies."""
        updated_count = 0
        failed_ids = []

        for company_id in company_ids:
            try:
                company = await CompanyService.get_company(company_id, session)
                if company and company.mdm_flag != mdm_flag:
                    company.mdm_flag = mdm_flag
                    updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update MDM flag for company {company_id}: {e}")
                failed_ids.append(str(company_id))

        if updated_count > 0:
            # Log bulk action
            AuditLog.log_action(
                session=session,
                action="bulk_mdm_update",
                details={
                    "company_count": updated_count,
                    "mdm_flag": mdm_flag,
                    "failed_ids": failed_ids
                },
                user_id=user_id
            )

            session.commit()

        return {
            "updated_count": updated_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids
        }
