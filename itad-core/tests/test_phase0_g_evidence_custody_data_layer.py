import uuid

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError

from app.core.db import async_session, create_tables
from app.repositories import artifacts_repo, custody_repo
from app.models.evidence import EvidenceArtifact, ArtifactLink, CustodyEvent


@pytest_asyncio.fixture(autouse=True)
async def ensure_tables():
    await create_tables()


@pytest.mark.asyncio
async def test_artifact_sha_validation_and_dedup():
    async with async_session() as session:
        # Invalid sha raises
        with pytest.raises(ValueError):
            await artifacts_repo.create_artifact(
                session,
                artifact_type="PDF",
                sha256_hex="badsha",
                byte_size=10,
                mime_type="application/pdf",
                storage_provider="LOCAL",
                storage_ref="ref1",
                visibility="INTERNAL",
                created_by="tester",
                metadata_json={},
            )

        art1 = await artifacts_repo.create_artifact(
            session,
            artifact_type="PDF",
            sha256_hex="a" * 64,
            byte_size=10,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="ref1",
            visibility="INTERNAL",
            created_by="tester",
            metadata_json={"name": "doc1"},
        )
        await session.commit()

        # Dedup: same sha/provider/ref returns existing
        art2 = await artifacts_repo.create_artifact(
            session,
            artifact_type="PDF",
            sha256_hex="a" * 64,
            byte_size=10,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="ref1",
            visibility="INTERNAL",
            created_by="tester",
            metadata_json={"name": "doc1"},
        )
        assert art1.id == art2.id


@pytest.mark.asyncio
async def test_artifact_link_uniqueness_and_visibility():
    async with async_session() as session:
        artifact = await artifacts_repo.create_artifact(
            session,
            artifact_type="PHOTO",
            sha256_hex="b" * 64,
            byte_size=20,
            mime_type="image/png",
            storage_provider="LOCAL",
            storage_ref="ref2",
            visibility="COMPLIANCE_ONLY",
            created_by="tester",
            metadata_json={},
        )
        await session.flush()

        link = await artifacts_repo.link_artifact(
            session,
            artifact_id=artifact.id,
            entity_type="BOL",
            entity_id=str(uuid.uuid4()),
            link_role="SCALE_TICKET",
            created_by="tester",
        )
        await session.commit()
        assert link.id is not None
        entity_id = link.entity_id

        # Duplicate link should fail unique constraint
        dup = ArtifactLink(
            artifact_id=artifact.id,
            entity_type="BOL",
            entity_id=entity_id,
            link_role="SCALE_TICKET",
        )
        session.add(dup)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        visible_none = await artifacts_repo.list_artifacts_for_entity(
            session, entity_type="BOL", entity_id=entity_id, requester_role="internal"
        )
        assert visible_none == []

        visible_compliance = await artifacts_repo.list_artifacts_for_entity(
            session, entity_type="BOL", entity_id=entity_id, requester_role="compliance_admin"
        )
        assert len(visible_compliance) == 1
        assert visible_compliance[0].id == artifact.id


@pytest.mark.asyncio
async def test_custody_event_append_only_and_compensating():
    async with async_session() as session:
        entity_id = str(uuid.uuid4())
        e1 = await custody_repo.add_custody_event(
            session,
            actor="user1",
            event_type="SCAN_IN",
            entity_type="BOL",
            entity_id=entity_id,
            from_location_code="YARD",
            to_location_code="RECEIVING",
        )
        await session.commit()
        assert e1.id is not None

        timeline1 = await custody_repo.get_custody_timeline(session, "BOL", entity_id)
        assert len(timeline1) == 1

        e2 = await custody_repo.add_custody_event(
            session,
            actor="user1",
            event_type="MOVE",
            entity_type="BOL",
            entity_id=entity_id,
            from_location_code="RECEIVING",
            to_location_code="STAGING",
        )
        await session.commit()
        e3 = await custody_repo.add_custody_event(
            session,
            actor="user1",
            event_type="SCAN_OUT",
            entity_type="BOL",
            entity_id=entity_id,
            from_location_code="STAGING",
            to_location_code="TRUCK",
            supersedes_event_id=e2.id,
        )
        await session.commit()

        timeline2 = await custody_repo.get_custody_timeline(session, "BOL", entity_id)
        assert len(timeline2) == 3
        assert timeline2[2].supersedes_event_id == e2.id


@pytest.mark.asyncio
async def test_artifact_link_visibility_override():
    async with async_session() as session:
        artifact = await artifacts_repo.create_artifact(
            session,
            artifact_type="PHOTO",
            sha256_hex="c" * 64,
            byte_size=30,
            mime_type="image/jpeg",
            storage_provider="LOCAL",
            storage_ref="ref3",
            visibility="INTERNAL",
            created_by="tester",
            metadata_json={},
        )
        await session.flush()
        link = await artifacts_repo.link_artifact(
            session,
            artifact_id=artifact.id,
            entity_type="BOL",
            entity_id=str(uuid.uuid4()),
            link_role="POD",
            created_by="tester",
            visibility_override="COMPLIANCE_ONLY",
        )
        await session.commit()

        visible_internal = await artifacts_repo.list_artifacts_for_entity(
            session, entity_type="BOL", entity_id=link.entity_id, requester_role="internal"
        )
        assert visible_internal == []

        visible_compliance = await artifacts_repo.list_artifacts_for_entity(
            session, entity_type="BOL", entity_id=link.entity_id, requester_role="compliance_admin"
        )
        assert len(visible_compliance) == 1


@pytest.mark.asyncio
async def test_duplicate_artifact_detection():
    async with async_session() as session:
        art = await artifacts_repo.create_artifact(
            session,
            artifact_type="PDF",
            sha256_hex="d" * 64,
            byte_size=40,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="ref4",
            visibility="INTERNAL",
            created_by="tester",
            metadata_json={},
        )
        await session.commit()
        art_id = art.id
        # Different storage_ref should allow new artifact with same hash
        art2 = await artifacts_repo.create_artifact(
            session,
            artifact_type="PDF",
            sha256_hex="d" * 64,
            byte_size=40,
            mime_type="application/pdf",
            storage_provider="LOCAL",
            storage_ref="ref5",
            visibility="INTERNAL",
            created_by="tester",
            metadata_json={},
        )
        await session.commit()
        art2_id = art2.id
        assert art_id != art2_id
