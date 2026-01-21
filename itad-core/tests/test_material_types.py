"""
Phase 2.3: Material Types Endpoint Tests

Tests for GET /api/v1/material-types endpoint.
Following strict TDD: tests written first.
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

from app.main import app
from app.models.material_type import MaterialType


@pytest.mark.asyncio
async def test_response_shape_wrapper_contains_items_meta(db_session):
    """Test material types list returns wrapper with items and meta fields"""
    # Create test material type
    mat = MaterialType(
        code="BAT-LI-001",
        name="Lithium Batteries",
        stream="batteries",
        requires_photo=True,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(mat)
    await db_session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types")
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert wrapper structure
    assert "items" in data
    assert "meta" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["meta"], dict)
    
    # Assert meta fields
    meta = data["meta"]
    assert "generated_at" in meta
    assert "count" in meta
    assert "include_inactive" in meta
    assert "updated_since" in meta
    
    # Verify meta values
    assert meta["count"] == 1
    assert meta["include_inactive"] is True
    assert meta["updated_since"] is None
    
    # Verify generated_at is ISO8601 with Z
    assert meta["generated_at"].endswith("Z")
    datetime.fromisoformat(meta["generated_at"].replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_material_types_list_schema(db_session):
    """Test material types items contain correct fields"""
    # Create test material types
    mat1 = MaterialType(
        code="BAT-LI-001",
        name="Lithium Batteries",
        stream="batteries",
        hazard_class="Class 9",
        default_action="recycle",
        requires_photo=True,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    mat2 = MaterialType(
        code="EW-CPU-001",
        name="CPU/Boards",
        stream="electronics",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    
    db_session.add_all([mat1, mat2])
    await db_session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types")
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert list length
    assert len(data["items"]) == 2
    assert data["meta"]["count"] == 2
    
    # Assert each object contains required keys
    for item in data["items"]:
        assert "id" in item
        assert "code" in item
        assert "name" in item
        assert "stream" in item
        assert "hazard_class" in item
        assert "default_action" in item
        assert "requires_photo" in item
        assert "requires_weight" in item
        assert "is_active" in item
        assert "updated_at" in item
        # Phase 2.4a: Billing metadata fields
        assert "default_price" in item
        assert "basis_of_charge" in item
        assert "gl_account_code" in item
        
        # Assert types
        assert isinstance(item["id"], str)  # UUID as string
        assert isinstance(item["requires_photo"], bool)
        assert isinstance(item["requires_weight"], bool)
        assert isinstance(item["is_active"], bool)
        assert isinstance(item["updated_at"], str)  # ISO 8601 string


@pytest.mark.asyncio
async def test_updated_at_is_timezone_aware_iso8601(db_session):
    """Test updated_at field is always timezone-aware ISO8601 with UTC Z"""
    mat = MaterialType(
        code="TEST-001",
        name="Test Material",
        stream="test",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(mat)
    await db_session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types")
    
    assert response.status_code == 200
    data = response.json()
    
    for item in data["items"]:
        updated_at_str = item["updated_at"]
        
        # Verify ISO 8601 format with timezone
        # Accept both Z and +00:00 formats
        assert "T" in updated_at_str
        assert (updated_at_str.endswith("Z") or "+00:00" in updated_at_str or updated_at_str.endswith("+00:00"))
        
        # Verify parseable as datetime
        parsed = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None  # Must be timezone-aware


@pytest.mark.asyncio
async def test_include_inactive_false_filters_inactive(db_session):
    """Test include_inactive=false returns only active records"""
    # Create active and inactive records
    active = MaterialType(
        code="ACTIVE-001",
        name="Active Material",
        stream="active",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    inactive = MaterialType(
        code="INACTIVE-001",
        name="Inactive Material",
        stream="inactive",
        requires_photo=False,
        requires_weight=True,
        is_active=False,
        updated_at=datetime.now(timezone.utc),
    )
    
    db_session.add_all([active, inactive])
    await db_session.commit()
    
    # Test include_inactive=false
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types?include_inactive=false")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return only active
    assert data["meta"]["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["code"] == "ACTIVE-001"
    assert data["items"][0]["is_active"] is True
    assert data["meta"]["include_inactive"] is False


@pytest.mark.asyncio
async def test_include_inactive_true_returns_all(db_session):
    """Test include_inactive=true (default) returns both active and inactive"""
    # Create active and inactive records
    active = MaterialType(
        code="ACTIVE-001",
        name="Active Material",
        stream="active",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    inactive = MaterialType(
        code="INACTIVE-001",
        name="Inactive Material",
        stream="inactive",
        requires_photo=False,
        requires_weight=True,
        is_active=False,
        updated_at=datetime.now(timezone.utc),
    )
    
    db_session.add_all([active, inactive])
    await db_session.commit()
    
    # Test include_inactive=true (explicit)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types?include_inactive=true")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return both
    assert data["meta"]["count"] == 2
    assert len(data["items"]) == 2
    assert data["meta"]["include_inactive"] is True
    
    # Verify both present
    codes = [item["code"] for item in data["items"]]
    assert "ACTIVE-001" in codes
    assert "INACTIVE-001" in codes


@pytest.mark.asyncio
async def test_material_types_filter_stream(db_session):
    """Test filtering by stream parameter"""
    # Create items with different streams
    batteries = MaterialType(
        code="BAT-LI-001",
        name="Lithium Batteries",
        stream="batteries",
        requires_photo=True,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    electronics = MaterialType(
        code="EW-CPU-001",
        name="CPU/Boards",
        stream="electronics",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    metals = MaterialType(
        code="SCR-MET-001",
        name="Mixed Metal Scrap",
        stream="metals",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    
    db_session.add_all([batteries, electronics, metals])
    await db_session.commit()
    
    # GET with stream filter
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types?stream=batteries")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return only batteries
    assert data["meta"]["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["code"] == "BAT-LI-001"
    assert data["items"][0]["stream"] == "batteries"


@pytest.mark.asyncio
async def test_updated_since_filters_by_updated_at(db_session):
    """Test updated_since parameter filters correctly with >= comparison"""
    # Create item T1
    t1_time = datetime(2026, 1, 17, 10, 0, 0, tzinfo=timezone.utc)
    t1 = MaterialType(
        code="OLD-001",
        name="Old Material",
        stream="old",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=t1_time,
    )
    db_session.add(t1)
    await db_session.commit()
    
    # Create item T2 later
    t2_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=timezone.utc)
    t2 = MaterialType(
        code="NEW-001",
        name="New Material",
        stream="new",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=t2_time,
    )
    db_session.add(t2)
    await db_session.commit()
    
    # Call endpoint with cutoff between T1 and T2
    cutoff = datetime(2026, 1, 17, 11, 0, 0, tzinfo=timezone.utc)
    cutoff_iso = cutoff.isoformat()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/material-types",
            params={"updated_since": cutoff_iso},
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return only T2 (newer than cutoff)
    assert data["meta"]["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["code"] == "NEW-001"
    assert data["meta"]["updated_since"] == cutoff_iso
    
    # Test with exact timestamp (>= should include it)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/material-types",
            params={"updated_since": t2_time.isoformat()},
        )
    
    data = response.json()
    # >= comparison should include T2
    assert data["meta"]["count"] == 1
    assert data["items"][0]["code"] == "NEW-001"


@pytest.mark.asyncio
async def test_material_types_includes_inactive(db_session):
    """Test that inactive records are included by default with is_active=false"""
    # Create inactive record
    inactive = MaterialType(
        code="INACTIVE-001",
        name="Inactive Material",
        stream="inactive",
        requires_photo=False,
        requires_weight=True,
        is_active=False,  # Inactive
        updated_at=datetime.now(timezone.utc),
    )
    active = MaterialType(
        code="ACTIVE-001",
        name="Active Material",
        stream="active",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )
    
    db_session.add_all([inactive, active])
    await db_session.commit()
    
    # GET all (default include_inactive=true)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return both
    assert data["meta"]["count"] == 2
    assert len(data["items"]) == 2
    
    # Find inactive record
    inactive_item = next(item for item in data["items"] if item["code"] == "INACTIVE-001")
    assert inactive_item["is_active"] is False
    
    # Find active record
    active_item = next(item for item in data["items"] if item["code"] == "ACTIVE-001")
    assert active_item["is_active"] is True


# Phase 2.4a: Billing Metadata Tests

@pytest.mark.asyncio
async def test_billing_fields_in_response(db_session):
    """Test material types response includes billing metadata fields"""
    from decimal import Decimal
    
    mat = MaterialType(
        code="BILL-001",
        name="Billable Material",
        stream="billing",
        requires_photo=False,
        requires_weight=True,
        is_active=True,
        default_price=Decimal("0.1500"),
        basis_of_charge="per_lb",
        gl_account_code="4100-100",
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(mat)
    await db_session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types")
    
    assert response.status_code == 200
    data = response.json()
    
    # Find billing material
    item = next(i for i in data["items"] if i["code"] == "BILL-001")
    
    # Verify billing fields present and correct
    assert item["default_price"] == "0.1500"
    assert item["basis_of_charge"] == "per_lb"
    assert item["gl_account_code"] == "4100-100"


@pytest.mark.asyncio
async def test_billing_fields_null_when_not_set(db_session):
    """Test billing fields are null when not set"""
    mat = MaterialType(
        code="NOBILL-001",
        name="Non-Billable Material",
        stream="test",
        requires_photo=False,
        requires_weight=False,
        is_active=True,
        # No billing fields set
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(mat)
    await db_session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types")
    
    assert response.status_code == 200
    data = response.json()
    
    item = next(i for i in data["items"] if i["code"] == "NOBILL-001")
    
    assert item["default_price"] is None
    assert item["basis_of_charge"] is None
    assert item["gl_account_code"] is None


@pytest.mark.asyncio
async def test_updated_since_includes_billing_updates(db_session):
    """Test that updated_since filter catches billing field updates"""
    from decimal import Decimal
    from datetime import timedelta
    
    # Create material with old timestamp
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    mat = MaterialType(
        code="UPDATE-BILL-001",
        name="Update Test Material",
        stream="test",
        requires_photo=False,
        requires_weight=False,
        is_active=True,
        default_price=Decimal("1.0000"),
        basis_of_charge="per_unit",
        gl_account_code="4100-200",
        updated_at=old_time,
    )
    db_session.add(mat)
    await db_session.commit()
    
    # Update billing field (simulates updated_at change)
    mat.default_price = Decimal("2.5000")
    mat.updated_at = datetime.now(timezone.utc)  # Explicit update
    await db_session.commit()
    
    # Query with updated_since before the update
    filter_time = old_time + timedelta(minutes=1)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/v1/material-types?updated_since={filter_time.isoformat()}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should find the updated record
    assert data["meta"]["count"] >= 1
    item = next((i for i in data["items"] if i["code"] == "UPDATE-BILL-001"), None)
    assert item is not None
    assert item["default_price"] == "2.5000"


@pytest.mark.asyncio
async def test_basis_of_charge_enum_values(db_session):
    """Test all allowed basis_of_charge values work"""
    from decimal import Decimal
    
    allowed_values = ["per_lb", "per_kg", "per_unit", "flat_fee"]
    
    for i, basis in enumerate(allowed_values):
        mat = MaterialType(
            code=f"ENUM-{i:03d}",
            name=f"Test {basis}",
            stream="test",
            requires_photo=False,
            requires_weight=False,
            is_active=True,
            default_price=Decimal("1.0000"),
            basis_of_charge=basis,
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(mat)
    
    await db_session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/material-types")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify all were created
    codes = [i["code"] for i in data["items"]]
    for i in range(len(allowed_values)):
        assert f"ENUM-{i:03d}" in codes
