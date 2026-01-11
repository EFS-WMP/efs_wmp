# Phase 1 Verification Runbook

## Purpose
This runbook produces Phase 1 DoD evidence: green tests + idempotency + SoR guard rejection + correlation/outcome log snippets.

## Preconditions
ITAD Core and Odoo containers available.

Service names/ports are discovered and may differ; use discovery commands and copy the actual service name into later commands.

CANON_ITAD_COMPOSE = C:\odoo_dev\itad-core\docker-compose.itad-core.yml

Discovery commands:

```powershell
docker compose -p itad-core -f <CANON_ITAD_COMPOSE> ps
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml ps
```

## Step 0 - Record Test-Path evidence (copy/paste)

Run these and paste the outputs into the Verification Log section:

```powershell
Test-Path C:\odoo_dev\itad-core\docker-compose.itad-core.yml
Test-Path C:\odoo_dev\docker\itad-core\docker-`
compose.itad-core.yml
Test-Path C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml
Test-Path C:\odoo_dev\docker\odoo18\odoo.conf
```

## A) ITAD Core tests (in-container)

Discover services (UNVERIFIED service name; must be copied into subsequent commands):

```powershell
docker compose -p itad-core -f <CANON_ITAD_COMPOSE> ps
```

Run pytest (use actual service name from ps; default placeholder itad-core):

```powershell
docker compose -p itad-core -f <CANON_ITAD_COMPOSE> exec -T itad-core sh -lc "pytest -q"
```

## B) Odoo addon guardrail: fail on attrs=/states=

```powershell
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 `
  sh -lc "(! grep -RIn --include='*.xml' -E '\b(attrs|states)\s*=' /mnt/extra-addons-custom/itad_core)"
```

## C) E2E idempotency proof (API-level)

Note: Port 8001 is UNVERIFIED; if different, update the URL once and keep it consistent.

```powershell
$idem="idem-$(New-Guid)"
$corr="corr-$(New-Guid)"

curl.exe -sS -X POST "http://localhost:8001/api/v1/pickup-manifests:submit" `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: $idem" `
  -H "X-Correlation-Id: $corr" `
  -d @C:\odoo_dev\docs\phase1\sample_payloads\pickup_manifest_min.json

curl.exe -sS -X POST "http://localhost:8001/api/v1/pickup-manifests:submit" `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: $idem" `
  -H "X-Correlation-Id: $corr" `
  -d @C:\odoo_dev\docs\phase1\sample_payloads\pickup_manifest_min.json
```

## D) SoR guard proof (must reject operational-truth fields)

```powershell
$idem2="idem-$(New-Guid)"
$corr2="corr-$(New-Guid)"

curl.exe -i -sS -X POST "http://localhost:8001/api/v1/pickup-manifests:submit" `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: $idem2" `
  -H "X-Correlation-Id: $corr2" `
  -d @C:\odoo_dev\docs\phase1\sample_payloads\pickup_manifest_forbidden_fields.json
```

Expectation: HTTP 422 (or repo-standard validation error).

## E) Evidence extraction (logs: correlation id + attempt outcome)

Service name UNVERIFIED; replace from `docker compose ... ps`:

```powershell
docker compose -p itad-core -f <CANON_ITAD_COMPOSE> logs --tail 300 itad-core | Select-String -Pattern $corr
```

Requirement: the log snippet must show correlation id + attempt outcome (ACCEPTED/DUPLICATE_RETURNED/REJECTED/ERROR) or equivalent.

## Verification Log template

Paste the following outputs:

- Test-Path outputs
- docker compose ... ps
- pytest output
- Odoo scan output
- both idempotency POST outputs
- 422 response output
- log snippet for correlation id/outcome

## Rollback
Revert PR; doc-only + payload samples; no runtime impact.
