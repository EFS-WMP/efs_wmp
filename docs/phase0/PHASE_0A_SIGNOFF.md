# Phase 0A Sign-off — Planning & Discovery

## Scope

This sign-off covers:

- **System-of-Record (SoR) boundaries** — Clear ownership delineation between Odoo (Scheduling/Dispatch) and ITAD Core (Compliance/Processing/Custody/Evidence/Inventory/Settlement)
- **Integration invariants** — Idempotency, correlation IDs, external_id_map, snapshot rules, append-only constraints
- **Canonical ITAD model lock intent for Phase 1+** — Data model stability commitment for downstream integration

## Approved Artifacts (Immutable References)

The following artifacts are approved as the authoritative Phase 0A documentation:

| Artifact | Path | Purpose |
|----------|------|---------|
| SoR Lock | [SOR_LOCK.md](./SOR_LOCK.md) | System-of-Record ownership boundaries |
| Lock Review | [PHASE_0_LOCK_REVIEW.md](./PHASE_0_LOCK_REVIEW.md) | Detailed review of all Phase 0 items including integration invariants |
| Risk Register | [PHASE_0_RISK_REGISTER.md](./PHASE_0_RISK_REGISTER.md) | Identified risks and mitigations |

> [!NOTE]
> Integration invariants (idempotency, correlation IDs, external_id_map, snapshot rules) are documented within `PHASE_0_LOCK_REVIEW.md` sections B3, I2, I5, and J4.

## Sign-off

| Role | Name | Date (UTC) | Signature/Approval Link |
|------|------|------------|-------------------------|
| Engineering TL | | | |
| Solution Architect | | | |
| Compliance | | | |
| Ops Lead | | | |

> [!IMPORTANT]
> All signatories must review the approved artifacts above before signing. Signing indicates agreement that the SoR boundaries and integration invariants are correct and ready for Phase 1 implementation.

## Evidence

- **Commit SHA**: `<pending — populate after sign-off commit>`
- **PR / Approval Link**: `<pending — link to PR or approval record>`
- **Verification Run**: See [PHASE_0_VERIFICATION_LOG.md](./PHASE_0_VERIFICATION_LOG.md) for latest verification results

## Change Control

Once signed, changes to approved artifacts require:

1. New sign-off with updated date
2. Change justification documented
3. Re-run of verification script with passing result
