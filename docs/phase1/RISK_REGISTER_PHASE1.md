# RISK REGISTER — Phase 1 (Top 10)

1) SoR contradictions in docs lead to wrong implementation (dual-write).
   - Mitigation: SoR guard + single canonical docs folder; archive duplicates.

2) Odoo18 → ITAD Core calls from isolated compose networks fail (DNS assumptions).
   - Mitigation: use host.docker.internal in dev; document explicitly.

3) Idempotency key regenerated on retry creates duplicates.
   - Mitigation: store idempotency key on outbox row + originating Odoo record; never regenerate.

4) Odoo UI blocks on synchronous HTTP call, techs get stuck.
   - Mitigation: outbox + cron retry; UI shows “pending/failed” rather than blocking completion.

5) POD files handled inconsistently (mutable evidence).
   - Mitigation: store files in Odoo attachments; send hashes/refs; ITAD Core stores immutable refs/hashes only.

6) Route/stop mapping unclear due to OCA module model differences.
   - Mitigation: verify technical model names in Odoo before coding mappings; document in DATA_MAPPING.md.

7) Engineers accidentally use /mnt/extra-addons ghost mount code.
   - Mitigation: remove the mount OR mount an explicitly empty folder and add a guard that fails if it contains manifests.

8) OCA field-service module dependencies drift.
   - Mitigation: pin git branch 18.0; track commit SHA; keep it in addons/odoo18 only.

9) Error handling not user-visible; failures become silent.
   - Mitigation: outbox UI view + last error + retry; ITAD Core standardized error payload.

10) Phase 1 scope creep into pricing/settlement engine.
   - Mitigation: non-goals locked; only snapshot placeholders allowed (Phase 0 J).

Go/No-Go signals:
- NO-GO if any SoR contradiction remains or any route execution truth is written in ITAD Core.
- NO-GO if submit endpoint is not idempotent or duplicate-safe.

