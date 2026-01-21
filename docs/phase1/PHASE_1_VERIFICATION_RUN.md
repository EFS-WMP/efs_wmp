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

## API healthcheck (manual)

Locate the script path inside the Odoo container:

```powershell
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 sh -lc `
  "pwd; ls -la; find / -maxdepth 4 -type f -name api_healthcheck.sh 2>/dev/null | head"
```

If the script is not found (repo root not mounted), copy it into the container and set permissions:

```powershell
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml cp `
  scripts/api_healthcheck.sh odoo18:/tmp/api_healthcheck.sh
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T --user root odoo18 sh -lc `
  "chmod +x /tmp/api_healthcheck.sh"
```

Run the healthcheck (validated path):

```powershell
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 sh -lc `
  "/tmp/api_healthcheck.sh"
```

Optional overrides:

```powershell
docker compose -p odoo18 -f C:\odoo_dev\docker\odoo18\docker-compose.odoo18.yml exec -T odoo18 sh -lc `
  "TARGET_URL=http://host.docker.internal:8001/openapi.json MAX_RETRIES=5 SLEEP_TIME=2 /tmp/api_healthcheck.sh"
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

## C) Idempotency Proof (Phase 1 Valid Evidence)

Note: Port 8001 is UNVERIFIED; if different, update the URL once and keep it consistent.

This is NOT valid idempotency evidence if the submit was failing (422). Valid evidence requires two successful submits with the same Idempotency-Key and the same manifest_fingerprint, returning the same IDs.

```powershell
$idem="idem-$(New-Guid)"
$corr="corr-$(New-Guid)"

# First submit (must succeed and return IDs)
curl.exe -sS -D - -o C:\odoo_dev\docs\phase1\evidence\submit1_body.json `
  -X POST "http://localhost:8001/api/v1/pickup-manifests:submit" `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: $idem" `
  -H "X-Correlation-Id: $corr" `
  -d @C:\odoo_dev\docs\phase1\sample_payloads\pickup_manifest_min.json

# Second submit (same Idempotency-Key + same payload => must return SAME IDs)
curl.exe -sS -D - -o C:\odoo_dev\docs\phase1\evidence\submit2_body.json `
  -X POST "http://localhost:8001/api/v1/pickup-manifests:submit" `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: $idem" `
  -H "X-Correlation-Id: $corr" `
  -d @C:\odoo_dev\docs\phase1\sample_payloads\pickup_manifest_min.json
```

If either call returns 422, STOP: idempotency evidence is not valid yet. Fix payload (manifest_fingerprint) first.

Extract and compare IDs from `submit1_body.json` and `submit2_body.json`:
`pickup_manifest_id`, `bol_id`, and receiving anchor ID (if present). Expected: identical IDs and a duplicate outcome (DUPLICATE_RETURNED or equivalent).

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

✅ Idempotency proven only if:
- First submit succeeded and returned IDs
- Second submit with same Idempotency-Key + same manifest_fingerprint returned the same IDs
- Logs show correlation id + outcomes (ACCEPTED then DUPLICATE_RETURNED)

## Verification Log template

Paste the following outputs:

- Test-Path outputs
- docker compose ... ps
- pytest output
- Odoo scan output
- submit1/submit2 headers and bodies (evidence files)
- 422 response output
- log snippet for correlation id/outcome

## Rollback
Revert PR; doc-only + payload samples; no runtime impact.
