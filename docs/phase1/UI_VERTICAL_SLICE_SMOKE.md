# Phase 1 UI Vertical Slice: Smoke Test Runbook

**Duration:** ~15 minutes  
**Scope:** End-to-end flow from Odoo18 FSM Order submission through ITAD Core pickup manifest creation with idempotent retry verification.

**Prerequisites:**
- Odoo18 container running with itad_core addon installed
- ITAD Core API running and accessible at `http://host.docker.internal:8001`
- Both databases initialized (see docker-compose files)
- Field Service module installed in Odoo

---

## Phase 1 Scenario: Submit Pickup Manifest with POD Evidence

### Step 1: Create FSM Order in Odoo (2 min)

1. Open Odoo at `http://localhost:8070` (or configured port)
2. Navigate to **Field Service** → **Work Orders**
3. Click **Create**
4. Fill in:
   - **Title:** `Phase 1 Test Order - POD Verification`
   - **Location:** Select any available location (e.g., `Test Location`)
   - **Customer:** Select any customer
   - **Stage:** Do NOT set yet; leave as draft or in-progress
5. **Save** (do not submit yet—state must be completed first)

### Step 2: Attach POD Evidence (2 min)

1. On the saved order, click **Attach Files** (or use the Attachments area)
2. Upload a test image or document (e.g., `test-pod.jpg`)
3. Verify attachment appears in the order
4. **Note:** The button will use SHA256 hash of this evidence

### Step 3: Mark Order as Completed (1 min)

1. In the **Stage** field, select a **Completed** stage (e.g., `Completed`)
   - The outbox button visibility is controlled by `itad_submit_state` (not stage directly)
2. **Save**
3. Verify order now shows `itad_submit_state = "Not Sent"` (visible in ITAD tab or list view)

### Step 4: Click "Submit Pickup Manifest" Button (1 min)

1. On the completed order form, navigate to the **ITAD** section in the header
2. Locate and click the **Submit Pickup Manifest** button (blue/highlighted button)
3. **Expected result:** Button click completes without error

### Step 5: Observe Outbox Creation and State (2 min)

1. On the order, check the **ITAD** tab for:
   - **Submit State:** Should change to `"Pending"`
   - **Last Submit At:** Should show current timestamp
   - **Last Error:** Should be empty
2. Navigate to **Field Service** → **ITAD Core** → **Outbox** menu
3. Find the order's outbox record:
   - Verify **State:** `Pending`
   - Verify **Idempotency Key:** Non-empty hex string
   - Verify **Correlation ID:** Non-empty hex string
   - Note the IDs for verification in Step 9

### Step 6: Verify Cron Processes and Transitions to SENT (3 min)

1. The cron `ITAD Core Outbox Processor` runs every 5 minutes
   - **Option A (immediate test):** Manually trigger cron:
     - SSH/terminal into Odoo container:
       ```bash
       docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml exec -T odoo18 bash
       ```
     - Inside container, run Odoo shell:
       ```bash
       odoo -c /etc/odoo/odoo.conf -d <DB_NAME> --shell
       ```
     - Execute:
       ```python
       env["itad.core.outbox"]._cron_process_itad_outbox()
       ```
     - Exit shell (`Ctrl+D`)
   - **Option B (wait):** Wait up to 5 minutes for cron to run naturally

2. Refresh the outbox record → verify **State** changed to `Sent`

3. Check returned IDs in outbox:
   - **Pickup Manifest ID:** Should be populated (e.g., `pm-uuid`)
   - **Manifest No:** Should be populated (e.g., `MF-2026-001`)
   - **BOL ID:** Should be populated (e.g., `bol-uuid`)
   - **Geocode Gate:** Should be populated (e.g., `AUTO_ACCEPT`, `NEEDS_REVIEW`, `MANUAL_REQUIRED`)

### Step 7: Verify Order Updated with Read-Only Refs (1 min)

1. Return to the original FSM order
2. Verify **ITAD** tab now shows:
   - **Pickup Manifest ID:** Matches outbox
   - **Manifest No:** Matches outbox
   - **BOL ID:** Matches outbox
   - **Geocode Gate:** Matches outbox
   - **Submit State:** Now `"Sent"` (changed from "Pending")
3. All fields are **read-only** (grayed out, non-editable)

---

## Phase 1 Verification: Idempotent Retry Behavior

This is NOT valid idempotency evidence if the submit was failing (422). Valid evidence requires two successful submits with the same Idempotency-Key and the same manifest_fingerprint, returning the same IDs.

### Step 8: Click Button Again (Idempotent) - (1 min)

1. With the order still open (still in SENT state), click **Submit Pickup Manifest** button again
2. **Expected behavior:** Depending on current state:
   - If outbox state is `Sent`: Button is **invisible** (modifiers rule: invisible when itad_submit_state='sent')
   - If outbox state is `Failed`: Button becomes `Retry` and resets state to `Pending`
