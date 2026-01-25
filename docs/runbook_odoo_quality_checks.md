# Odoo 18 Quality Gates & CI Runbook

This runbook captures the minimal, repeatable checks for Odoo 18 + OCA Field Service
so we avoid false "green" signals during development and CI.

## 1) Installability Smoke Test (Docker, Odoo 18)

**Goal:** confirm `itad_core` installs in the *exact* runtime environment.

```bash
# Inspect addons_path (inside the container)
python3 -c "import os; print(os.environ.get('ODOO_RC',''))"
grep -n "addons_path" /etc/odoo/odoo.conf || true

# Install + stop after init
# NOTE: use the exact addons_path from /etc/odoo/odoo.conf in this container.
# Example (replace with the paths from your odoo.conf):
odoo \
  --addons-path=/usr/lib/python3/dist-packages/odoo/addons,<custom_addons_path>,<oca_field_service_path> \
  -d itad_test \
  -i itad_core \
  --stop-after-init

Non-fatal warning to ignore during install/upgrade:

- `Warn: Can't find .pfb for face 'Courier'` (font warning; does not block module init)
```

## 2) OCA Field Service Dependency Check

**Goal:** ensure the OCA stack is present and version-pinned.

```bash
# Use the same base path that appears in addons_path.
ls -la <custom_addons_path>
find <oca_field_service_path> -maxdepth 3 -type f -name "__manifest__.py" | grep -i "fieldservice" || true
```

Recommended layout:

- `<custom_addons_path>` (this repo in the container)
- `<oca_field_service_path>` (OCA)

And `addons_path` must include both.

## 3) Manifest Coverage (XML/CSV must be referenced)

Use the existing CI hygiene script (supports allowlist entries):

```bash
python3 scripts/odoo_ci_checks.py
```

If a file is intentionally excluded, record it in `scripts/odoo_ci_allowlist.txt`.

## 4) SoR Boundary Guardrail (Outbox vs. Business Fields)

Outbox submissions **must not** mutate business truth fields in Odoo, except
for service metadata (send status, error, timestamps).

Minimum assertions for regressions:

- only `state`, `last_sent_at`, `last_error`, `attempt_count`, etc. change after a send
- no change to FSM business fields (weights, compliance flags, etc.)

## 5) Outbox Resiliency (Retry + Dead-Letter)

**Minimum behavior:**

- retry with exponential backoff + jitter
- cap attempts and mark dead-letter on exhaustion
- track `attempt_count`, `next_retry_at`, `last_http_status`, `last_error`

## 6) Registry + Cron Smoke Check (Post-Install)

```bash
odoo -d itad_test -u itad_core --stop-after-init

odoo shell -d itad_test <<'PY'
for model in ["itad.core.outbox", "itad.core.config", "itad.receipt.audit.log"]:
    print(model, "OK" if model in env else "MISSING")

crons = env["ir.cron"].search([("active", "=", True), ("name", "ilike", "ITAD")])
print("Active ITAD crons:", len(crons))
for cron in crons:
    print(cron.name, cron.nextcall)
PY
```

## 7) Pre-Merge Checklist (PR Template Ready)

1. ✅ Install/upgrade passes in Docker (`-i`, `-u`).
2. ✅ `addons_path` identical across dev/CI/prod.
3. ✅ `python3 scripts/odoo_ci_checks.py` clean.
4. ✅ Tests run under `--test-enable`.
5. ✅ SoR guard: no business-field mutation on outbox send.
6. ✅ Retry/backoff + dead-letter behavior unchanged.
7. ✅ Cron/registry smoke-check passes after install.
