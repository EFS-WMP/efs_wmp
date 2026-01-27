# File: itad_core/models/itad_outbox.py

import hashlib
import json
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItadCoreOutbox(models.Model):
    _name = "itad.core.outbox"
    _description = "ITAD Core Outbox"
    _order = "create_date asc"
    _rec_name = "idempotency_key"

    order_id = fields.Many2one("fsm.order", required=True, ondelete="cascade", index=True)

    state = fields.Selection(
        [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")],
        default="pending",
        required=True,
        index=True,
    )

    idempotency_key = fields.Char(required=True, readonly=True, index=True)
    correlation_id = fields.Char(required=True, readonly=True, index=True)

    payload_json = fields.Text(readonly=True)
    payload_sha256 = fields.Char(readonly=True)

    attempt_count = fields.Integer(default=0, readonly=True)
    next_attempt_at = fields.Datetime(readonly=True)
    last_error = fields.Text(readonly=True)

    # Response snapshot (optional but handy for UI/debug)
    itad_pickup_manifest_id = fields.Char(readonly=True)
    itad_manifest_no = fields.Char(readonly=True)
    itad_status = fields.Char(readonly=True)
    itad_bol_id = fields.Char(readonly=True)
    itad_geocode_gate = fields.Char(readonly=True)
    itad_receiving_id = fields.Char(readonly=True)
    itad_receiving_weight_record_id = fields.Char(
        related="order_id.itad_receiving_weight_record_id",
        readonly=True,
    )

    def _get_config(self):
        # Expect config model to return (base_url, token)
        return self.env["itad.core.config"].get_itad_core_config()

    def _get_retry_config(self):
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "max_attempts": int(icp.get_param("itad_core.outbox_max_attempts", "5")),
            "base_delay_seconds": int(icp.get_param("itad_core.outbox_backoff_base_seconds", "60")),
            "max_delay_seconds": int(icp.get_param("itad_core.outbox_max_delay_seconds", "3600")),
            "jitter_ratio": float(icp.get_param("itad_core.outbox_backoff_jitter_ratio", "0.25")),
        }

    def _deterministic_jitter(self, base_delay, attempt):
        if not self.idempotency_key:
            return 0
        raw = f"{self.idempotency_key}:{attempt}".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        jitter_range = max(1, int(base_delay * self._get_retry_config()["jitter_ratio"]))
        return int(digest, 16) % (jitter_range + 1)

    def _is_retryable_status(self, status_code):
        if status_code is None:
            return True
        if status_code >= 500:
            return True
        if status_code in (408, 429):
            return True
        if 400 <= status_code < 500:
            return False
        return True

    @api.model
    def _map_outbox_state_to_submit_state(self, outbox_state):
        mapping = {
            "pending": "pending",
            "sent": "sent",
            "failed": "failed",
            "dead_letter": "failed",
        }
        return mapping.get(outbox_state, "failed")

    def _filter_outbox_write_vals(self, vals):
        """Filter write values to fields defined on every record in the recordset."""
        if not self:
            return {}
        return {
            field: value
            for field, value in vals.items()
            if all(field in rec._fields for rec in self)
        }

    def _sql_update_fsm_order_itad_fields(self, order, vals):
        """Write ITAD fields via SQL to avoid FSM write side effects."""
        invalid_keys = [key for key in vals if not key.startswith("itad_")]
        if invalid_keys:
            raise ValueError(f"Only itad_* fields are allowed: {', '.join(invalid_keys)}")

        if not order:
            return

        order_sudo = order.sudo()
        protected_fields = []
        snapshots = {}
        if hasattr(order_sudo, "_get_telemetry_protected_fields"):
            protected_fields = order_sudo._get_telemetry_protected_fields()
        compliance_fields = [
            "itad_receipt_weight_lbs",
            "itad_receipt_material_code",
            "itad_receipt_confirmed_at",
            "itad_receipt_notes",
            "itad_receipt_idempotency_key",
        ]
        protected_fields.extend(
            field
            for field in compliance_fields
            if field in order_sudo._fields and field not in protected_fields
        )
        if protected_fields:
            snapshots = order_sudo._snapshot_telemetry_fields(protected_fields)

        for rec in order_sudo:
            update_vals = {}
            for field, value in vals.items():
                if field not in rec._fields:
                    continue
                field_def = rec._fields[field]
                if not field_def.store:
                    continue
                if field_def.type == "many2one":
                    value = value.id if hasattr(value, "id") and value else value or None
                update_vals[field] = value
            if not update_vals:
                continue
            set_clause = ", ".join(f"{field}=%s" for field in update_vals)
            params = list(update_vals.values()) + [rec.id]
            self.env.cr.execute(
                f"UPDATE {rec._table} SET {set_clause} WHERE id=%s",
                params,
            )
            rec._invalidate_cache(fnames=list(update_vals))

        if protected_fields:
            order_sudo._restore_telemetry_fields(snapshots, protected_fields)

    def _send_to_itad_core(self):
        self.ensure_one()
        if not self.payload_json:
            raise UserError(_("Missing payload_json."))

        base_url, token = self._get_config()
        url = base_url.rstrip("/") + "/api/v1/pickup-manifests:submit"

        headers = {
            "Idempotency-Key": self.idempotency_key,
            "X-Correlation-Id": self.correlation_id,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = json.loads(self.payload_json)
        if "manifest_fingerprint" not in payload:
            payload["manifest_fingerprint"] = self.payload_sha256
        resp = requests.post(url, json=payload, headers=headers, timeout=15)

        if 200 <= resp.status_code < 300:
            return resp.json()

        raise UserError(
            _("ITAD Core error %(status)s: %(body)s")
            % {"status": resp.status_code, "body": resp.text}
        )

    def _record_success(self, data: dict):
        now = fields.Datetime.now()
        receiving_weight_record_id = data.get("receiving_weight_record_id") or data.get("receiving_id")
        self.write(
            self._filter_outbox_write_vals(
                {
                    "state": "sent",
                    "attempt_count": self.attempt_count + 1,
                    "next_attempt_at": False,
                    "last_error": False,
                    "itad_pickup_manifest_id": data.get("pickup_manifest_id"),
                    "itad_manifest_no": data.get("manifest_no"),
                    "itad_status": data.get("status"),
                    "itad_bol_id": data.get("bol_id"),
                    "itad_geocode_gate": data.get("geocode_gate"),
                    "itad_receiving_id": data.get("receiving_id"),
                }
            )
        )

        # Phase 1: FSM is SoR; update read-only ITAD refs on order
        order_vals = {
            "itad_submit_state": "sent",
            "itad_pickup_manifest_id": data.get("pickup_manifest_id"),
            "itad_manifest_no": data.get("manifest_no"),
            "itad_manifest_status": data.get("status"),
            "itad_bol_id": data.get("bol_id"),
            "itad_geocode_gate": data.get("geocode_gate"),
            "itad_last_submit_at": now,
            "itad_last_error": False,
            "itad_outbox_id": self.id,
            "itad_outbox_last_id": self.id,
            "itad_receipt_state": "pending",  # Phase 2.1: Ready for receiving confirmation
        }
        if receiving_weight_record_id:
            order_vals["itad_receiving_weight_record_id"] = receiving_weight_record_id
            if "itad_receiving_id" in self.order_id._fields and not self.order_id.itad_receiving_id:
                order_vals["itad_receiving_id"] = data.get("receiving_id") or receiving_weight_record_id
        self._sql_update_fsm_order_itad_fields(self.order_id, order_vals)

    def _record_failure(self, error_message: str):
        now = fields.Datetime.now()
        attempt = self.attempt_count + 1
        delay = min(60 * (2 ** max(attempt - 1, 0)), 3600)  # 1m,2m,4m.. max 1h
        next_attempt = now + timedelta(seconds=delay)

        self.write(
            self._filter_outbox_write_vals(
                {
                    "state": "failed",
                    "attempt_count": attempt,
                    "next_attempt_at": next_attempt,
                    "last_error": error_message,
                }
            )
        )

        self._sql_update_fsm_order_itad_fields(
            self.order_id,
            {
                "itad_submit_state": "failed",
                "itad_last_error": error_message,
                "itad_last_submit_at": now,
                "itad_outbox_id": self.id,
                "itad_outbox_last_id": self.id,
            },
        )

    def _process_one(self):
        self.ensure_one()
        try:
            data = self._send_to_itad_core()
            self._record_success(data)
        except Exception as exc:
            self._record_failure(str(exc))

    def action_retry(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.write(
                rec._filter_outbox_write_vals(
                    {
                        "state": "pending",
                        "attempt_count": 0,
                        "next_attempt_at": now,
                        "last_error": False,
                    }
                )
            )
            vals = {
                "itad_last_error": False,
                "itad_outbox_id": rec.id,
                "itad_outbox_last_id": rec.id,
                "itad_submit_state": "pending",
            }
            self._sql_update_fsm_order_itad_fields(
                rec.order_id,
                vals,
            )
        return True

    @api.model
    def _cron_process_itad_outbox(self):
        now = fields.Datetime.now()
        records = self.search(
            [
                "|",
                ("state", "=", "pending"),
                "&",
                ("state", "=", "failed"),
                "|",
                ("next_attempt_at", "=", False),
                ("next_attempt_at", "<=", now),
            ],
            order="create_date asc",
        )
        for rec in records:
            rec._process_one()
        return True
