import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, JSON, func
from app.models.base import Base


class DomainEvent(Base):
    __tablename__ = "domain_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    occurred_at = Column(TIMESTAMP, server_default=func.now())
    actor = Column(String, nullable=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload_json = Column(JSON, nullable=False)
    request_id = Column(String, nullable=True)
    correlation_id = Column(String, nullable=True)