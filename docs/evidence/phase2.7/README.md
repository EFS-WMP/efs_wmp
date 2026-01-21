# Evidence Pack Documentation

## Overview

Phase 2.7 provides one-click generation of audit-grade evidence bundles (JSON + PDF) for end-to-end traceability.

---

## Who Can Generate

- **Receiving Manager** role (group_receiving_manager)
- **Admin** (base.group_system)

Regular users cannot generate evidence packs.

---

## How to Generate

### From UI

1. Open FSM Order with a BOL ID
2. Click **"Generate Evidence Pack"** button in header
3. Notification confirms pack ID
4. View packs via **"Evidence Packs"** smart button

### From Shell (CLI)

```python
# Odoo shell
order_id = 123
result = env["itad.evidence.pack.service"].generate_for_order(order_id)
print(f"Pack ID: {result['pack_id']}")
```

---

## Output Files

For each pack, 3 attachments are created:

| File | Content |
|------|---------|
| `EvidencePack-{pack_id}.json` | Full pack data |
| `EvidencePack-{pack_id}.pdf` | Formatted report |
| `EvidencePack-{pack_id}.sha256` | Hash checksums |

---

## Pack ID Format

```
evp-{bol_or_manifest}-{YYYYMMDDHHMMSSZ}
```

Example: `evp-BOL-2026-001234-20260118093045Z`

---

## Verify SHA256

```bash
# PowerShell
Get-FileHash -Algorithm SHA256 EvidencePack-xxx.json | Select Hash
# Compare to value in .sha256 file
```

---

## Retention

Evidence packs are stored as Odoo attachments and follow standard attachment retention policies.

---

## Schema Version

Current: **1.0**

Changes to schema require version bump in `meta.schema_version`.
