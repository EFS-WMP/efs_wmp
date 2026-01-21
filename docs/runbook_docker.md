# Docker-Only Odoo 18 Runbook

> **Runtime**: Odoo source is NOT a runtime dependency. Docker image `odoo:18.0` is the only supported runtime.

---

## ⚠️ Environment Requirements

- **Run all commands from repo root**: `c:\odoo_dev`
- **Shell**: PowerShell (Windows). WSL/Linux users need adapted paths.
- **Docker Desktop** must be running

---

## 📋 Quick Reference

| Action | Command |
|--------|---------|
| Start services | `docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml up -d` |
| Stop services | `docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml down` |
| View logs | `docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml logs -f odoo18` |
| Upgrade module | See [One-Shot Upgrade](#one-shot-upgrade) |
| Run tests | See [Tests](#tests) |

---

## 🚀 Start Services

```powershell
cd c:\odoo_dev
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml up -d
```

Access Odoo at: http://localhost:8070

---

## 🔄 One-Shot Upgrade

> [!IMPORTANT]
> **Port Conflict Rule**: Always use `run --rm` for one-shot operations. Never use `exec` when the main odoo18 service is running—it causes "Address already in use" errors.

```powershell
# Ensure DB is running
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml up -d db18

# Upgrade itad_core
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http --http-port=0
```

Expected: Exit 0, no errors.

---

## 🧪 Tests

```powershell
# Ensure DB is running
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml up -d db18

# Run tests
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo --test-enable --test-tags=itad_core -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http --http-port=0
```

Expected: `0 failed, 0 errors` in output.

Save test log:
```powershell
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo --test-enable --test-tags=itad_core -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http --http-port=0 `
  2>&1 | Tee-Object -FilePath artifacts/odoo_itad_core_tests.log
```

---

## ✅ Mount Validation (Sanity Checks)

Verify addon mounts are correct:

```powershell
# Check itad_core mounted
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  sh -lc "ls -la /mnt/extra-addons-custom/itad_core/__manifest__.py"

# Check OCA field-service mounted
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  sh -lc "ls -la /mnt/extra-addons-odoo18/oca/field-service/fieldservice/__manifest__.py"
```

Expected: Both show file listings (not "No such file").

---

## 🎯 DoD-Check (Definition of Done)

Run this to verify upgrade worked and crons exist:

```powershell
# 1. Upgrade and verify exit 0
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core --stop-after-init --no-http --http-port=0

# 2. Check cron XMLIDs exist (Odoo shell one-liner)
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 `
  odoo shell -c /etc/odoo/odoo.conf -d odoo18_db --stop-after-init --no-http -c "
from odoo import api, SUPERUSER_ID
env = api.Environment(self.env.cr, SUPERUSER_ID, {})
crons = ['itad_core.ir_cron_itad_outbox_process', 'itad_core.ir_cron_archive_audit_logs']
for xmlid in crons:
    rec = env.ref(xmlid, raise_if_not_found=False)
    print(f'{xmlid}: {\"EXISTS\" if rec else \"MISSING\"} active={getattr(rec, \"active\", None)}')
"
```

---

## 🔧 Compose Configuration

| Setting | Value |
|---------|-------|
| **Image** | `odoo:18.0` (production: pin digest) |
| **Ports** | `8070:8069` (web), `8072:8072` (longpoll) |
| **Config** | `./docker/odoo18/odoo.conf` → `/etc/odoo/odoo.conf` |
| **Addons** | `./addons/common` → `/mnt/extra-addons-custom` |
| | `./addons/odoo18` → `/mnt/extra-addons-odoo18` |

---

## 🔒 Production Notes

For production/CI, pin the Docker image digest:
```yaml
image: odoo@sha256:<digest>
```

Get current digest:
```powershell
docker pull odoo:18.0
docker inspect --format='{{index .RepoDigests 0}}' odoo:18.0
```
