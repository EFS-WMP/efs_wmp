## System-of-Record Lock

Odoo is the system of record for Scheduling, Day Routes, and Dispatch execution. ITAD Core is the system of record for Compliance, Receiving, Processing, Custody, Evidence, Inventory, and Settlement. Routific acts solely as an optimizer; proposals are stored/versioned in Odoo, and ITAD Core receives compliance artifacts later via pickup_manifest → BOL → receiving. Acceptance/dispatch execution commits to Odoo.

### Forbidden Examples
- “system of record for all operational data”
- “ITAD Core serves as the system of record for all operational data”
- “acceptance … commits to ITAD Core”
- Any claim that “Odoo SoR compliance” or similar toggles the SoR lock
