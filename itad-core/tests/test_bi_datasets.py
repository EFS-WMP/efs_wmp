"""
Phase 2.6: BI Datasets Tests

Tests for:
- BI schema and views exist
- Required columns present
- Freshness recording works
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_bi_schema_exists(db: AsyncSession):
    """Test that bi schema exists."""
    result = await db.execute(text("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name = 'bi'
    """))
    row = result.fetchone()
    assert row is not None, "bi schema should exist"
    assert row[0] == "bi"


@pytest.mark.asyncio
async def test_bi_material_types_v1_exists(db: AsyncSession):
    """Test bi.material_types_v1 view exists with required columns."""
    result = await db.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'bi' AND table_name = 'material_types_v1'
        ORDER BY ordinal_position
    """))
    columns = [row[0] for row in result.fetchall()]
    
    required = [
        "material_type_id", "code", "name", "stream", "is_active",
        "pricing_state", "updated_at"
    ]
    for col in required:
        assert col in columns, f"Column {col} should exist in bi.material_types_v1"


@pytest.mark.asyncio
async def test_bi_receiving_records_v1_exists(db: AsyncSession):
    """Test bi.receiving_records_v1 view exists with required columns."""
    result = await db.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'bi' AND table_name = 'receiving_records_v1'
    """))
    columns = [row[0] for row in result.fetchall()]
    
    required = [
        "receiving_record_id", "occurred_at", "bol_id", 
        "material_type_code", "material_stream", "net_weight", "is_void"
    ]
    for col in required:
        assert col in columns, f"Column {col} should exist in bi.receiving_records_v1"


@pytest.mark.asyncio
async def test_bi_receiving_kpis_daily_v1_exists(db: AsyncSession):
    """Test bi.receiving_kpis_daily_v1 view exists with required columns."""
    result = await db.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'bi' AND table_name = 'receiving_kpis_daily_v1'
    """))
    columns = [row[0] for row in result.fetchall()]
    
    required = ["report_date", "stream", "total_net_weight", "total_receipts_count"]
    for col in required:
        assert col in columns, f"Column {col} should exist in bi.receiving_kpis_daily_v1"


@pytest.mark.asyncio
async def test_bi_dataset_freshness_table_exists(db: AsyncSession):
    """Test bi.dataset_freshness table exists."""
    result = await db.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'bi' AND table_name = 'dataset_freshness'
    """))
    row = result.fetchone()
    assert row is not None, "bi.dataset_freshness table should exist"


@pytest.mark.asyncio
async def test_freshness_upsert(db: AsyncSession):
    """Test freshness record can be upserted."""
    # Insert/update test freshness record
    await db.execute(text("""
        INSERT INTO bi.dataset_freshness 
            (dataset_name, dataset_version, computed_at, row_count, status)
        VALUES 
            ('test_dataset', 'v1', NOW(), 100, 'ok')
        ON CONFLICT (dataset_name, dataset_version) 
        DO UPDATE SET
            computed_at = NOW(),
            row_count = 100,
            status = 'ok'
    """))
    await db.commit()
    
    # Verify
    result = await db.execute(text("""
        SELECT dataset_name, status 
        FROM bi.dataset_freshness 
        WHERE dataset_name = 'test_dataset'
    """))
    row = result.fetchone()
    assert row is not None
    assert row[0] == "test_dataset"
    assert row[1] == "ok"
    
    # Cleanup
    await db.execute(text("DELETE FROM bi.dataset_freshness WHERE dataset_name = 'test_dataset'"))
    await db.commit()


@pytest.mark.asyncio
async def test_material_types_v1_query(db: AsyncSession):
    """Test bi.material_types_v1 can be queried."""
    result = await db.execute(text("""
        SELECT COUNT(*) FROM bi.material_types_v1
    """))
    row = result.fetchone()
    assert row is not None
    # Count can be 0 if no data, but query should work
    assert row[0] >= 0


@pytest.mark.asyncio
async def test_receiving_records_v1_join(db: AsyncSession):
    """Test bi.receiving_records_v1 has correct join (material_stream not null for known types)."""
    # This tests the view definition is correct
    result = await db.execute(text("""
        SELECT COUNT(*) 
        FROM bi.receiving_records_v1 
        WHERE material_stream IS NULL
    """))
    row = result.fetchone()
    # Should be 0 or small number (unknown types get 'unknown')
    assert row[0] == 0, "material_stream should be 'unknown' for unmatched, never NULL"
