"""
Phase 2.3: Material Types API Endpoint

GET /api/v1/material-types - List material types with optional filtering.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.material_type import MaterialType
from app.schemas.material_type import MaterialTypeListResponse, MaterialTypeListMeta


router = APIRouter()


@router.get("/material-types", response_model=MaterialTypeListResponse)
async def list_material_types(
    include_inactive: bool = Query(True, description="Include inactive records (is_active=false)"),
    updated_since: Optional[datetime] = Query(None, description="Return only records updated after this timestamp (inclusive)"),
    stream: Optional[str] = Query(None, description="Filter by stream"),
    db: AsyncSession = Depends(get_db),
):
    """
    List material types with wrapper response format.
    
    Returns material types with metadata in standardized wrapper format.
    Supports incremental sync via updated_since parameter.
    
    Args:
        include_inactive: If true, return both active and inactive records. If false, return only active.
        updated_since: Optional datetime filter for incremental sync (>= comparison)
        stream: Optional stream filter
        db: Database session
        
    Returns:
        MaterialTypeListResponse with items and meta
    """
    # Build query
    query = select(MaterialType)
    
    # Apply filters
    if not include_inactive:
        query = query.where(MaterialType.is_active == True)
    
    if stream:
        query = query.where(MaterialType.stream == stream)
    
    if updated_since:
        # Use >= for inclusive filtering (standard for incremental sync)
        query = query.where(MaterialType.updated_at >= updated_since)
    
    # Order by updated_at descending for consistency
    query = query.order_by(MaterialType.updated_at.desc())
    
    # Execute
    result = await db.execute(query)
    materials = result.scalars().all()
    
    # Build response wrapper
    meta = MaterialTypeListMeta(
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        count=len(materials),
        include_inactive=include_inactive,
        updated_since=updated_since.isoformat() if updated_since else None,
    )
    
    return MaterialTypeListResponse(items=materials, meta=meta)
