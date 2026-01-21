# File: itad_core/models/itad_outbox.py

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
        self.order_id.write(order_vals)

    def _record_failure(self, error_message: str):
        now = fields.Datetime.now()
        attempt = self.attempt_count + 1
        delay = min(60 * (2 ** max(attempt - 1, 0)), 3600)  # 1m,2m,4m.. max 1h
        next_attempt = now + timedelta(seconds=delay)

        self.write(
            {
                "state": "failed",
                "attempt_count": attempt,
                "next_attempt_at": next_attempt,
                "last_error": error_message,
            }
        )

        self.order_id.write(
            {
                "itad_submit_state": "failed",
                "itad_last_error": error_message,
                "itad_last_submit_at": now,
                "itad_outbox_id": self.id,
                "itad_outbox_last_id": self.id,
            }
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
            rec.write({"state": "pending", "next_attempt_at": now, "last_error": False})
            rec.order_id.write(
                {
                    "itad_submit_state": "pending",
                    "itad_last_error": False,
                    "itad_outbox_id": rec.id,
                    "itad_outbox_last_id": rec.id,
                }
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
