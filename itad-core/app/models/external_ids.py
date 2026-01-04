import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, func, Index, UniqueConstraint
from app.models.base import Base


class ExternalIDMap(Base):
    __tablename__ = "external_id_map"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system = Column(String, nullable=False)  # 'odoo' or 'routific'
    entity_type = Column(String, nullable=False)  # e.g., 'work_order', 'pickup_manifest', 'job'
    external_id = Column(String, nullable=False)  # ID in external system
    itad_entity_id = Column(String, nullable=False)  # UUID of ITAD entity
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('system', 'entity_type', 'external_id', name='uq_external_id_map_system_entity_external'),
    )


# Indexes for lookup
Index("idx_external_system_entity", ExternalIDMap.system, ExternalIDMap.entity_type)
Index("idx_external_itad_entity", ExternalIDMap.itad_entity_id)