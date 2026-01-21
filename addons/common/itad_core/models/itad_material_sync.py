# File: itad_core/models/itad_material_sync.py

import hashlib
import json
import logging
from datetime import datetime, timedelta

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Phase 2.3 Security: Deterministic advisory lock namespace
# Lock key derived from SHA256 for auditability and stability
SYNC_LOCK_NAMESPACE = "itad_core.material_type_sync"


class ItadMaterialSync(models.AbstractModel):
    """
    Material Taxonomy Sync Service
    
    Phase 2.3: Handles syncing material taxonomy from ITAD Core to local cache.
    Uses PostgreSQL advisory lock for concurrency control.
    """
    _name = "itad.material.sync"
    _description = "Material Taxonomy Sync Service"
    
    def _advisory_lock_key(self, namespace):
        """
        Derive deterministic PostgreSQL advisory lock key from namespace.
        
        Uses SHA256(namespace) -> first 8 bytes -> unsigned 64-bit int -> mask to 63-bit signed safe.
        Ensures stable, auditable lock keys across deployments.
        PostgreSQL advisory locks use bigint (signed 64-bit), so we mask to fit.
        
        Args:
            namespace: String namespace (e.g., "itad_core.material_type_sync")
        
        Returns:
            int: Signed 64-bit safe integer lock key (0 to 2^63-1)
        """
        hash_bytes = hashlib.sha256(namespace.encode('utf-8')).digest()[:8]
        # Convert to unsigned 64-bit, then mask to 63-bit signed safe
        key = int.from_bytes(hash_bytes, 'big', signed=False) & ((1 << 63) - 1)
        return key
    
    def _get_config(self):
        """Get ITAD Core API configuration"""
        icp = self.env["ir.config_parameter"].sudo()
        
        # Reuse existing config pattern from Phase 2.2
        base_url = icp.get_param("itad_core.base_url", "http://localhost:8000")
        token = icp.get_param("itad_core.api_token", "")
        
        return base_url.rstrip("/"), token
    
    def _get_sync_config(self):
        """Get taxonomy sync-specific configuration"""
        icp = self.env["ir.config_parameter"].sudo()
        
        return {
            "include_inactive": icp.get_param(
                "itad_core.taxonomy.sync.include_inactive", "true"
            ).lower() == "true",
            "incremental_enabled": icp.get_param(
                "itad_core.taxonomy.sync.incremental_enabled", "true"
            ).lower() == "true",
            "max_stale_hours": int(icp.get_param(
                "itad_core.taxonomy.sync.max_stale_hours", "24"
            )),
            "timeout_seconds": int(icp.get_param(
                "itad_core.taxonomy.sync.timeout_seconds", "15"
            )),
            "overlap_seconds": int(icp.get_param(
                "itad_core.taxonomy.sync.overlap_seconds", "2"
            )),
            "block_if_stale": icp.get_param(
                "itad_core.taxonomy.sync.block_if_stale", "true"
            ).lower() == "true",
        }
    
    def _compute_source_hash(self, item_data):
        """Compute stable hash from item fields for change detection"""
        # Canonical field order for consistent hashing
        fields_to_hash = [
            str(item_data.get("code", "")),
            str(item_data.get("name", "")),
            str(item_data.get("stream", "")),
            str(item_data.get("hazard_class", "")),
            str(item_data.get("default_action", "")),
            str(item_data.get("requires_photo", False)),
            str(item_data.get("requires_weight", False)),
            str(item_data.get("is_active", True)),
            # Phase 2.4a: Include pricing_state and billing fields in hash
            str(item_data.get("pricing_state", "unpriced")),
            str(item_data.get("default_price", "")),
            str(item_data.get("basis_of_charge", "")),
            str(item_data.get("gl_account_code", "")),
        ]
        
        combined = "|".join(fields_to_hash)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
    
    def _upsert_material_type(self, item, now):
        """
        Upsert a single material type record.
        
        SECURITY: Uses sudo() to write. Permission enforced at cache model layer
        (requires integration group OR superuser).
        
        Returns ('created'|'updated'|'deactivated'|'unchanged', record)
        """
        cache_model = self.env["itad.material.type.cache"].sudo()
        
        itad_core_uuid = item.get("id")
        if not itad_core_uuid:
            _logger.warning("Skipping item with missing 'id' field: %s", item)
            return "unchanged", None
        
        # Find existing by itad_core_uuid ONLY (never match by code/name)
        existing = cache_model.search([("itad_core_uuid", "=", str(itad_core_uuid))], limit=1)
        
        # Parse source_updated_at (convert ISO8601 string to Odoo datetime)
        source_updated_at_iso = item.get("updated_at")
        source_updated_at = None
        if source_updated_at_iso:
            try:
                # Parse ISO8601
                source_updated_at_dt = datetime.fromisoformat(
                    source_updated_at_iso.replace("Z", "+00:00")
                )
                # Convert to naive UTC (Odoo stores as naive with implicit UTC)
                source_updated_at = fields.Datetime.to_string(source_updated_at_dt.replace(tzinfo=None))
            except Exception as e:
                _logger.warning("Failed to parse updated_at '%s': %s", source_updated_at_iso, e)
        
        # Build values
        vals = {
            "itad_core_uuid": str(itad_core_uuid),
            "code": item.get("code"),
            "name": item.get("name"),
            "stream": item.get("stream"),
            "hazard_class": item.get("hazard_class"),
            "default_action": item.get("default_action"),
            "requires_photo": item.get("requires_photo", False),
            "requires_weight": item.get("requires_weight", False),
            "active": item.get("is_active", True),
            "source_updated_at": source_updated_at,
            "last_synced_at": now,
            "source_hash": self._compute_source_hash(item),
            # Phase 2.4a: Pricing state and billing metadata fields
            "pricing_state": item.get("pricing_state", "unpriced"),
            "default_price": float(item.get("default_price")) if item.get("default_price") is not None else False,
            "basis_of_charge": item.get("basis_of_charge"),
            "gl_account_code": item.get("gl_account_code"),
        }
        
        if existing:
            # Check if anything changed (optimization)
            if existing.source_hash == vals["source_hash"]:
                # No change, just update last_synced_at
                existing.write({"last_synced_at": now})
                
                # Check for deactivation
                if not vals["active"] and existing.active:
                    return "deactivated", existing
                
                return "unchanged", existing
            else:
                # Update existing record
                existing.write(vals)
                
                # Determine action
                if not vals["active"] and existing.active:
                    return "deactivated", existing
                else:
                    return "updated", existing
        else:
            # Create new record
            new_record = cache_model.create(vals)
            return "created", new_record
    
    @api.model
    def _sync_from_itad_core(self, manual=False):
        """
        Sync material taxonomy from ITAD Core.
        
        Algorithm:
        1. Acquire PostgreSQL advisory lock (exit if already locked)
        2. Determine updated_since cursor from sync state
        3. GET /api/v1/material-types?include_inactive=true&updated_since=...
        4. Upsert each item by itad_core_uuid
        5. Update sync state with stats
        
        Args:
            manual: True if triggered by "Sync Now" button, False if cron
        
        Returns:
            dict with stats
        """
        _logger.info("Starting material taxonomy sync (manual=%s)", manual)
        
        sync_state_model = self.env["itad.taxonomy.sync.state"]
        sync_state = sync_state_model.get_singleton()
        
        now = fields.Datetime.now()
        
        # Step 1: Acquire deterministic advisory lock
        lock_key = self._advisory_lock_key(SYNC_LOCK_NAMESPACE)
        _logger.info("Attempting to acquire advisory lock (key=%s, namespace=%s)", lock_key, SYNC_LOCK_NAMESPACE)
        
        lock_acquired = False
        try:
            self.env.cr.execute(
                "SELECT pg_try_advisory_lock(%s::bigint)",
                [lock_key]
            )
            lock_acquired = self.env.cr.fetchone()[0]
        except Exception as e:
            _logger.error("Failed to acquire advisory lock: %s", e)
            
            # Log audit event
            self.env["itad.taxonomy.audit.log"].log_event(
                action="sync_failure",
                details=f"Advisory lock acquisition failed: {e}",
                success=False,
                error_message=str(e),
            )
            
            sync_state.write({
                "last_attempt_at": now,
                "last_error": f"Failed to acquire advisory lock: {e}",
            })
            return {"success": False, "error": "Lock acquisition failed"}
        
        if not lock_acquired:
            error_msg = "Sync already running (could not acquire advisory lock)"
            _logger.warning(error_msg)
            
            # Log audit event
            self.env["itad.taxonomy.audit.log"].log_event(
                action="sync_failure",
                details="Advisory lock already held by another process",
                success=False,
                error_message=error_msg,
            )
            
            sync_state.write({
                "last_attempt_at": now,
                "last_error": error_msg,
            })
            return {"success": False, "error": error_msg}
        
        try:
            # Log sync attempt
            self.env["itad.taxonomy.audit.log"].log_event(
                action="sync_attempt",
                details=f"Manual: {manual}",
            )
            
            # Step 2: Determine updated_since with overlap
            base_url, token = self._get_config()
            sync_config = self._get_sync_config()
            
            updated_since = None
            if sync_config["incremental_enabled"] and sync_state.last_cursor_updated_since:
                # Apply overlap to catch same-timestamp updates
                overlap_seconds = sync_config["overlap_seconds"]
                cursor = sync_state.last_cursor_updated_since
                updated_since = cursor - timedelta(seconds=overlap_seconds)
                _logger.info(
                    "Using incremental cursor with overlap: cursor=%s, overlap=%ss, updated_since=%s",
                    cursor, overlap_seconds, updated_since
                )
            
            # Step 3: Call ITAD Core API
            url = f"{base_url}/api/v1/material-types"
            params = {
                "include_inactive": "true" if sync_config["include_inactive"] else "false",
            }
            
            if updated_since:
                params["updated_since"] = fields.Datetime.to_string(updated_since)
            
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            _logger.info("Fetching material types from %s with params %s", url, params)
            
            try:
                resp = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=sync_config["timeout_seconds"]
                )
                resp.raise_for_status()
            except requests.RequestException as e:
                error_msg = f"HTTP request failed: {e}"
                _logger.error(error_msg)
                sync_state.write({
                    "last_attempt_at": now,
                    "last_error": error_msg,
                })
                return {"success": False, "error": error_msg}
            
            # Parse response
            try:
                data = resp.json()
            except Exception as e:
                error_msg = f"Failed to parse JSON response: {e}"
                _logger.error(error_msg)
                
                # Log audit event
                self.env["itad.taxonomy.audit.log"].log_event(
                    action="sync_failure",
                    details="JSON parsing failed",
                    success=False,
                    error_message=error_msg,
                )
                
                sync_state.write({
                    "last_attempt_at": now,
                    "last_error": error_msg,
                })
                return {"success": False, "error": error_msg}
            
            # SECURITY: Validate contract - wrapper format
            if "items" not in data or "meta" not in data:
                error_msg = "Invalid API response: missing 'items' or 'meta' wrapper keys"
                _logger.error(error_msg)
                
                # Log audit event
                self.env["itad.taxonomy.audit.log"].log_event(
                    action="sync_failure",
                    details=f"Contract violation: response={data}",
                    success=False,
                    error_message=error_msg,
                )
                sync_state.write({
                    "last_attempt_at": now,
                    "last_error": error_msg,
                })
                return {"success": False, "error": error_msg}
            
            items = data["items"]
            meta = data["meta"]
            
            _logger.info("Received %d items from ITAD Core (meta: %s)", len(items), meta)
            
            # SECURITY: Validate contract - required item fields
            required_fields = ['id', 'code', 'name', 'stream', 'requires_photo', 
                             'requires_weight', 'is_active', 'updated_at']
            for idx, item in enumerate(items):
                missing = [f for f in required_fields if f not in item]
                if missing:
                    error_msg = f"Item {idx} missing required fields: {missing}"
                    _logger.error(error_msg)
                    
                    # Log audit event
                    self.env["itad.taxonomy.audit.log"].log_event(
                        action="sync_failure",
                        details=f"Contract violation: item={item}",
                        success=False,
                        error_message=error_msg,
                    )
                    
                    sync_state.write({
                        "last_attempt_at": now,
                        "last_error": error_msg,
                    })
                    return {"success": False, "error": error_msg}
            
            # Step 4: Upsert each item
            stats = {
                "created": 0,
                "updated": 0,
                "deactivated": 0,
                "unchanged": 0,
            }
            
            max_updated_at = None
            
            for item in items:
                action, record = self._upsert_material_type(item, now)
                stats[action] += 1
                
                # Track max updated_at for cursor
                item_updated_at = item.get("updated_at")
                if item_updated_at:
                    try:
                        item_dt = datetime.fromisoformat(item_updated_at.replace("Z", "+00:00"))
                        if max_updated_at is None or item_dt > max_updated_at:
                            max_updated_at = item_dt
                    except Exception:
                        pass
            
            # Step 5: Update sync state
            new_cursor = None
            if sync_config["incremental_enabled"] and max_updated_at:
                # Use max(updated_at) as new cursor
                new_cursor = fields.Datetime.to_string(max_updated_at.replace(tzinfo=None))
            
            stats_json = json.dumps(stats, indent=2)
            
            # Log success audit event
            self.env["itad.taxonomy.audit.log"].log_event(
                action="sync_success",
                details=stats_json,
                success=True,
            )
            
            sync_state.write({
                "last_attempt_at": now,
                "last_success_at": now,
                "last_error": False,  # Clear error on success
                "last_cursor_updated_since": new_cursor,
                "stats_last_run": stats_json,
            })
            
            _logger.info("Sync completed successfully. Stats: %s", stats_json)
            
            return {
                "success": True,
                "stats": stats,
                "cursor": new_cursor,
            }
            
        finally:
            # Always release advisory lock
            try:
                self.env.cr.execute(
                    "SELECT pg_advisory_unlock(%s::bigint)",
                    [lock_key]
                )
                _logger.info("Released advisory lock (key=%s)", lock_key)
            except Exception as e:
                _logger.error("Failed to release advisory lock: %s", e)
    
    @api.model
    def export_sync_evidence(self, output_dir=None, limit=20):
        """
        Export evidence bundle of last sync run for audit purposes.
        
        Args:
            output_dir: Optional output directory (default: docs/evidence/phase2.3/<timestamp>)
            limit: Number of audit logs to include (default 20)
        
        Returns:
            dict with paths to generated files
        """
        import os
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not output_dir:
            # Default to addons/common/itad_core/docs/evidence/phase2.3/<timestamp>
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_path, "docs", "evidence", "phase2.3", timestamp)
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Get sync state snapshot
        sync_state = self.env["itad.taxonomy.sync.state"].get_singleton()
        sync_state_data = {
            "id": sync_state.id,
            "name": sync_state.name,
            "last_success_at": sync_state.last_success_at.isoformat() if sync_state.last_success_at else None,
            "last_attempt_at": sync_state.last_attempt_at.isoformat() if sync_state.last_attempt_at else None,
            "last_error": sync_state.last_error or None,
            "last_cursor_updated_since": sync_state.last_cursor_updated_since.isoformat() if sync_state.last_cursor_updated_since else None,
            "stats_last_run": sync_state.stats_last_run,
            "break_glass_reason": sync_state.break_glass_reason or None,
            "exported_at": timestamp,
        }
        
        sync_state_path = os.path.join(output_dir, "sync_state.json")
        with open(sync_state_path, "w") as f:
            json.dump(sync_state_data, f, indent=2)
        
        # Get recent audit logs
        audit_logs = self.env["itad.taxonomy.audit.log"].search(
            [],
            limit=limit,
            order="occurred_at desc"
        )
        
        audit_logs_data = []
        for log in audit_logs:
            audit_logs_data.append({
                "id": log.id,
                "user_id": log.user_id.id,
                "user_name": log.user_id.name,
                "occurred_at": log.occurred_at.isoformat() if log.occurred_at else None,
                "action": log.action,
                "details": log.details,
                "success": log.success,
                "error_message": log.error_message,
            })
        
        audit_logs_path = os.path.join(output_dir, "audit_logs.json")
        with open(audit_logs_path, "w") as f:
            json.dump(audit_logs_data, f, indent=2)
        
        # Get cache stats
        cache_model = self.env["itad.material.type.cache"]
        cache_stats = {
            "total_records": cache_model.search_count([]),
            "active_records": cache_model.search_count([("active", "=", True)]),
            "inactive_records": cache_model.search_count([("active", "=", False)]),
            "exported_at": timestamp,
        }
        
        cache_stats_path = os.path.join(output_dir, "cache_stats.json")
        with open(cache_stats_path, "w") as f:
            json.dump(cache_stats, f, indent=2)
        
        # Create manifest
        manifest = {
            "evidence_bundle_version": "1.0",
            "phase": "2.3",
            "exported_at": timestamp,
            "files": ["sync_state.json", "audit_logs.json", "cache_stats.json"],
            "audit_log_count": len(audit_logs_data),
            "correlation_id": f"evidence-{timestamp}",
        }
        
        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        _logger.info("Evidence bundle exported to: %s", output_dir)
        
        return {
            "output_dir": output_dir,
            "manifest": manifest_path,
            "sync_state": sync_state_path,
            "audit_logs": audit_logs_path,
            "cache_stats": cache_stats_path,
            "correlation_id": f"evidence-{timestamp}",
        }
    
    @api.model
    def action_sync_now(self):
        """Action called by 'Sync Now' button"""
        result = self._sync_from_itad_core(manual=True)
        
        if result.get("success"):
            stats = result.get("stats", {})
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Taxonomy Sync Complete",
                    "message": (
                        f"Successfully synced material taxonomy. "
                        f"Created: {stats.get('created', 0)}, "
                        f"Updated: {stats.get('updated', 0)}, "
                        f"Deactivated: {stats.get('deactivated', 0)}, "
                        f"Unchanged: {stats.get('unchanged', 0)}"
                    ),
                    "type": "success",
                    "sticky": False,
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Taxonomy Sync Failed",
                    "message": result.get("error", "Unknown error"),
                    "type": "warning",
                    "sticky": True,
                },
            }
