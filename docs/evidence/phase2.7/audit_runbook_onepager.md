# Evidence Pack Audit Runbook (One-Pager)

## Purpose

Generate audit-grade evidence bundle for any BOL/manifest/order.

---

## Quick Steps

### Generate Pack

1. **Navigate**: FSM Order → select order with BOL ID
2. **Click**: "Generate Evidence Pack" button
3. **Verify**: Notification shows pack ID
4. **Download**: Click "Evidence Packs" smart button → download files

### Verify Integrity

```powershell
# Compute hash of downloaded JSON
Get-FileHash -Algorithm SHA256 "EvidencePack-evp-xxx.json"
# Compare to value in .sha256 file
```

---

## What's Included

| Section | Contents |
|---------|----------|
| `meta` | Pack ID, timestamp, generator, systems |
| `trace` | Correlation IDs, idempotency keys |
| `odoo` | FSM order, outbox events, audit logs, attachments |
| `itad_core` | Receiving anchors, material type snapshot |
| `retention_and_controls` | Retention policy, break-glass events |
| `integrity` | SHA256 hashes |

---

## Access Control

| Role | Can Generate |
|------|-------------|
| Receiving Manager | ✅ |
| Admin | ✅ |
| Regular User | ❌ |

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Button not visible | Check user has manager role |
| ITAD Core fetch failed | Pack still generated with error notes |
| Missing BOL ID | Button hidden - complete manifest submission first |

---

## Support

For issues, contact IT Operations with the pack ID.