3. **Verify:** Idempotency key was **NOT regenerated**
   - Open the outbox record → **Idempotency Key** should be the **same** as in Step 5

### Step 9: Simulate Failure and Verify Retry Preserves Key (2 min)

**For advanced testing (requires manual DB manipulation or mock):**

1. Query the outbox record and manually set state to `Failed`:
   ```sql
   UPDATE itad_core_outbox SET state='failed' WHERE id=<OUTBOX_ID>;
   ```

2. On the order, the button should now be visible again (if not in SENT state)

3. Click **Submit Pickup Manifest** (or if button not visible, navigate to outbox and click **Retry**)

4. Trigger cron again (Option A from Step 6)

5. Verify in outbox:
   - **Idempotency Key:** Same as original (from Step 5)
   - **State:** Back to `Sent` (or pending if still failing)
   - **Attempt Count:** Should be incremented (e.g., 2, 3, etc.)
   - **Next Attempt At:** Should be cleared when transitioning to SENT

---

## Phase 1 Verification: No Duplicate BOLs Created

### Step 10: Check ITAD Core for Single BOL (1 min)

**Direct DB query (optional, requires access to ITAD Core DB):**

```sql
SELECT id, bol_number, source_type, pickup_manifest_id, created_at
FROM bol
WHERE source_type = 'PICKUP'
  AND pickup_manifest_id = '<PM_ID_FROM_STEP_6>';
```

**Expected:** Exactly 1 BOL record, with:
- `source_type = 'PICKUP'`
- `pickup_manifest_id` = the manifest returned in Step 6
- Even if cron ran twice or button clicked twice, only 1 BOL exists

**Rationale:** 1:1 binding enforced by UNIQUE constraint on `(pickup_manifest_id)` when `source_type='PICKUP'`

---

## Phase 1 Verification: XML Compliance (Automated)

### Step 11: Run Guardrail Test (1 min)

1. SSH into Odoo container:
   ```bash
   docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml exec -T odoo18 bash
   ```

2. Run test:
   ```bash
   odoo -c /etc/odoo/odoo.conf -d <DB_NAME> -u itad_core --stop-after-init --test-enable
   ```

3. **Expected:** All tests pass, including `test_no_attrs_states`
   - Output should include: `✅ test_no_attrs_states PASSED`

---

## Phase 1 Verification: SoR Guard (API Rejects Dispatch State)

### Step 12: Test SoR Guard (1 min, optional curl test)

**Requires curl or Postman; tests directly against ITAD Core API:**

1. Payload with forbidden field (should fail):
   ```bash
   curl -X POST http://host.docker.internal:8001/api/v1/pickup-manifests:submit \
     -H "Content-Type: application/json" \
     -H "Idempotency-Key: test-$(uuidgen)" \
     -d '{
       "source_system": "odoo18",
       "manifest_fingerprint": "'$(echo -n test | sha256sum | cut -d' ' -f1)'",
       "completed_at": "2026-01-04T12:00:00+00:00",
       "dispatch_status": "DISPATCHED",
       "odoo_refs": {...},
       "route_snapshot_json": {...},
       "location_snapshot_json": {...},
       "pod_evidence": []
     }'
   ```

2. **Expected response:** `422 Unprocessable Entity`
   ```json
   {
     "detail": "Forbidden operational truth field 'dispatch_status' found at 'dispatch_status'. Odoo18 is the dispatch SoR..."
   }
   ```

3. Payload without forbidden field (should succeed):
   ```bash
   curl -X POST http://host.docker.internal:8001/api/v1/pickup-manifests:submit \
     -H "Content-Type: application/json" \
     -H "Idempotency-Key: test-$(uuidgen)" \
     -d '{
       "source_system": "odoo18",
       "manifest_fingerprint": "'$(echo -n test | sha256sum | cut -d' ' -f1)'",
       "completed_at": "2026-01-04T12:00:00+00:00",
       "odoo_refs": {...},
       "route_snapshot_json": {...},
       "location_snapshot_json": {...},
       "pod_evidence": []
     }'
   ```

4. **Expected response:** `200 OK` with manifest/BOL IDs

---

## Acceptance Criteria Checklist

- [ ] **Step 4:** Order submit button exists and is clickable
- [ ] **Step 5:** Outbox created with state=pending, stable idempotency/correlation keys
- [ ] **Step 6:** Cron transitions outbox to sent, returns manifest/BOL IDs
- [ ] **Step 7:** Order ITAD tab populated with read-only returned IDs
- [ ] **Step 8:** Idempotency key NOT regenerated on repeat click
- [ ] **Step 9:** Retry logic reuses outbox row and preserves key
- [ ] **Step 10:** Exactly 1 BOL created for PICKUP source type (no duplicates)
- [ ] **Step 11:** Guardrail test passes (no attrs=/states= in XML)
- [ ] **Step 12:** API rejects payloads with operational truth fields (422)

