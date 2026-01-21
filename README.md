# ITAD Core Workspace

## 🐳 Docker Runtime

> **Odoo source is NOT a runtime dependency. Docker image (`odoo:18.0`) is the only supported runtime.**

See [Docker Runbook](docs/runbook_docker.md) for all operational commands.

```powershell
# Start services (from repo root)
docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml up -d
```

---

## Codex Checklist
Use CODEX_CHECKLIST.md for every Codex change set / PR.

Note: tasks.md is the canonical Phase 0 Lock Review tracker.

## SoR Guardrails
Run the guard script to ensure canonical Phase 0 docs still contain the locked SoR wording and exclude forbidden phrases:

```
powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1
```
