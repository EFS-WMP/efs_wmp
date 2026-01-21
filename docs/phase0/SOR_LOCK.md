## System-of-Record Lock

Odoo is the system of record for Scheduling, Day Routes, and Dispatch execution. ITAD Core is the system of record for Compliance, Receiving, Processing, Custody, Evidence, Inventory, and Settlement. Routific acts solely as an optimizer; proposals are stored/versioned in Odoo, and ITAD Core receives compliance artifacts later via pickup_manifest → BOL → receiving. Acceptance/dispatch execution commits to Odoo.

### Forbidden Pattern Reference

> [!NOTE]
> Examples of forbidden SoR claims are documented in [archive/forbidden_examples_reference.md](./archive/forbidden_examples_reference.md).
> That file is excluded from verification scanning to prevent false positives.
