"""
Fresness update service for BI datasets.

Phase 2.6: Provides functions to check and record dataset freshness
for monitoring in bi.dataset_freshness table.
"""
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# Dataset definitions with freshness thresholds
DATASET_CONFIGS = {
    "material_types_v1": {
        "version": "v1",
        "source_table": "material_types",
        "updated_at_column": "updated_at",
        "stale_threshold_hours": 2,
    },
    "receiving_records_v1": {
        "version": "v1",
        "source_table": "receiving_weight_record_v3",
        "updated_at_column": "created_at",
        "stale_threshold_hours": 1,
    },
    "receiving_kpis_daily_v1": {
        "version": "v1",
        "source_table": "receiving_weight_record_v3",
        "updated_at_column": "created_at",
        "stale_threshold_hours": 48,
    },
}


async def compute_dataset_freshness(db: AsyncSession, dataset_name: str) -> dict:
    """
    Compute freshness for a single dataset.
    
    Returns dict with: dataset_name, version, max_updated_at, row_count, status
    """
    config = DATASET_CONFIGS.get(dataset_name)
    if not config:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    
    # Query source table for max updated_at and count
    query = text(f"""
        SELECT 
            MAX({config['updated_at_column']}) as max_updated,
            COUNT(*) as row_count
        FROM {config['source_table']}
    """)
    
    result = await db.execute(query)
    row = result.fetchone()
    
    max_updated = row.max_updated if row else None
    row_count = row.row_count if row else 0
    
    # Determine status based on threshold
    status = "ok"
    if max_updated:
        age_hours = (datetime.utcnow() - max_updated.replace(tzinfo=None)).total_seconds() / 3600
        if age_hours > config["stale_threshold_hours"]:
            status = "stale"
        elif age_hours > config["stale_threshold_hours"] / 2:
            status = "warn"
    else:
        status = "stale"  # No data = stale
    
    return {
        "dataset_name": dataset_name,
        "dataset_version": config["version"],
        "max_source_updated_at": max_updated,
        "row_count": row_count,
        "status": status,
    }


async def update_freshness_record(db: AsyncSession, dataset_name: str) -> dict:
    """
    Compute and upsert freshness record for a dataset.
    
    Returns the computed freshness dict.
    """
    freshness = await compute_dataset_freshness(db, dataset_name)
    
    # Upsert into bi.dataset_freshness
    upsert_query = text("""
        INSERT INTO bi.dataset_freshness 
            (dataset_name, dataset_version, computed_at, max_source_updated_at, row_count, status)
        VALUES 
            (:dataset_name, :dataset_version, NOW(), :max_source_updated_at, :row_count, :status)
        ON CONFLICT (dataset_name, dataset_version) 
        DO UPDATE SET
            computed_at = NOW(),
            max_source_updated_at = EXCLUDED.max_source_updated_at,
            row_count = EXCLUDED.row_count,
            status = EXCLUDED.status
    """)
    
    await db.execute(upsert_query, {
        "dataset_name": freshness["dataset_name"],
        "dataset_version": freshness["dataset_version"],
        "max_source_updated_at": freshness["max_source_updated_at"],
        "row_count": freshness["row_count"],
        "status": freshness["status"],
    })
    await db.commit()
    
    return freshness


async def update_all_freshness(db: AsyncSession) -> list[dict]:
    """
    Update freshness for all configured datasets.
    
    Returns list of freshness dicts.
    """
    results = []
    for dataset_name in DATASET_CONFIGS:
        freshness = await update_freshness_record(db, dataset_name)
        results.append(freshness)
    return results
