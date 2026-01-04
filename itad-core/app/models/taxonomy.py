import uuid

from sqlalchemy import Boolean, Column, ForeignKey, JSON, String, TIMESTAMP, UniqueConstraint, func

from app.models.base import Base


class TaxonomyType(Base):
    __tablename__ = "taxonomy_type"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_code = Column(String, nullable=False)
    type_code = Column(String, nullable=False)
    type_name = Column(String, nullable=False)
    effective_from = Column(TIMESTAMP(timezone=True), nullable=False)
    effective_to = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "group_code",
            "type_code",
            "effective_from",
            name="uq_taxonomy_type_group_code_type_code_effective_from",
        ),
    )


class TaxonomyItem(Base):
    __tablename__ = "taxonomy_item"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    taxonomy_type_id = Column(String, ForeignKey("taxonomy_type.id"), nullable=False)
    variant_code = Column(String, nullable=False)
    variant_name = Column(String, nullable=False)
    sb20_flag = Column(Boolean, nullable=False, default=False)
    hazard_class = Column(String, nullable=True)
    un_number = Column(String, nullable=True)
    effective_from = Column(TIMESTAMP(timezone=True), nullable=False)
    effective_to = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "taxonomy_type_id",
            "variant_code",
            "effective_from",
            name="uq_taxonomy_item_type_variant_effective_from",
        ),
    )


class TaxonomyChangeLog(Base):
    __tablename__ = "taxonomy_change_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    actor = Column(String, nullable=True)
    action_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    payload_json = Column(JSON, nullable=False)
