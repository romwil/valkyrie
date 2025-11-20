"""Companies router for managing company data and MDM."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_active_user, User, can_manage_companies
from src.api.schemas.companies import (
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse,
    CompanyMerge
)
from src.api.schemas.base import PaginationParams, PaginatedResponse, SuccessResponse
from src.api.services.company_service import CompanyService
from src.database import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    current_user: User = Depends(can_manage_companies),
    session: Session = Depends(db_manager.get_session)
):
    """Create a new company."""
    try:
        company = await CompanyService.create_company(
            company_data=company_data,
            user_id=current_user.id,
            session=session
        )
        return company
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create company"
        )


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get company details by ID."""
    company = await CompanyService.get_company(company_id, session)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    # Add record count
    company.record_count = session.query(Record).filter_by(company_id=company.id).count()

    return company


@router.get("/", response_model=PaginatedResponse)
async def list_companies(
    mdm_only: bool = Query(False, description="Show only MDM flagged companies"),
    search: Optional[str] = Query(None, description="Search by name or domain"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """List companies with optional filtering."""
    companies, total = await CompanyService.list_companies(
        session=session,
        mdm_only=mdm_only,
        search=search,
        industry=industry,
        limit=pagination.page_size,
        offset=pagination.offset
    )

    # Convert to response schema
    company_responses = [CompanyListResponse.model_validate(company) for company in companies]

    return PaginatedResponse.create(
        items=company_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    update_data: CompanyUpdate,
    current_user: User = Depends(can_manage_companies),
    session: Session = Depends(db_manager.get_session)
):
    """Update company details."""
    company = await CompanyService.update_company(
        company_id=company_id,
        update_data=update_data,
        user_id=current_user.id,
        session=session
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    return company


@router.delete("/{company_id}", response_model=SuccessResponse)
async def delete_company(
    company_id: UUID,
    current_user: User = Depends(can_manage_companies),
    session: Session = Depends(db_manager.get_session)
):
    """Delete a company."""
    try:
        success = await CompanyService.delete_company(
            company_id=company_id,
            user_id=current_user.id,
            session=session
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company {company_id} not found"
            )

        return SuccessResponse(
            message="Company deleted successfully",
            data={"company_id": str(company_id)}
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{company_id}/toggle-mdm", response_model=CompanyResponse)
async def toggle_mdm_flag(
    company_id: UUID,
    current_user: User = Depends(can_manage_companies),
    session: Session = Depends(db_manager.get_session)
):
    """Toggle MDM flag for a company."""
    company = await CompanyService.toggle_mdm_flag(
        company_id=company_id,
        user_id=current_user.id,
        session=session
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    return company


@router.get("/search/similar")
async def find_similar_companies(
    name: str = Query(..., description="Company name to search for"),
    threshold: int = Query(80, ge=0, le=100, description="Similarity threshold (0-100)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Find companies with similar names."""
    similar = await CompanyService.find_similar_companies(
        company_name=name,
        session=session,
        threshold=threshold,
        limit=limit
    )

    # Format response
    results = []
    for item in similar:
        company_data = CompanyListResponse.model_validate(item["company"])
        results.append({
            "company": company_data,
            "similarity_score": item["similarity_score"]
        })

    return {
        "query": name,
        "threshold": threshold,
        "results": results
    }


@router.post("/merge", response_model=CompanyResponse)
async def merge_companies(
    merge_data: CompanyMerge,
    current_user: User = Depends(can_manage_companies),
    session: Session = Depends(db_manager.get_session)
):
    """Merge multiple companies into one."""
    try:
        company = await CompanyService.merge_companies(
            merge_data=merge_data,
            user_id=current_user.id,
            session=session
        )
        return company
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to merge companies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to merge companies"
        )


@router.get("/{company_id}/statistics")
async def get_company_statistics(
    company_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get detailed statistics for a company."""
    try:
        stats = await CompanyService.get_company_statistics(company_id, session)
        return stats
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/bulk/mdm-update", response_model=SuccessResponse)
async def bulk_update_mdm_flags(
    company_ids: List[UUID],
    mdm_flag: bool,
    current_user: User = Depends(can_manage_companies),
    session: Session = Depends(db_manager.get_session)
):
    """Bulk update MDM flags for multiple companies."""
    if not company_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No company IDs provided"
        )

    if len(company_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 companies can be updated at once"
        )

    result = await CompanyService.bulk_update_mdm_flags(
        company_ids=company_ids,
        mdm_flag=mdm_flag,
        user_id=current_user.id,
        session=session
    )

    return SuccessResponse(
        message=f"Updated MDM flags for {result['updated_count']} companies",
        data=result
    )


@router.get("/industries/list")
async def list_industries(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(db_manager.get_session)
):
    """Get list of all unique industries."""
    from sqlalchemy import distinct

    industries = session.query(distinct(Company.industry)).filter(
        Company.industry.isnot(None)
    ).order_by(Company.industry).all()

    return {
        "industries": [ind[0] for ind in industries if ind[0]],
        "count": len(industries)
    }


# Import Record model for the router
from src.models import Record
