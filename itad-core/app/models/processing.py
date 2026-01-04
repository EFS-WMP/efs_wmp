import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text, TIMESTAMP, func

from app.models.base import Base


class BatteryProcessingSession(Base):
    __tablename__ = "battery_processing_session"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bol_id = Column(String, ForeignKey("bol.id"), nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    headcount = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class BatteryProcessingLine(Base):
    __tablename__ = "battery_processing_line"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("battery_processing_session.id"), nullable=False)
    taxonomy_item_id = Column(String, ForeignKey("taxonomy_item.id"), nullable=False)
    weight_lbs = Column(Numeric, nullable=False)
    quantity = Column(Integer, nullable=True)
    contamination_flag = Column(Boolean, nullable=False, default=False)
    contamination_taxonomy_item_id = Column(String, ForeignKey("taxonomy_item.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class EwasteProcessingSession(Base):
    __tablename__ = "ewaste_processing_session"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bol_id = Column(String, ForeignKey("bol.id"), nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=False)
    headcount = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class EwasteProcessingLine(Base):
    __tablename__ = "ewaste_processing_line"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("ewaste_processing_session.id"), nullable=False)
    taxonomy_item_id = Column(String, ForeignKey("taxonomy_item.id"), nullable=False)
    weight_lbs = Column(Numeric, nullable=False)
    quantity = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
