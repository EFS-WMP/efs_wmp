import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    JSON,
    String,
    TIMESTAMP,
    UniqueConstraint,
    func,
)

from app.models.base import Base


class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifact"
    __table_args__ = (
        UniqueConstraint(
            "sha256_hex",
            "storage_provider",
            "storage_ref",
            name="uq_artifact_content_pointer",
        ),
        CheckConstraint("byte_size >= 0", name="ck_artifact_byte_size_nonnegative"),
        CheckConstraint("sha256_hex ~ '^[0-9a-f]{64}$'", name="ck_artifact_sha256_format"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    artifact_type = Column(String, nullable=False)
    sha256_hex = Column(String, nullable=False)
    byte_size = Column(BigInteger, nullable=False)
    mime_type = Column(String, nullable=True)
    storage_provider = Column(String, nullable=False)
    storage_ref = Column(String, nullable=False)
    storage_version = Column(String, nullable=True)
    retention_until = Column(TIMESTAMP(timezone=True), nullable=True)
    visibility = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False, server_default="{}")


class ArtifactLink(Base):
    __tablename__ = "artifact_link"
    __table_args__ = (
        UniqueConstraint(
            "artifact_id",
            "entity_type",
            "entity_id",
            "link_role",
            name="uq_artifact_link_unique",
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    artifact_id = Column(String, ForeignKey("evidence_artifact.id"), nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    link_role = Column(String, nullable=False)
    visibility_override = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    notes = Column(String, nullable=True)


class CustodyEvent(Base):
    __tablename__ = "custody_event"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    actor = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    from_location_id = Column(String, nullable=True)
    to_location_id = Column(String, nullable=True)
    from_location_code = Column(String, nullable=True)
    to_location_code = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False, server_default="{}")
    supersedes_event_id = Column(String, nullable=True)
