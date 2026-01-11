from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, select

from app.core.db import async_session
from app.main import app
from app.models.bol import BOL
from app.models.pickup_manifest import PickupManifest, PickupManifestIntegrationAttempt


FORBIDDEN_TOKENS = (
    "route_state",
    "route_execution",
    "stop_execution",
    "dispatch_state",
    "dispatch_execution",
    "day_route_state",
    "technician_assignment_state",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_code_files() -> list[Path]:
    root = _repo_root()
    paths: list[Path] = []
    for base in (root / "app" / "models", root / "alembic" / "versions"):
        if base.exists():
            paths.extend(base.rglob("*.py"))
    return paths


def _line_allowed(line: str) -> bool:
    lower = line.lower()
    if "_snapshot_json" in lower:
        return True
    if "snapshot" in lower:
        return True
    return False


def test_no_operational_truth_terms_in_models_or_migrations():
    violations: list[str] = []
    for path in _iter_code_files():
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            lower = line.lower()
            for token in FORBIDDEN_TOKENS:
                if token in lower and not _line_allowed(line):
                    violations.append(f"{path}:{idx}: {token}")
    if violations:
        pytest.fail("Forbidden operational-truth tokens found:\n" + "\n".join(violations))


def test_pickup_manifest_has_no_operational_truth_columns():
    disallowed: list[str] = []
    for column in PickupManifest.__table__.columns:
        name = column.name.lower()
        if "route_" in name and not (name == "route_snapshot_json" or name.startswith("odoo_")):
            disallowed.append(column.name)
        if "stop_" in name and not name.startswith("odoo_"):
            disallowed.append(column.name)
        for token in ("dispatch_", "technician_", "assignment_", "execution_"):
            if token in name:
                disallowed.append(column.name)
    if disallowed:
        pytest.fail("Operational truth columns found on pickup_manifest: " + ", ".join(sorted(set(disallowed))))


def _has_unique_constraint_on_column(table, column_name: str) -> bool:
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            cols = [col.name for col in constraint.columns]
            if cols == [column_name]:
                return True
    for index in table.indexes:
        if index.unique and [col.name for col in index.columns] == [column_name]:
            return True
    return False


def _has_pickup_manifest_required_check(table) -> bool:
    for constraint in table.constraints:
        if isinstance(constraint, CheckConstraint):
            expr = str(constraint.sqltext).lower()
            if "source_type" in expr and "pickup_manifest_id" in expr and "pickup" in expr:
                return True
    return False


@pytest.mark.asyncio
async def test_pickup_bol_requires_pickup_manifest_id_and_is_unique():
    bol_table = BOL.__table__
    assert _has_unique_constraint_on_column(bol_table, "pickup_manifest_id")
    assert _has_pickup_manifest_required_check(bol_table)


def _build_payload(fingerprint: str) -> dict:
    return {
        "source_system": "odoo18",
        "manifest_fingerprint": fingerprint,
        "completed_at": "2026-01-02T03:04:05+00:00",
        "odoo_refs": {
            "odoo_day_route_id": "route-1",
            "odoo_stop_id": "stop-1",
            "odoo_pickup_occurrence_id": "pickup-1",
            "odoo_work_order_id": "wo-1",
            "customer_id": "cust-1",
            "service_location_id": "loc-1",
        },
        "route_snapshot_json": {"snapshot": "ok"},
        "location_snapshot_json": {"geocode_confidence": 0.9, "address": "123 Main St"},
        "pod_evidence": [
            {"ref": "s3://bucket/pod-1.jpg", "sha256": "a" * 64, "filename": "pod-1.jpg"}
        ],
    }


@pytest.mark.asyncio
async def test_duplicate_submit_does_not_create_new_pickup_bol():
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    payload = _build_payload("f" * 64)
    headers1 = {"Idempotency-Key": "idem-1"}
    headers2 = {"Idempotency-Key": "idem-2"}

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response1 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers1)
        assert response1.status_code == 200
        response2 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers2)
        assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()
    assert data1["pickup_manifest_id"] == data2["pickup_manifest_id"]
    assert data1["bol_id"] == data2["bol_id"]

    async with async_session() as session:
        result = await session.execute(
            select(BOL).where(BOL.pickup_manifest_id == data1["pickup_manifest_id"])
        )
        assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_integration_attempts_are_append_only_on_duplicate():
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    payload = _build_payload("b" * 64)
    headers = {
        "Idempotency-Key": "idem-append",
        "X-Request-Id": "req-1",
        "X-Correlation-Id": "corr-1",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response1 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers)
        assert response1.status_code == 200

    async with async_session() as session:
        first_attempt = await session.execute(
            select(PickupManifestIntegrationAttempt)
            .where(PickupManifestIntegrationAttempt.manifest_fingerprint == payload["manifest_fingerprint"])
            .order_by(PickupManifestIntegrationAttempt.occurred_at)
        )
        first_row = first_attempt.scalars().first()
        assert first_row is not None
        first_snapshot = (
            first_row.outcome,
            first_row.idempotency_key,
            first_row.correlation_id,
            first_row.manifest_fingerprint,
            first_row.error_message,
        )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response2 = await client.post("/api/v1/pickup-manifests:submit", json=payload, headers=headers)
        assert response2.status_code == 200

    async with async_session() as session:
        attempts = await session.execute(
            select(PickupManifestIntegrationAttempt).where(
                PickupManifestIntegrationAttempt.manifest_fingerprint == payload["manifest_fingerprint"]
            )
        )
        rows = attempts.scalars().all()
        assert len(rows) == 2
        stored = await session.get(PickupManifestIntegrationAttempt, first_row.id)
        assert stored is not None
        stored_snapshot = (
            stored.outcome,
            stored.idempotency_key,
            stored.correlation_id,
            stored.manifest_fingerprint,
            stored.error_message,
        )
        assert stored_snapshot == first_snapshot
        assert stored.idempotency_key == "idem-append"
        assert stored.correlation_id == "corr-1"


@pytest.mark.asyncio
async def test_attempt_outcome_enum_is_locked():
    table = PickupManifestIntegrationAttempt.__table__
    constraint_sql = [
        str(constraint.sqltext).lower()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    ]
    assert any(
        "outcome" in sql
        and "accepted" in sql
        and "duplicate_returned" in sql
        and "rejected" in sql
        and "error" in sql
        for sql in constraint_sql
    )


def test_docs_no_acceptance_commits_to_itad_core():
    root = _repo_root().parent
    doc_paths = []
    phase1 = root / "docs" / "phase1"
    if phase1.exists():
        doc_paths.extend(phase1.rglob("*.md"))
    for extra in ("README.md", "itad-core/README.md"):
        path = root / extra
        if path.exists():
            doc_paths.append(path)

    pattern = re.compile(r"acceptance.*commits.*itad core", re.IGNORECASE)
    violations: list[str] = []
    for path in doc_paths:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(content):
            violations.append(str(path))

    if violations:
        pytest.fail("Forbidden SoR phrase found in docs: " + ", ".join(sorted(violations)))
