import uuid
from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, JSON, func, UniqueConstraint
from app.models.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key = Column(String, nullable=False)
    route = Column(String, nullable=False)
    method = Column(String, nullable=False)
    request_hash = Column(String, nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body_json = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("idempotency_key", "route", "method", name="uq_idempotency_key_route_method"),
    )