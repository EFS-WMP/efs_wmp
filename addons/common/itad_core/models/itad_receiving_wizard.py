# File: itad_core/models/itad_receiving_wizard.py

import json
import logging
import uuid

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)


class ItadReceivingWizard(models.TransientModel):
    _name = "itad.receiving.wizard"
    _description = "Confirm Manifest Receipt"

    # Context from FSM order
    fsm_order_id = fields.Many2one("fsm.order", string="FSM Order", required=True, readonly=True)
    pickup_manifest_id = fields.Char(string="Pickup Manifest ID", required=True, readonly=True)
    manifest_no = fields.Char(string="Manifest No", readonly=True)
    bol_id = fields.Char(string="BOL ID", required=True, readonly=True)

    # Display fields (read-only)
    customer_name = fields.Char(
        compute="_compute_customer_name",
        store=True,
        string="Customer",
        readonly=True,
    )
    location_name = fields.Char(related="fsm_order_id.location_id.name", string="Location", readonly=True)
    completed_date = fields.Datetime(related="fsm_order_id.date_end", string="Completed Date", readonly=True)

    # User inputs (Phase 2.3 - synced taxonomy from ITAD Core)
    material_type_id = fields.Many2one(
        "itad.material.type.cache",
        string="Material Type",
        required=True,
        domain=[("active", "=", True)],
        help="Select the primary material type received from synced ITAD Core taxonomy.",
    )
    material_type_code = fields.Char(
        string="Material Type Code",
        help="Compatibility field to map material type by code when material_type_id is not provided.",
    )

    actual_weight_lbs = fields.Float(
        string="Actual Weight (lbs)",
        required=True,
        digits=(12, 2),
        help="Total gross weight received in pounds.",
    )

    operator_notes = fields.Text(
        string="Notes",
        help="Optional notes about the receipt (e.g., condition, discrepancies).",
    )

    receipt_timestamp = fields.Datetime(
        string="Receipt Time",
        default=lambda self: fields.Datetime.now(),
        required=True,
    )

    # Phase 2.2: Hardening fields for retry and audit
    error_state = fields.Boolean(
        string="Error State",
        default=False,
        help="True if last attempt failed",
    )
    
    last_error_message = fields.Text(
        string="Last Error Message",
        readonly=True,
    )
    
    original_idempotency_key = fields.Char(
        string="Original Idempotency Key",
        readonly=True,
        help="Stable key across retries - never regenerated",
    )
    
    attempt_count = fields.Integer(
        string="Attempt Count",
        default=0,
        readonly=True,
    )
    
    last_attempt_at = fields.Datetime(
        string="Last Attempt At",
        readonly=True,
    )
    
    successful_at = fields.Datetime(
        string="Successful At",
        readonly=True,
    )
    
    api_response_id = fields.Char(
        string="API Response ID",
        readonly=True,
        help="ITAD Core receiving_weight_record_id",
    )

    @api.depends("fsm_order_id.location_id.partner_id.name", "fsm_order_id.location_id.name")
    def _compute_customer_name(self):
        for rec in self:
            location = rec.fsm_order_id.location_id if rec.fsm_order_id else False
            if location:
                rec.customer_name = (
                    (location.partner_id.name if location.partner_id else "")
                    or location.name
                    or ""
                )
            else:
                rec.customer_name = ""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("material_type_id") and vals.get("material_type_code"):
                code = vals.get("material_type_code")
                material = self.env["itad.material.type.cache"].search(
                    [("code", "=", code)],
                    limit=1,
                )
                if material:
                    vals["material_type_id"] = material.id
                else:
                    raise UserError(
                        _("Material type code '%(code)s' not found. Sync taxonomy and retry.")
                        % {"code": code}
                    )
        return super().create(vals_list)

    def _get_config(self):
        """Get ITAD Core API configuration (reuse Phase 1 pattern)."""
        return self.env["itad.core.config"].get_itad_core_config()

    def _now(self):
        """Deterministic time wrapper for testing"""
        return fields.Datetime.now()

    def _write_wizard_state(self, values):
        """Persist wizard state via SQL (TransientModel writes don't persist)."""
        self.ensure_one()
        if not values:
            return
        cleaned = {}
        for field_name, value in values.items():
            field = self._fields.get(field_name)
            if value is False and field and field.type in ("char", "text", "date", "datetime", "selection"):
                cleaned[field_name] = None
            else:
                cleaned[field_name] = value
        set_clause = ", ".join(f"{field} = %s" for field in cleaned.keys())
        params = list(cleaned.values()) + [self.id]
        self.env.cr.execute(
            f"""
            UPDATE {self._table}
               SET {set_clause}
             WHERE id = %s
            """,
            params,
        )
        self._invalidate_cache(fnames=list(cleaned.keys()), ids=[self.id])

    def _ensure_idempotency_key(self):
        """Ensure a stable idempotency key is stored for this wizard."""
        self.ensure_one()
        if not self.original_idempotency_key:
            self._write_wizard_state({
                "original_idempotency_key": f"receipt-{uuid.uuid4().hex}",
            })
        return self.original_idempotency_key

    def _get_receiving_defaults(self):
        """
        Get configurable receiving defaults from system parameters.
        
        Phase 2.2: Replaces hardcoded defaults with ir.config_parameter values.
        Falls back to sensible defaults if parameters not set.
        """
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "container_type": icp.get_param("itad_core.default_container_type", "PALLET"),
            "scale_id": icp.get_param("itad_core.default_scale_id", "DOCK-SCALE-01"),
            "timeout": int(icp.get_param("itad_core.receipt_timeout_seconds", "30")),
            "max_weight": int(icp.get_param("itad_core.max_receipt_weight_lbs", "100000")),
            "bol_pattern": icp.get_param("itad_core.bol_pattern", r"^BOL-\d{4}-\d{6}$"),
            "max_attempts_per_hour": int(icp.get_param("itad_core.max_receipt_attempts_per_hour", "10")),
        }

    def _check_itad_core_compatibility(self):
        """
        Check ITAD Core API health and version compatibility.
        
        Phase 2.2a: Verifies API is reachable and version >= 1.0.0
        Raises UserError if incompatible, logs audit entry.
        """
        self.ensure_one()
        
        base_url, token = self._get_config()
        defaults = self._get_receiving_defaults()
        timeout = defaults["timeout"]
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            # Try /health first
            health_resp = requests.get(
                base_url.rstrip("/") + "/health",
                headers=headers,
                timeout=timeout
            )
            
            if health_resp.status_code == 200:
                return  # Health check passed
            
            # Health failed, try /openapi.json
            openapi_resp = requests.get(
                base_url.rstrip("/") + "/openapi.json",
                headers=headers,
                timeout=timeout
            )
            
            if openapi_resp.status_code == 200:
                openapi_data = openapi_resp.json()
                version_str = openapi_data.get("info", {}).get("version", "0.0.0")
                
                # Parse version (simple semver check)
                try:
                    major = int(version_str.split(".")[0])
                    if major < 1:
                        # Version too old
                        self._log_receipt_attempt(
                            success=False,
                            outcome="API_VERSION_UNSUPPORTED",
                            error_message=_(
                                "ITAD Core API version %(version)s is not supported. Minimum version: 1.0.0"
                            )
                            % {"version": version_str},
                        )
                        raise UserError(
                            _("ITAD Core API version %(version)s is not supported. Minimum version: 1.0.0")
                            % {"version": version_str}
                        )
                except (ValueError, IndexError):
                    pass  # Could not parse version, allow
                
                return  # OpenAPI check passed
            
            # Both endpoints failed
            self._log_receipt_attempt(
                success=False,
                outcome="API_UNREACHABLE",
                error_message=_("ITAD Core API is unreachable. Please check the connection and try again."),
            )
            raise UserError(_("ITAD Core API is unreachable. Please check the connection and try again."))
            
        except requests.exceptions.RequestException:
            # Network error
            self._log_receipt_attempt(
                success=False,
                outcome="API_UNREACHABLE",
                error_message=_("ITAD Core API is unreachable. Please check the connection and try again."),
            )
            raise UserError(_("ITAD Core API is unreachable. Please check the connection and try again."))

    def _check_rate_limit(self):
        """
        Check if rate limit has been exceeded.
        
        Phase 2.2a: Enforces max attempts per hour per (user, order).
        Raises UserError if limit exceeded, logs audit entry.
        """
        self.ensure_one()
        
        defaults = self._get_receiving_defaults()
        max_attempts = defaults["max_attempts_per_hour"]
        
        # Calculate time window (last hour)
        now = self._now()
        from datetime import timedelta
        one_hour_ago = now - timedelta(hours=1)
        
        # Count recent attempts for this user + order
        recent_attempts = self.env["itad.receipt.audit.log"].sudo().search_count([
            ("user_id", "=", self.env.user.id),
            ("order_id", "=", self.fsm_order_id.id),
            ("attempted_at", ">=", one_hour_ago),
        ])
        
        if recent_attempts >= max_attempts:
            # Rate limit exceeded
            self._log_receipt_attempt(success=False, outcome="RATE_LIMIT_BLOCK")
            raise UserError(
                _("Rate limit exceeded. Maximum %(max)s attempts per hour allowed. Please try again later.")
                % {"max": max_attempts}
            )

    def _build_receiving_payload(self):
        """
        Build payload for ITAD Core POST /api/v1/receiving-weight-records.
        
        Phase 2.2: Uses configurable defaults from system parameters.
        """
        self.ensure_one()

        defaults = self._get_receiving_defaults()

        # Convert Odoo datetime to ISO format (deterministic)
        occurred_at = self.receipt_timestamp.isoformat() if self.receipt_timestamp else fields.Datetime.now().isoformat()

        # Phase 2.3: Send itad_core_uuid as material identifier
        material_received_as = self.material_type_id.itad_core_uuid if self.material_type_id else None
        
        payload = {
            "bol_id": self.bol_id,
            "occurred_at": occurred_at,
            "material_received_as": material_received_as,
            # Phase 2.2: Configurable defaults
            "container_type": defaults["container_type"],
            "quantity": 1,
            "gross_weight": float(self.actual_weight_lbs),
            "tare_weight": 0.0,  # Simplified for MVP
            "net_weight": float(self.actual_weight_lbs),
            "weight_unit": "LBS",
            "scale_id": defaults["scale_id"],
            "ddr_status": False,  # Dot Regulated Dangerous goods
            "receiver_employee_id": str(self.env.user.id),
            "receiver_name": self.env.user.name,
            "receiver_signature_json": {
                "type": "odoo_user",
                "user_id": self.env.user.id,
                "timestamp": fields.Datetime.now().isoformat(),
            },
            "tare_source": "NONE",  # Simplified for MVP
            "notes": self.operator_notes or "",
        }

        return payload

    def _call_itad_receiving_endpoint(self):
        """
        Call ITAD Core API to create receiving_weight_record.
        
        Phase 2.2: Uses original_idempotency_key for retry support.
        """
        self.ensure_one()

        base_url, token = self._get_config()
        url = base_url.rstrip("/") + "/api/v1/receiving-weight-records"

        defaults = self._get_receiving_defaults()

        # Generate or reuse idempotency key
        idempotency_key = self._ensure_idempotency_key()
        correlation_id = f"corr-receipt-{uuid.uuid4().hex}"

        headers = {
            "Idempotency-Key": idempotency_key,
            "X-Correlation-Id": correlation_id,
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = self._build_receiving_payload()

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=defaults["timeout"])

            if 200 <= resp.status_code < 300:
                return resp.json(), idempotency_key, correlation_id

            # API validation error (422) or other error
            error_detail = resp.text
            try:
                error_json = resp.json()
                error_detail = error_json.get("detail", resp.text)
            except Exception:
                pass

            raise UserError(
                _("ITAD Core API error (%(status)s): %(detail)s")
                % {"status": resp.status_code, "detail": error_detail}
            )

        except requests.exceptions.RequestException as exc:
            raise UserError(
                _("Network error calling ITAD Core: %(error)s") % {"error": str(exc)}
            )

    def _validate_bol_format(self):
        """
        Validate BOL ID format.
        
        Phase 2.2: BOL must match pattern BOL-YYYY-NNNNNN
        """
        self.ensure_one()
        import re
        
        BOL_PATTERN = r"^BOL-\d{4}-\d{6}$"
        
        if not re.match(BOL_PATTERN, self.bol_id or ""):
            raise ValidationError(
                _("Invalid BOL format: '%(bol)s'. Expected format: BOL-YYYY-NNNNNN (e.g., BOL-2026-000123)")
                % {"bol": self.bol_id}
            )

    def _validate_weight(self):
        """
        Validate weight is within acceptable range.
        
        Phase 2.2: Weight must be > 0 and <= max_receipt_weight_lbs
        """
        self.ensure_one()
        
        if self.actual_weight_lbs <= 0:
            raise ValidationError(_("Actual weight must be greater than zero."))
        
        defaults = self._get_receiving_defaults()
        max_weight = defaults["max_weight"]
        
        if self.actual_weight_lbs > max_weight:
            raise ValidationError(
                _("Weight %(weight)s lbs exceeds maximum allowed weight of %(max)s lbs.")
                % {"weight": self.actual_weight_lbs, "max": max_weight}
            )

    def _handle_api_error(self, error_message):
        """
        Handle API error by setting error state.
        
        Phase 2.2: Does NOT regenerate idempotency key.
        """
        self.ensure_one()
        
        self._write_wizard_state({
            "error_state": True,
            "last_error_message": error_message,
        })

    def _log_receipt_attempt(self, success, response_data=None, outcome=None, error_message=None):
        """
        Create audit log record for this attempt.
        
        Phase 2.2a: Logs all attempts with outcome.
        """
        self.ensure_one()
        
        now = self._now()
        next_attempt = self.attempt_count + 1
        
        # Determine outcome if not provided
        if outcome is None:
            outcome = "SUCCESS" if success else "SERVER_ERROR"
        
        # Update wizard timestamps
        vals = {
            "last_attempt_at": now,
            "attempt_count": next_attempt,
        }
        
        if success:
            vals.update({
                "successful_at": now,
                "error_state": False,
                "last_error_message": False,
                "api_response_id": response_data.get("id") if response_data else None,
            })
        else:
            vals["error_state"] = True
            if error_message:
                vals["last_error_message"] = error_message
        
        self._write_wizard_state(vals)
        
        # Create audit log via SQL to ensure immediate visibility for tests
        self.env.cr.execute(
            """
            SELECT fsm_order_id, manifest_no, bol_id
              FROM itad_receiving_wizard
             WHERE id = %s
            """,
            [self.id],
        )
        row = self.env.cr.fetchone() or (None, None, None)
        order_id, manifest_no_db, bol_id_db = row
        manifest_no = manifest_no_db or self.manifest_no
        bol_id = bol_id_db or self.bol_id
        error_detail = error_message or self.last_error_message
        response_id = response_data.get("id") if success and response_data else None
        insert_sql = """
            INSERT INTO itad_receipt_audit_log (
                wizard_id,
                order_id,
                user_id,
                manifest_no,
                bol_id,
                success,
                outcome,
                attempt_number,
                error_message,
                response_id,
                attempted_at,
                idempotency_key
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        insert_params = [
            self.id,
            order_id,
            self.env.user.id,
            manifest_no or None,
            bol_id or None,
            success,
            outcome,
            next_attempt,
            None if success else (error_detail or None),
            response_id,
            now,
            self.original_idempotency_key or None,
        ]
        self.env.cr.execute(insert_sql, insert_params)

    def action_retry_receipt(self):
        """
        Retry failed receipt confirmation.
        
        Phase 2.2: Reuses original_idempotency_key, does not regenerate.
        """
        self.ensure_one()

        # Call same confirm logic
        return self.action_confirm_receipt()

    def _check_taxonomy_cache_health(self):
        """
        Check taxonomy cache health (Phase 2.3 degraded mode).
        
        Raises UserError if:
        - Cache has 0 active records (not synced)
        - Sync is stale (> max_stale_hours) AND block_if_stale=true
        """
        self.ensure_one()
        
        # Check if cache has any active records
        active_count = self.env["itad.material.type.cache"].search_count([("active", "=", True)])
        
        if active_count == 0:
            # Log audit
            self._log_receipt_attempt(
                success=False,
                outcome="TAXONOMY_NOT_SYNCED",
                error_message="Material taxonomy not synced. Cache is empty.",
            )
            raise UserError(
                _("Material taxonomy not synced. Please run 'Sync Now' from ITAD Core > Material Types before submitting receipts.")
            )
        
        # Check if sync is stale
        icp = self.env["ir.config_parameter"].sudo()
        max_stale_hours = int(icp.get_param("itad_core.taxonomy.sync.max_stale_hours", "24"))
        block_if_stale = icp.get_param("itad_core.taxonomy.sync.block_if_stale", "true").lower() == "true"
        break_glass_enabled = icp.get_param("itad_core.taxonomy.sync.break_glass_enabled", "false").lower() == "true"
        
        if block_if_stale and not break_glass_enabled:
            sync_state = self.env["itad.taxonomy.sync.state"].get_singleton()
            
            if not sync_state.last_success_at:
                # Never synced
                self._log_receipt_attempt(
                    success=False,
                    outcome="TAXONOMY_STALE",
                    error_message="Taxonomy has never been synced.",
                )
                raise UserError(
                    _("Material taxonomy has never been synced. Please run 'Sync Now' before submitting receipts.")
                )
            
            from datetime import timedelta
            now = self._now()
            stale_threshold = now - timedelta(hours=max_stale_hours)
            
            if sync_state.last_success_at < stale_threshold:
                # Stale sync
                self._log_receipt_attempt(
                    success=False,
                    outcome="TAXONOMY_STALE",
                    error_message=f"Taxonomy sync is stale (last synced: {sync_state.last_success_at}).",
                )
                raise UserError(
                    _("Material taxonomy is stale (last synced: %(last_sync)s). Please run 'Sync Now' before submitting receipts.")
                    % {"last_sync": sync_state.last_success_at}
                )
        elif break_glass_enabled:
            # SECURITY: Break-glass enabled - allow but create audit event
            sync_state = self.env["itad.taxonomy.sync.state"].get_singleton()
            
            if sync_state.last_success_at:
                from datetime import timedelta
                now = self._now()
                stale_threshold = now - timedelta(hours=max_stale_hours)
                
                if sync_state.last_success_at < stale_threshold:
                    # Stale but allowing via break-glass - audit it
                    audit_model = self.env["itad.taxonomy.audit.log"]
                    audit_model.log_event(
                        action="stale_override_used",
                        details=(
                            f"Receiving wizard proceeded with stale taxonomy. "
                            f"Last sync: {sync_state.last_success_at}, "
                            f"Threshold: {stale_threshold}, "
                            f"Order: {self.fsm_order_id.name}, "
                            f"Break-glass reason: {sync_state.break_glass_reason or 'Not documented'}"
                        ),
                        success=True,
                    )
                    _logger.warning(
                        "Break-glass override: stale taxonomy used for order %s (last synced: %s)",
                        self.fsm_order_id.name, sync_state.last_success_at
                    )
    
    def _validate_material_requires_weight(self):
        """
        Validate weight is provided if material type requires it (Phase 2.3).
        """
        self.ensure_one()
        
        if self.material_type_id and self.material_type_id.requires_weight:
            if not self.actual_weight_lbs or self.actual_weight_lbs <= 0:
                raise ValidationError(
                    _("Material type '%(material)s' requires weight. Please provide actual weight.")
                    % {"material": self.material_type_id.name}
                )
    
    def _validate_material_requires_photo(self):
        """
        Validate photo/attachment is provided if material type requires it (Phase 2.3).
        """
        self.ensure_one()
        
        if self.material_type_id and self.material_type_id.requires_photo:
            # Check for attachments associated with this wizard or order
            # Using fsm_order_id as attachment reference
            attachment_count = self.env["ir.attachment"].search_count([
                ("res_model", "=", "fsm.order"),
                ("res_id", "=", self.fsm_order_id.id),
            ])
            
            if attachment_count == 0:
                raise ValidationError(
                    _("Material type '%(material)s' requires photo documentation. Please attach at least one photo to the order before receiving.")
                    % {"material": self.material_type_id.name}
                )
    
    def _check_hazard_class(self):
        """
        Log warning if material has hazard class (Phase 2.3).
        Does not block, just logs for audit.
        """
        self.ensure_one()
        
        if self.material_type_id and self.material_type_id.hazard_class:
            # Log to audit
            _logger.warning(
                "Receiving hazardous material: %s (Hazard Class: %s) on order %s",
                self.material_type_id.name,
                self.material_type_id.hazard_class,
                self.fsm_order_id.name,
            )
    
    def action_confirm_receipt(self):
        """
        Main action: Confirm receipt and create receiving_weight_record in ITAD Core.
        
        Phase 2.2a: Enhanced with API health check, rate limiting, validation, RBAC, error handling, and audit logging.
        Phase 2.3: Added taxonomy cache health check and material validation flags.
        """
        self.ensure_one()

        # Phase 2.2: RBAC check
        if not self.env.user.has_group("itad_core.group_receiving_manager"):
            raise AccessError(_("Only receiving managers can confirm receipts."))

        # Phase 2.3: Taxonomy cache health check (degraded mode)
        self._check_taxonomy_cache_health()
        
        # Phase 2.2a: API health/version compatibility check
        self._check_itad_core_compatibility()
        
        # Phase 2.2a: Rate limiting check
        self._check_rate_limit()

        # Phase 2.2: Enhanced validation
        self._validate_bol_format()
        self._validate_weight()
        
        # Phase 2.3: Material validation flags
        if not self.material_type_id:
            raise ValidationError(_("Material type is required."))
        
        self._validate_material_requires_weight()
        self._validate_material_requires_photo()
        self._check_hazard_class()

        # Call ITAD Core API
        try:
            response_data, idempotency_key, correlation_id = self._call_itad_receiving_endpoint()
        except UserError as exc:
            # Phase 2.2: Handle error with audit logging
            error_msg = str(exc)
            self._log_receipt_attempt(success=False, outcome="SERVER_ERROR", error_message=error_msg)
            
            # Update FSM order to exception state
            self.fsm_order_id.sudo().write({
                "itad_receipt_state": "exception",
            })
            raise  # Re-raise to show error to user

        # Success: Log attempt
        self._log_receipt_attempt(success=True, response_data=response_data, outcome="SUCCESS")
        
        # Update FSM order with receipt details
        receiving_weight_record_id = response_data.get("id")
        
        self.fsm_order_id.sudo().write({
            "itad_receipt_state": "received",
            "itad_receipt_confirmed_at": fields.Datetime.now(),
            "itad_receipt_weight_lbs": self.actual_weight_lbs,
            "itad_receipt_material_code": self.material_type_id.code if self.material_type_id else None,
            "itad_receiving_weight_record_id": receiving_weight_record_id,
            "itad_receipt_notes": self.operator_notes or "",
        })

        # Create audit log (reuse outbox pattern for consistency)
        self.env["itad.core.outbox"].create({
            "order_id": self.fsm_order_id.id,
            "state": "sent",
            "idempotency_key": idempotency_key,
            "correlation_id": correlation_id,
            "payload_json": json.dumps(self._build_receiving_payload(), indent=2),
            "payload_sha256": "",  # Not critical for receiving
            "attempt_count": self.attempt_count,
            "itad_receiving_weight_record_id": receiving_weight_record_id,
        })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Receipt Confirmed"),
                "message": _(
                    "Receipt confirmed successfully. Receiving Weight Record ID: %(record_id)s"
                ) % {"record_id": receiving_weight_record_id},
                "type": "success",
                "sticky": False,
            },
        }
