# Odoo 18 Quality Gates & CI Runbook

This runbook captures the minimal, repeatable checks for Odoo 18 + OCA Field Service
so we avoid false "green" signals during development and CI.

## 1) CI: Smoke gates (required) vs Tests (on-demand)

Required (merge gate):
В GitHub Actions на каждый PR обязаны проходить install/upgrade smoke в Docker odoo:18.0:

Install smoke: установка itad_core на чистую базу (-i itad_core --stop-after-init)

Upgrade smoke: обновление itad_core на той же базе (-u itad_core --stop-after-init)

Эти smoke-проверки считаются минимальной гарантией installability и корректного addons_path/OCA-зависимостей. Ветка main защищена правилами Branch Protection: merge невозможен без успешного прохождения smoke checks.

Tests (not a merge gate yet):
Полный прогон тестов Odoo (--test-enable) выполняется по запросу (manual) или по расписанию (nightly), чтобы не замедлять каждый PR:

Manual run: GitHub → Actions → workflow odoo-tests → Run workflow

Nightly run: по cron (если включено)

Windows notes (Docker Desktop): use `--db_host=host.docker.internal`, run the container with `--entrypoint odoo` to avoid the default `db` host, and mount the repo to both `/mnt/extra-addons` and `/mnt/odoo-dev` (docs tests expect the latter).

Windows Docker Desktop command (PowerShell):
```powershell
docker run --rm --entrypoint odoo `
  -e ODOO_RC=/dev/null `
  -v "${PWD}:/mnt/extra-addons" `
  -v "${PWD}:/mnt/odoo-dev" `
  odoo:18.0 `
    --config=/dev/null `
    --db_host=host.docker.internal --db_port=5432 --db_user=odoo --db_password=odoo `
    -d itad_ci_tests `
    --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons/addons/common,/mnt/extra-addons/oca/field-service `
    -i itad_core `
    --test-enable --test-tags /itad_core `
    --stop-after-init
```

Rationale:
Smoke gates ловят критические ошибки установки/обновления и окружения (Docker + Postgres + addons_path). Полные тесты включаются отдельно, чтобы балансировать скорость PR-цикла и глубину проверки. Когда тесты стабилизируются и время прогона приемлемо — они переводятся в обязательные checks.

How to enable tests as a PR gate later:
Добавить --test-enable в install step smoke workflow (или включить отдельный test job), и отметить этот check как required в Branch Protection.
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
