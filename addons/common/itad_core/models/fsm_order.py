# File: itad_core/models/fsm_order.py

import base64
import hashlib
import json
import uuid

from odoo import _, fields, models
from odoo.exceptions import UserError


class FsmOrder(models.Model):
    _inherit = "fsm.order"

    # Phase 1: only FSM is SoR; store ITAD Core refs as read-only
# Находим itad_submit_state = fields.Selection(
    itad_submit_state = fields.Selection(
        [("new", "New"), ("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")],
        default="new",
        readonly=True,
        copy=False,
    )


    itad_manifest_no = fields.Char(readonly=True, copy=False)
    itad_manifest_status = fields.Char(readonly=True, copy=False)
    itad_bol_id = fields.Char(readonly=True, copy=False)
    itad_receiving_id = fields.Char(readonly=True, copy=False, string="Receiving ID")
    itad_receiving_weight_record_id = fields.Char(
        readonly=True,
        copy=False,
        string="Receiving Weight Record ID",
    )
    itad_geocode_gate = fields.Char(readonly=True, copy=False, string="Geocode Gate")
    itad_last_submit_at = fields.Datetime(readonly=True, copy=False)
    itad_last_error = fields.Text(readonly=True, copy=False)
    itad_pickup_manifest_id = fields.Char(readonly=True, copy=False, string="ITAD Pickup Manifest ID")
    itad_outbox_id = fields.Many2one("itad.core.outbox", readonly=True, copy=False)
    itad_outbox_last_id = fields.Many2one("itad.core.outbox", string="Last Outbox Record", readonly=True, copy=False)

    def _itad_collect_pod_evidence(self):
        self.ensure_one()
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "=", self.id)]
        )
        evidence = []
        for attachment in attachments:
            sha256_hex = ""
            if attachment.datas:
                try:
                    raw = base64.b64decode(attachment.datas)
                    sha256_hex = hashlib.sha256(raw).hexdigest()
                except Exception:
                    sha256_hex = ""
            evidence.append(
                {
                    "ref": f"odoo-attachment:{attachment.id}",
                    "sha256": sha256_hex,
                    "filename": attachment.name,
                    "mimetype": attachment.mimetype,
                }
            )
        return evidence

    def _itad_build_payload(self):
        self.ensure_one()
        completed_at = self.date_end or fields.Datetime.now()
        location = getattr(self, "location_id", False)
        customer = getattr(self, "partner_id", False)

        payload = {
            "source_system": "odoo18",
            "completed_at": fields.Datetime.to_string(completed_at),
            "odoo_refs": {
                "odoo_day_route_id": None,
                "odoo_stop_id": None,
                "odoo_pickup_occurrence_id": str(self.id),
                "odoo_work_order_id": self.name or str(self.id),
                "customer_id": str(customer.id) if customer else None,
                "service_location_id": str(location.id) if location else None,
            },
            "route_snapshot_json": {
                "fsm_order_id": self.id,
                "fsm_stage": self.stage_id.name if self.stage_id else None,
            },
            "location_snapshot_json": {
                "name": location.name if location else None,
                "street": getattr(location, "street", None) if location else None,
                "street2": getattr(location, "street2", None) if location else None,
                "city": getattr(location, "city", None) if location else None,
                "zip": getattr(location, "zip", None) if location else None,
                "state": location.state_id.name if location and location.state_id else None,
                "country": location.country_id.name if location and location.country_id else None,
            },
            "pod_evidence": self._itad_collect_pod_evidence(),
        }

        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        payload_sha256 = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        return payload_json, payload_sha256

    def action_submit_pickup_manifest(self):
        for order in self:
            if not order.is_closed:
                raise UserError(_("FSM Order must be completed before submitting pickup manifest."))

            outbox = self.env["itad.core.outbox"].search(
                [("order_id", "=", order.id)], order="id desc", limit=1
            )
            if outbox:
                if outbox.state == "sent":
                    raise UserError(_("Pickup Manifest already submitted."))
                if outbox.state == "failed":
                    outbox.action_retry()
                order.write(
                    {
                        "itad_outbox_id": outbox.id,
                        "itad_outbox_last_id": outbox.id,
                        "itad_submit_state": outbox.state,
                    }
                )
                continue

            payload_json, payload_sha256 = order._itad_build_payload()
            outbox = self.env["itad.core.outbox"].create(
                {
                    "order_id": order.id,
                    "state": "pending",
                    "idempotency_key": uuid.uuid4().hex,
                    "correlation_id": uuid.uuid4().hex,
                    "payload_json": payload_json,
                    "payload_sha256": payload_sha256,
                }
            )
            order.write(
                {
                    "itad_outbox_id": outbox.id,
                    "itad_outbox_last_id": outbox.id,
                    "itad_submit_state": "pending",
                    "itad_last_error": False,
                    "itad_last_submit_at": fields.Datetime.now(),
                }
            )
        return True
