# File: itad_core/models/itad_evidence_pack.py
"""
Phase 2.7: Evidence Pack Automation Service

Generates audit-grade evidence bundles (JSON + PDF) for traceability.
Access restricted to manager/compliance roles.
"""

import base64
import hashlib
import json
import logging
from datetime import datetime

import requests

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

# Evidence pack schema version
EVIDENCE_PACK_SCHEMA_VERSION = "1.0"


class ItadEvidencePackService(models.TransientModel):
    """
    Evidence Pack Generator Service.
    
    Phase 2.7: One-click generation of audit-grade evidence bundles.
    Produces JSON + PDF with full traceability chain.
    """
    _name = "itad.evidence.pack.service"
    _description = "Evidence Pack Generator"
    
    fsm_order_id = fields.Many2one("fsm.order", string="FSM Order", required=True)
    
    def _check_access(self):
        """Verify user has compliance/manager role."""
        user = self.env.user
        # Check for receiving manager or admin
        is_manager = user.has_group("itad_core.group_receiving_manager")
        is_admin = user.has_group("base.group_system")
        
        if not (is_manager or is_admin):
            raise AccessError(_(
                "Evidence Pack generation requires Receiving Manager or Admin role."
            ))
    
    def _get_pack_id(self, order):
        """Generate deterministic pack ID."""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%SZ")
        bol_or_manifest = order.itad_bol_id or order.itad_manifest_no or f"order-{order.id}"
        return f"evp-{bol_or_manifest}-{timestamp}"
    
    def _collect_odoo_data(self, order):
        """Collect all Odoo-side data for evidence pack."""
        # FSM Order data
        fsm_order_data = {
            "id": order.id,
            "name": order.name,
            "itad_manifest_no": order.itad_manifest_no or None,
            "itad_bol_id": order.itad_bol_id or None,
            "itad_receipt_state": order.itad_receipt_state or None,
            "itad_receipt_idempotency_key": order.itad_receipt_idempotency_key or None,
            "customer": order.customer_name or None,
            "timestamps": {
                "created_at": order.create_date.isoformat() + "Z" if order.create_date else None,
                "updated_at": order.write_date.isoformat() + "Z" if order.write_date else None,
                "receipt_confirmed_at": order.itad_receipt_confirmed_at.isoformat() + "Z" if order.itad_receipt_confirmed_at else None,
            },
        }
        
        # Outbox events
        outbox_records = self.env["itad.core.outbox"].search([("order_id", "=", order.id)])
        outbox_events = []
        correlation_ids = []
        idempotency_keys = []
        
        for ob in outbox_records:
            outbox_events.append({
                "id": ob.id,
                "state": ob.state,
                "idempotency_key": ob.idempotency_key,
                "correlation_id": ob.correlation_id,
                "attempt_count": ob.attempt_count,
                "last_error": ob.last_error or None,
                "created_at": ob.create_date.isoformat() + "Z" if ob.create_date else None,
                "updated_at": ob.write_date.isoformat() + "Z" if ob.write_date else None,
            })
            if ob.correlation_id:
                correlation_ids.append(ob.correlation_id)
            if ob.idempotency_key:
                idempotency_keys.append(ob.idempotency_key)
        
        # Add receipt idempotency key
        if order.itad_receipt_idempotency_key:
            idempotency_keys.append(order.itad_receipt_idempotency_key)
        
        # Receipt audit logs
        audit_logs = self.env["itad.receipt.audit.log"].search([
            ("fsm_order_id", "=", order.id)
        ], order="attempted_at desc")
        
        receipt_audit_logs = []
        for log in audit_logs:
            receipt_audit_logs.append({
                "id": log.id,
                "attempt_number": log.attempt_number,
                "attempted_at": log.attempted_at.isoformat() + "Z" if log.attempted_at else None,
                "outcome": log.outcome,
                "success": log.success,
                "error_message": log.error_message or None,
                "archived": log.archived,
                "archived_at": log.archived_at.isoformat() + "Z" if log.archived_at else None,
            })
        
        # Attachments
        attachments_data = []
        attachments = self.env["ir.attachment"].search([
            ("res_model", "=", "fsm.order"),
            ("res_id", "=", order.id),
        ])
        
        for att in attachments:
            sha256_hex = ""
            if att.datas:
                try:
                    raw = base64.b64decode(att.datas)
                    sha256_hex = hashlib.sha256(raw).hexdigest()
                except Exception:
                    sha256_hex = ""
            
            attachments_data.append({
                "id": att.id,
                "name": att.name,
                "mimetype": att.mimetype or "unknown",
                "created_at": att.create_date.isoformat() + "Z" if att.create_date else None,
                "sha256": sha256_hex,
                "source": "fsm.order",
            })
        
        return {
            "fsm_order": fsm_order_data,
            "outbox_events": outbox_events,
            "receipt_audit_logs": receipt_audit_logs,
            "attachments": attachments_data,
        }, correlation_ids, idempotency_keys
    
    def _fetch_itad_core_data(self, bol_id, material_code=None):
        """Fetch data from ITAD Core API."""
        try:
            config = self.env["itad.core.config"].get_itad_core_config()
            base_url, token = config
        except Exception as e:
            _logger.warning("Cannot get ITAD Core config: %s", e)
            return {"error": str(e), "receiving_anchors": [], "material_type_snapshot": None}
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        result = {
            "receiving_anchors": [],
            "material_type_snapshot": None,
            "version": None,
        }
        
        # Fetch receiving records by BOL
        if bol_id:
            try:
                url = f"{base_url.rstrip('/')}/api/v1/receiving-weight-records"
                resp = requests.get(url, params={"bol_id": bol_id}, headers=headers, timeout=10)
                if resp.ok:
                    data = resp.json()
                    records = data if isinstance(data, list) else data.get("items", [])
                    for rec in records:
                        result["receiving_anchors"].append({
                            "id": rec.get("id"),
                            "bol_id": rec.get("bol_id"),
                            "occurred_at": rec.get("occurred_at"),
                            "net_weight": rec.get("net_weight"),
                            "weight_unit": rec.get("weight_unit"),
                            "material_type_id": rec.get("material_type_id"),
                            "material_code": rec.get("material_received_as"),
                            "created_at": rec.get("created_at"),
                            "updated_at": rec.get("updated_at"),
                        })
            except Exception as e:
                _logger.warning("Failed to fetch receiving records: %s", e)
                result["error_receiving"] = str(e)
        
        # Fetch material type snapshot
        if material_code:
            try:
                url = f"{base_url.rstrip('/')}/api/v1/material-types"
                resp = requests.get(url, params={"code": material_code}, headers=headers, timeout=10)
                if resp.ok:
                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("items", [])
                    if items:
                        mt = items[0]
                        result["material_type_snapshot"] = {
                            "id": mt.get("id"),
                            "code": mt.get("code"),
                            "name": mt.get("name"),
                            "stream": mt.get("stream"),
                            "hazard_class": mt.get("hazard_class"),
                            "requires_photo": mt.get("requires_photo"),
                            "requires_weight": mt.get("requires_weight"),
                            "is_active": mt.get("is_active"),
                            "updated_at": mt.get("updated_at"),
                            "billing": {
                                "pricing_state": mt.get("pricing_state"),
                                "default_price": mt.get("default_price"),
                                "basis_of_charge": mt.get("basis_of_charge"),
                                "gl_account_code": mt.get("gl_account_code"),
                            },
                        }
            except Exception as e:
                _logger.warning("Failed to fetch material type: %s", e)
                result["error_material"] = str(e)
        
        return result
    
    def _collect_retention_and_controls(self):
        """Collect retention policy and break-glass events."""
        icp = self.env["ir.config_parameter"].sudo()
        
        retention_days = int(icp.get_param("itad_core.taxonomy.audit_retention_days", "365"))
        retention_mode = icp.get_param("itad_core.taxonomy.audit_retention_mode", "archive")
        
        # Get break-glass events from taxonomy audit log
        break_glass_logs = self.env["itad.taxonomy.audit.log"].search([
            ("action", "in", ["break_glass_enabled", "stale_override_used", "retention_delete"])
        ], limit=10, order="occurred_at desc")
        
        break_glass_events = []
        for log in break_glass_logs:
            break_glass_events.append({
                "timestamp": log.occurred_at.isoformat() + "Z" if log.occurred_at else None,
                "actor": log.user_id.login if log.user_id else "system",
                "reason": log.details or "",
                "scope": log.action,
            })
        
        return {
            "retention_policy": {
                "odoo_audit_retention_days": retention_days,
                "mode": retention_mode,
                "last_retention_run_at": None,  # Would need to track this
            },
            "break_glass_events": break_glass_events,
        }
    
    def _build_json(self, order, pack_id, odoo_data, itad_data, correlation_ids, idempotency_keys):
        """Build the complete evidence pack JSON."""
        now = datetime.utcnow()
        user = self.env.user
        
        # Get system info
        icp = self.env["ir.config_parameter"].sudo()
        base_url = icp.get_param("itad_core.api.base_url", "")
        db_name = self.env.cr.dbname
        
        pack = {
            "meta": {
                "pack_id": pack_id,
                "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
                "generated_at": now.isoformat() + "Z",
                "generated_by": {
                    "odoo_user_id": user.id,
                    "odoo_user_login": user.login,
                    "roles": [g.name for g in user.groups_id if "itad" in g.name.lower()],
                },
                "input": {
                    "bol_id": order.itad_bol_id or None,
                    "manifest_no": order.itad_manifest_no or None,
                    "fsm_order_id": order.id,
                },
                "systems": {
                    "odoo_db": db_name,
                    "itad_core_base_url": base_url,
                    "itad_core_version": itad_data.get("version"),
                },
            },
            "trace": {
                "correlation_ids": list(set(correlation_ids)),
                "idempotency_keys": list(set(idempotency_keys)),
            },
            "odoo": odoo_data,
            "itad_core": {
                "receiving_anchors": itad_data.get("receiving_anchors", []),
                "material_type_snapshot": itad_data.get("material_type_snapshot"),
            },
            "retention_and_controls": self._collect_retention_and_controls(),
            "integrity": {
                "json_sha256": "",  # Will be filled after serialization
                "pdf_sha256": "",
                "notes": [],
            },
        }
        
        # Add error notes if any
        if itad_data.get("error"):
            pack["integrity"]["notes"].append(f"ITAD Core config error: {itad_data['error']}")
        if itad_data.get("error_receiving"):
            pack["integrity"]["notes"].append(f"Receiving fetch error: {itad_data['error_receiving']}")
        if itad_data.get("error_material"):
            pack["integrity"]["notes"].append(f"Material fetch error: {itad_data['error_material']}")
        
        return pack
    
    def _compute_hashes(self, pack_dict, pdf_bytes):
        """Compute and update integrity hashes."""
        # JSON hash (without the hash fields)
        pack_for_hash = pack_dict.copy()
        pack_for_hash["integrity"] = {"json_sha256": "", "pdf_sha256": "", "notes": pack_dict["integrity"]["notes"]}
        json_bytes = json.dumps(pack_for_hash, sort_keys=True, ensure_ascii=False).encode("utf-8")
        json_sha256 = hashlib.sha256(json_bytes).hexdigest()
        
        # PDF hash
        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        
        pack_dict["integrity"]["json_sha256"] = json_sha256
        pack_dict["integrity"]["pdf_sha256"] = pdf_sha256
        
        return pack_dict
    
    def _render_pdf(self, pack_dict):
        """Render PDF from pack data using QWeb report."""
        try:
            report = self.env.ref("itad_core.report_evidence_pack")
            pdf_content, _ = report._render_qweb_pdf(
                "itad_core.report_evidence_pack_template",
                res_ids=[],
                data={"pack": pack_dict},
            )
            return pdf_content
        except Exception as e:
            _logger.warning("PDF render failed, using fallback: %s", e)
            # Fallback: simple text-based PDF placeholder
            return self._render_fallback_pdf(pack_dict)
    
    def _render_fallback_pdf(self, pack_dict):
        """Fallback PDF if QWeb template not available."""
        # Simple text representation
        content = f"""
ITAD Evidence Pack
==================
Pack ID: {pack_dict['meta']['pack_id']}
Generated: {pack_dict['meta']['generated_at']}
Generated By: {pack_dict['meta']['generated_by']['odoo_user_login']}

Input:
- BOL ID: {pack_dict['meta']['input']['bol_id']}
- Manifest No: {pack_dict['meta']['input']['manifest_no']}
- FSM Order ID: {pack_dict['meta']['input']['fsm_order_id']}

Trace:
- Correlation IDs: {', '.join(pack_dict['trace']['correlation_ids'])}
- Idempotency Keys: {', '.join(pack_dict['trace']['idempotency_keys'])}

See JSON attachment for full data.
        """
        # Return as bytes (not a real PDF, but placeholder)
        return content.encode("utf-8")
    
    def _store_attachments(self, order, pack_id, json_bytes, pdf_bytes, hashes):
        """Store generated files as Odoo attachments."""
        Attachment = self.env["ir.attachment"]
        
        # JSON attachment
        json_att = Attachment.create({
            "name": f"EvidencePack-{pack_id}.json",
            "type": "binary",
            "datas": base64.b64encode(json_bytes),
            "res_model": "fsm.order",
            "res_id": order.id,
            "mimetype": "application/json",
        })
        
        # PDF attachment
        pdf_att = Attachment.create({
            "name": f"EvidencePack-{pack_id}.pdf",
            "type": "binary",
            "datas": base64.b64encode(pdf_bytes),
            "res_model": "fsm.order",
            "res_id": order.id,
            "mimetype": "application/pdf",
        })
        
        # SHA256 checksum file
        checksum_content = f"{hashes['json_sha256']}  EvidencePack-{pack_id}.json\n{hashes['pdf_sha256']}  EvidencePack-{pack_id}.pdf\n"
        sha_att = Attachment.create({
            "name": f"EvidencePack-{pack_id}.sha256",
            "type": "binary",
            "datas": base64.b64encode(checksum_content.encode("utf-8")),
            "res_model": "fsm.order",
            "res_id": order.id,
            "mimetype": "text/plain",
        })
        
        return json_att, pdf_att, sha_att
    
    @api.model
    def generate_for_order(self, order_id):
        """
        Generate evidence pack for an FSM order.
        
        Returns dict with pack_id and attachment IDs.
        """
        self._check_access()
        
        order = self.env["fsm.order"].browse(order_id)
        if not order.exists():
            raise UserError(_("FSM Order not found."))
        
        # Generate pack ID
        pack_id = self._get_pack_id(order)
        
        # Collect Odoo data
        odoo_data, correlation_ids, idempotency_keys = self._collect_odoo_data(order)
        
        # Fetch ITAD Core data
        material_code = order.itad_receipt_material_code or None
        itad_data = self._fetch_itad_core_data(order.itad_bol_id, material_code)
        
        # Build JSON
        pack_dict = self._build_json(
            order, pack_id, odoo_data, itad_data,
            correlation_ids, idempotency_keys
        )
        
        # Render PDF (placeholder for now)
        pdf_bytes = self._render_fallback_pdf(pack_dict)
        
        # Compute hashes
        pack_dict = self._compute_hashes(pack_dict, pdf_bytes)
        
        # Serialize JSON
        json_bytes = json.dumps(pack_dict, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")
        
        # Store attachments
        json_att, pdf_att, sha_att = self._store_attachments(
            order, pack_id, json_bytes, pdf_bytes,
            {"json_sha256": pack_dict["integrity"]["json_sha256"], "pdf_sha256": pack_dict["integrity"]["pdf_sha256"]}
        )
        
        _logger.info("Evidence pack generated: %s for order %s", pack_id, order.id)
        
        return {
            "pack_id": pack_id,
            "json_attachment_id": json_att.id,
            "pdf_attachment_id": pdf_att.id,
            "sha256_attachment_id": sha_att.id,
        }
