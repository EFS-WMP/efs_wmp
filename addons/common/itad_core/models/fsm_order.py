# File: itad_core/models/fsm_order.py

import base64
import hashlib
import json
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FsmOrder(models.Model):
    _inherit = "fsm.order"

    TELEMETRY_PROTECTED_FIELDS = {
        "stage_id",
        "date_start",
        "date_end",
        "scheduled_date",
        "location_id",
        "partner_id",
        "team_id",
        "priority",
        "name",
    }

    # Phase 1: only FSM is SoR; store ITAD Core refs as read-only
# Находим itad_submit_state = fields.Selection(
    itad_submit_state = fields.Selection(
        [
            ("new", "New"),
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("dead_letter", "Dead Letter"),
        ],
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

    customer_name = fields.Char(
        compute="_compute_customer_name",
        store=True,
        readonly=True,
        string="Customer",
    )

    # Phase 2.1: Receipt confirmation state (operational visibility only; ITAD Core is SoR)
    itad_receipt_state = fields.Selection(
        selection=[
            ("pending", "Pending Receipt"),
            ("received", "Received"),
            ("exception", "Receipt Exception"),
        ],
        string="ITAD Receipt Status",
        readonly=True,
        copy=False,
        help="Tracks physical receipt confirmation at the facility. ITAD Core is SoR for receiving_weight_record.",
    )
    itad_receipt_confirmed_at = fields.Datetime(
        string="Receipt Confirmed At",
        readonly=True,
        copy=False,
    )
    itad_receipt_weight_lbs = fields.Float(
        string="Receipt Weight (lbs)",
        readonly=True,
        copy=False,
        digits=(12, 2),
    )
    itad_receipt_material_code = fields.Char(
        string="Receipt Material Code",
        readonly=True,
        copy=False,
    )
    itad_receipt_notes = fields.Text(
        string="Receipt Notes",
        readonly=True,
        copy=False,
        help="Notes entered during receiving (from the Receiving Wizard).",
    )
    
    # Phase 2.2b: Persistent idempotency key for retry support
    itad_receipt_idempotency_key = fields.Char(
        string="Receipt Idempotency Key",
        readonly=True,
        copy=False,
        help="Stable idempotency key for receipt confirmation retries. Backfilled by migration for legacy exception records.",
    )
    
    # Phase 2.5: Data Quality - Variance Fields
    itad_variance_flag = fields.Boolean(
        string="Variance Flag",
        default=False,
        index=True,
        copy=False,
        help="True if order has data quality variance requiring review",
    )
    itad_variance_reason = fields.Text(
        string="Variance Reason",
        copy=False,
        help="Description of the variance detected",
    )
    itad_variance_review_state = fields.Selection(
        [
            ("none", "None"),
            ("pending", "Pending Review"),
            ("resolved", "Resolved"),
        ],
        string="Variance Review State",
        default="none",
        index=True,
        copy=False,
    )
    itad_variance_reviewed_by = fields.Many2one(
        "res.users",
        string="Reviewed By",
        readonly=True,
        copy=False,
    )
    itad_variance_reviewed_at = fields.Datetime(
        string="Reviewed At",
        readonly=True,
        copy=False,
    )
    itad_variance_review_note = fields.Text(
        string="Review Notes",
        copy=False,
    )

    @api.depends("location_id.partner_id.name", "location_id.name")
    def _compute_customer_name(self):
        for rec in self:
            location = rec.location_id
            if location:
                rec.customer_name = (
                    (location.partner_id.name if location.partner_id else "")
                    or location.name
                    or ""
                )
            else:
                rec.customer_name = ""

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
                submit_state = self.env["itad.core.outbox"]._map_outbox_state_to_submit_state(
                    outbox.state
                )
                order.write(
                    {
                        "itad_outbox_id": outbox.id,
                        "itad_outbox_last_id": outbox.id,
                        "itad_submit_state": submit_state,
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
            order.sudo().with_context(
                itad_telemetry_write=True,
                mail_notrack=True,
                tracking_disable=True,
            ).write(
                {
                    "itad_outbox_id": outbox.id,
                    "itad_outbox_last_id": outbox.id,
                    "itad_submit_state": "pending",
                    "itad_last_error": False,
                    "itad_last_submit_at": fields.Datetime.now(),
                }
            )
        return True

    def _has_operational_scheduling_vals(self, vals):
        return any(field in vals for field in self.TELEMETRY_PROTECTED_FIELDS)

    def write(self, vals):
        if self.env.context.get("itad_telemetry_write"):
            safe_vals = dict(vals)
            for field in self.TELEMETRY_PROTECTED_FIELDS:
                safe_vals.pop(field, None)
            return super().write(safe_vals)
        return super().write(vals)

    def action_open_receiving_wizard(self):
        """Open receiving confirmation wizard for this order."""
        self.ensure_one()
        if not self.itad_pickup_manifest_id:
            raise UserError(_("No pickup manifest found for this order."))
        if not self.itad_bol_id:
            raise UserError(_("No BOL ID found. Manifest must be bound to BOL first."))
        
        return {
            "type": "ir.actions.act_window",
            "name": "Confirm Receipt",
            "res_model": "itad.receiving.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_fsm_order_id": self.id,
                "default_pickup_manifest_id": self.itad_pickup_manifest_id,
                "default_manifest_no": self.itad_manifest_no,
                "default_bol_id": self.itad_bol_id,
            },
        }
    
    # Phase 2.5: Variance Resolution
    def action_resolve_variance(self):
        """Mark variance as resolved (manager action)."""
        for rec in self:
            if rec.itad_variance_review_state != "pending":
                continue
            rec.write({
                "itad_variance_review_state": "resolved",
                "itad_variance_reviewed_by": self.env.user.id,
                "itad_variance_reviewed_at": fields.Datetime.now(),
            })
        return True
    
    @api.model
    def _get_variance_thresholds(self):
        """Get variance detection thresholds from config."""
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "percent_threshold": float(icp.get_param("itad_core.variance.percent_threshold", "25")),
            "absolute_lbs_threshold": float(icp.get_param("itad_core.variance.absolute_lbs_threshold", "500")),
            "max_weight_lbs": float(icp.get_param("itad_core.max_receipt_weight_lbs", "50000")),
        }
    
    def _evaluate_variance_for_order(self):
        """
        Evaluate variance for a single order.
        Returns (flag, reason) tuple.
        """
        self.ensure_one()
        thresholds = self._get_variance_thresholds()
        
        # Skip if no receipt weight
        if not self.itad_receipt_weight_lbs:
            return False, ""
        
        weight = self.itad_receipt_weight_lbs
        reasons = []
        
        # Rule 1: Weight exceeds max threshold
        if weight > thresholds["max_weight_lbs"]:
            reasons.append(
                f"Receipt weight {weight:.1f} lbs exceeds max {thresholds['max_weight_lbs']:.0f} lbs"
            )
        
        # Rule 2: Expected weight comparison (if available via related field)
        # Note: expected_weight would need to be added if not present
        expected = getattr(self, "expected_weight_lbs", None)
        if expected and expected > 0:
            delta = abs(weight - expected)
            delta_pct = (delta / expected) * 100
            
            if delta > thresholds["absolute_lbs_threshold"]:
                reasons.append(
                    f"Weight delta {delta:.1f} lbs exceeds threshold {thresholds['absolute_lbs_threshold']:.0f} lbs"
                )
            elif delta_pct > thresholds["percent_threshold"]:
                reasons.append(
                    f"Weight delta {delta_pct:.1f}% exceeds threshold {thresholds['percent_threshold']:.0f}%"
                )
        
        if reasons:
            return True, "; ".join(reasons)
        return False, ""
    
    @api.model
    def _cron_evaluate_variance(self):
        """
        Cron job: Evaluate variance for recently received orders.
        
        Only evaluates orders that:
        - Have received state
        - Haven't been evaluated yet (variance_review_state = 'none')
        - Were confirmed in last 7 days
        """
        from datetime import timedelta
        
        now = fields.Datetime.now()
        cutoff = now - timedelta(days=7)
        
        orders = self.search([
            ("itad_receipt_state", "=", "received"),
            ("itad_variance_review_state", "=", "none"),
            ("itad_receipt_confirmed_at", ">=", cutoff),
        ], limit=500)  # Batch limit
        
        flagged_count = 0
        for order in orders:
            flag, reason = order._evaluate_variance_for_order()
            if flag:
                order.write({
                    "itad_variance_flag": True,
                    "itad_variance_reason": reason,
                    "itad_variance_review_state": "pending",
                })
                flagged_count += 1
            else:
                # Mark as evaluated (no variance)
                order.write({
                    "itad_variance_flag": False,
                    "itad_variance_reason": "",
                })
        
        if flagged_count:
            import logging
            logging.getLogger(__name__).info(
                "Variance evaluation: flagged %d of %d orders", flagged_count, len(orders)
            )
        return True
    