---

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Button not visible on order | Verify stage is `Completed`; verify itad_submit_state != "sent" |
| Cron doesn't run | Manually trigger via shell (Option A) or check ir.cron record active status |
| Outbox state stays "pending" | Check error in outbox.last_error; verify ITAD Core URL reachable |
| HTTP 400 "Idempotency-Key required" | Verify endpoint receiving correct headers |
| HTTP 422 "Forbidden field" | Payload contains dispatch state; remove and retry |
| Different BOL IDs on retry | Check for unique constraint violation in DB; verify dedup logic |

---

## Reference: Configuration

**Odoo config parameters (set in `Settings` → `System Parameters`):**
- `itad_core.base_url` - ITAD Core API URL (default: `http://host.docker.internal:8001`)
- `itad_core.token` - Bearer token if required (default: empty)
- `itad_core.port` - Port when base_url not set (default: 8001)

**Cron job:** `ITAD Core Outbox Processor` runs every 5 minutes (ir.cron record in manifest data)

**Database views:**
- Odoo: `itad_core_outbox` table (order_id FK, state, idempotency_key, returned IDs)
- ITAD Core: `pickup_manifest`, `bol`, `pickup_manifest_integration_attempt` tables

---

**Phase 1 Smoke Test Complete!**
- Settings -> Technical -> System Parameters -> Create:
  - Key: `itad_core.base_url` Value: `http://host.docker.internal:<itad_port>`
  - Key: `itad_core.token` Value: `<token>`

Optional (Odoo shell):
```
env["ir.config_parameter"].sudo().set_param("itad_core.base_url", "http://host.docker.internal:<itad_port>")
env["ir.config_parameter"].sudo().set_param("itad_core.token", "<token>")
```

## Happy Path (UI)
1) Enable Developer Mode (Settings -> Activate the developer mode).
2) Create an FSM Order:
   - Field Service -> Orders -> Create.
   - Fill required fields (Location, Team, etc.).
3) Attach POD evidence:
   - Open the chatter and upload a file (paperclip).
4) Mark the order as completed (move to a closed stage).
5) Click **Submit Pickup Manifest** in the header.
6) Verify Outbox row:
   - ITAD Core -> Outbox.
   - New row is **PENDING** with non-empty `idempotency_key` and `correlation_id`.
7) Run cron:
   - Settings -> Technical -> Automation -> Scheduled Actions.
   - Open **ITAD Core Outbox Processor** -> Run Manually.
8) Verify SENT and refs:
   - Outbox row becomes **SENT** and stores `manifest_no`, `pickup_manifest_id`, `bol_id`.
   - Open the FSM Order -> **ITAD** tab shows read-only ITAD refs:
     - `itad_pickup_manifest_id` / `itad_manifest_no`
     - `itad_bol_id`
     - `itad_geocode_gate` (if returned)

## Idempotency / No Duplicates
If a submit returned 422, STOP: idempotency evidence is not valid yet. Fix manifest_fingerprint and repeat with a successful submit.

Option A (retry from Outbox):
1) Run the cron again or use **Retry** if the row is FAILED.
2) Acceptance:
   - ITAD IDs on the FSM Order remain unchanged.
   - `attempt_count` increments on the outbox row.

Option B (submit again):
1) Click **Submit Pickup Manifest** again on the same order.
2) Acceptance:
   - No new manifest/BOL IDs are created.
   - Existing IDs on the order remain unchanged.

## Failure Path (ITAD Core Error)
1) Temporarily set an invalid config:
   - Set `itad_core.token` to an invalid value, OR
   - Set `itad_core.base_url` to an unreachable URL.
2) Run the cron or click **Retry** on the outbox row.
3) Verify:
   - Outbox becomes **FAILED**.
   - `last_error` is populated.
   - `idempotency_key` remains the same (no regeneration).
4) Restore correct config and retry:
   - Outbox transitions to **SENT**.
   - ITAD refs populate on the FSM Order.

## Fast Spot Checks
- Outbox list:
  - Field Service -> ITAD Core -> Outbox (or Outbox (Failed))
- Manual cron run:
  - Settings -> Technical -> Automation -> Scheduled Actions -> ITAD Core Outbox Processor -> Run Manually
- Expected screenshots list:
  - FSM Order form with **ITAD** tab and read-only refs.
  - Outbox list showing **PENDING**.
  - Outbox list showing **SENT** with IDs.
  - Outbox list showing **FAILED** with `last_error`.

## Acceptance Criteria
PASS: After retry/cron, no duplicates (same ITAD IDs on the FSM Order)
PASS: On ITAD error, outbox -> FAILED, `idempotency_key` preserved, retry works after fixing config
