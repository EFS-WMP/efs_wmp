import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    TIMESTAMP,
    UniqueConstraint,
    func,
)

from app.models.base import Base


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_run"
    __table_args__ = (
        UniqueConstraint("bol_id", "run_no", name="uq_reconciliation_run_bol_run_no"),
        CheckConstraint("receiving_total_net_lbs >= 0", name="ck_recon_run_receiving_nonnegative"),
        CheckConstraint("processing_total_lbs >= 0", name="ck_recon_run_processing_nonnegative"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bol_id = Column(String, ForeignKey("bol.id"), nullable=False)
    run_no = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False)
    receiving_total_net_lbs = Column(Numeric, nullable=False)
    processing_total_lbs = Column(Numeric, nullable=False)
    variance_lbs = Column(Numeric, nullable=False)
    variance_pct = Column(Numeric, nullable=False)
    threshold_pct = Column(Numeric, nullable=False)
    threshold_lbs = Column(Numeric, nullable=True)
    approval_required = Column(Boolean, nullable=False, default=False)
    computed_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    computed_by = Column(String, nullable=True)
    snapshot_json = Column(JSON, nullable=False, server_default="{}")
    voided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    voided_by = Column(String, nullable=True)
    void_reason = Column(String, nullable=True)


class ReconciliationApprovalEvent(Base):
    __tablename__ = "reconciliation_approval_event"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    reconciliation_run_id = Column(String, ForeignKey("reconciliation_run.id"), nullable=False)
    decision = Column(String, nullable=False)
    approver = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    decided_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    payload_json = Column(JSON, nullable=False, server_default="{}")


class DiscrepancyCase(Base):
    __tablename__ = "discrepancy_case"
    __table_args__ = (
        UniqueConstraint("bol_id", "case_no", name="uq_discrepancy_case_bol_case_no"),
        CheckConstraint(
            "("
            "(status IN ('OPEN','IN_DISPUTE') AND resolved_at IS NULL)"
            " OR "
            "(status IN ('RESOLVED','VOIDED'))"
            ")",
            name="ck_discrepancy_state_resolution",
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bol_id = Column(String, ForeignKey("bol.id"), nullable=False)
    case_no = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False)
    discrepancy_type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String, nullable=False)
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolved_by = Column(String, nullable=True)
    resolution_text = Column(String, nullable=True)
    artifact_refs_json = Column(JSON, nullable=True)
    voided_at = Column(TIMESTAMP(timezone=True), nullable=True)
    voided_by = Column(String, nullable=True)
    void_reason = Column(String, nullable=True)
