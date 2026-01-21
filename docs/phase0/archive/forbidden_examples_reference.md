# Forbidden SoR Pattern Examples (Reference Only)

> [!CAUTION]
> This file is located in `docs/phase0/archive/` and is **excluded from verification scanning**.
> These examples show patterns that violate the established System-of-Record boundaries.

## Purpose

This document preserves examples of forbidden SoR claims for reference by reviewers and auditors.
The verification script (`scripts/phase0_verify.ps1`) scans for these patterns in `docs/phase0/` but explicitly excludes the `archive/` directory.

## Forbidden Patterns

The following phrases violate the SoR lock established in [SOR_LOCK.md](../SOR_LOCK.md):

### SOR_ALL_001
**Violation**: Claiming any single system is SoR for "all operational data"
- Example: "system of record for all operational data"
- Example: "ITAD Core serves as the system of record for all operational data"

### SOR_COMP_001, SOR_COMP_002, SOR_COMP_003
**Violation**: Claiming Odoo is authoritative for compliance data
- Example: "Odoo is the system of record for compliance"
- Example: "Odoo stores the authoritative compliance records"
- Example: "Odoo is authoritative for receiving weight compliance"

### SOR_ACC_001
**Violation**: Claiming acceptance commits to ITAD Core
- Example: "acceptance phase commits to ITAD Core"
- Correct: "Acceptance/dispatch execution commits to Odoo" (per SOR_LOCK.md)

## Reference

See the [SOR_LOCK.md](../SOR_LOCK.md) for the correct SoR boundaries:
- **Odoo**: Scheduling, Day Routes, Dispatch execution
- **ITAD Core**: Compliance, Receiving, Processing, Custody, Evidence, Inventory, Settlement
- **Routific**: Optimizer only (proposals stored/versioned in Odoo)
