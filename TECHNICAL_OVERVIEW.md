# 📘 Project Technical Overview

## 🔧 Odoo Version
- Target Odoo version: 18.0 Community
- Actual version used in development: Odoo 18.0 (from `docker/odoo18/docker-compose.odoo18.yml` image `odoo:18.0`)
- Notes on compatibility or migration issues:
  - Custom module version string is `18.0.2.2.0` in `addons/common/itad_core/__manifest__.py`, which aligns with Odoo 18.0.
  - Dependencies include `fieldservice` from the OCA field-service stack; ensure the OCA addons path is present and loadable.

## 📦 Project Description
- High-level description: Odoo 18 Field Service bridge that integrates with ITAD Core for pickup manifest submission and receiving confirmation.
- Core modules and features:
  - ITAD Core outbox with idempotent submission, retries, and audit trail.
  - Receiving dashboard and receipt audit archiving cron.
  - Configurable defaults via `ir.config_parameter` and RBAC for receiving managers.
- Architecture: Variant A (Odoo + ITAD Core + Routific)
  - Odoo is the system of record for field service scheduling/execution.
  - ITAD Core receives compliance artifacts and processing data via the outbox flow.
  - Routific is optimizer-only; no write-back of operational truth.

## 🗂 Directory and Module Structure
### Custom Modules
| Module | Location | Summary |
| --- | --- | --- |
| `itad_core` | `addons/common/itad_core/` | ITAD Core bridge: outbox, receiving, audit, and configuration models/views |

### Vendor Modules (OCA)
- `addons/odoo18/oca/field-service/` contains the OCA Field Service suite used by `itad_core`.

### Key Locations
- Models: `addons/common/itad_core/models/`
  - `fsm_order.py`: FSM extensions (ITAD fields + workflow touchpoints)
  - `itad_outbox.py`: Outbox model and cron processor
  - `itad_config.py`: ITAD Core configuration model
  - `itad_receiving_wizard.py`: Receiving wizard flow
  - `itad_receipt_audit_log.py`: Receipt audit log model
- Views: `addons/common/itad_core/views/`
  - `itad_outbox_views.xml`, `itad_receiving_views.xml`, `fsm_order_itad.xml`
- Controllers: `addons/common/itad_core/controllers/controllers.py`
- Data/Cron: `addons/common/itad_core/data/itad_outbox_cron.xml`, `addons/common/itad_core/data/itad_receipt_audit_archiving_cron.xml`
- Security: `addons/common/itad_core/security/`
- Tests: `addons/common/itad_core/tests/`

### Orphaned or Unused Modules (Requires Runtime Confirmation)
- Reported runtime logs indicate `itad_core` is “not installable / module not found / module path false”. Treat this as a blocker until addons-path and dependencies are verified in the running container.

## 🚨 Versioning and Compliance Checks
- Odoo version alignment: Module versions indicate 18.0 and match the Odoo 18.0 image.
- Dependency checks: `itad_core` depends on `fieldservice` (OCA). Ensure the OCA addons path is mounted and included in `addons_path`.
- Manifest coverage (requires confirmation):
  - Verify all shipped XML/CSV files are referenced in `__manifest__.py` under `data`, `demo`, `qweb`, or `assets`.
- SoR principles:
  - Ensure ITAD-bound payloads are read-only reflections in Odoo and that outbox submissions do not mutate operational truth fields.
- Hardcoded/legacy patterns (requires confirmation):
  - `itad_outbox.py` issues HTTP requests directly; verify retry/backoff and error handling align with production expectations.

## ⚠️ Known Issues or Technical Risks
- Installability blocker: runtime logs report `itad_core` as not installable. Until resolved, module discovery and registry checks are unreliable.
- Manifest drift risk: unreferenced XML/demo files can accumulate and create audit noise if not explicitly documented or removed.
- External dependency risk: outbox calls require valid ITAD Core config; missing config will fail submissions.

## ✅ Recommendations
- Close the installability blocker first:
  - Confirm `addons_path` inside the container matches mounted paths (`docker/odoo18/odoo.conf`).
  - Confirm `fieldservice` is loadable in the same environment.
  - Re-run `-u itad_core` after fixing discovery.
- Upgrade “dead code” verification:
  - Check `__manifest__.py` for `data`, `demo`, `assets`, and `qweb`.
  - Grep file names across the repo (including view inheritance references) before declaring files unused.
  - Only then remove or archive unreferenced XML/templates.
- Demo data policy:
  - If `demo.xml` is retained, document “never loaded in prod”.
  - If demo data is used, wire it under `demo` and add a deployment guardrail.
- CI gates:
  - Enforce `.DISABLED` file checks.
  - Require `__manifest__.py` in all addon folders inside `addons_path`.
  - Add manifest-coverage checks with allowlist support.
- SoR boundary guardrail:
  - After install/upgrade, verify `ir.cron` records exist and expected models are in the registry (e.g., `itad.core.outbox`, `itad.core.config`, `itad.receipt.audit.log`).
