#!/usr/bin/env python3
"""
Phase 2.3 Evidence Bundle Export Script

Exports evidence of last sync run for audit purposes:
- Sync state snapshot
- Last N taxonomy audit logs
- Correlation/run ID

Output: JSON files under docs/evidence/phase2.3/<timestamp>/

Usage:
    python export_sync_evidence.py --db-name=<database> [--limit=20]
    
    Or via Odoo shell:
    env['itad.material.sync'].export_sync_evidence()
"""

import json
import os
from datetime import datetime


def export_sync_evidence_odoo(env, output_dir=None, limit=20):
    """
    Export sync evidence from within Odoo environment.
    
    Args:
        env: Odoo environment
        output_dir: Output directory (default: docs/evidence/phase2.3/<timestamp>)
        limit: Number of audit logs to include
    
    Returns:
        dict with paths to generated files
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not output_dir:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_path, "docs", "evidence", "phase2.3", timestamp)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get sync state snapshot
    sync_state = env["itad.taxonomy.sync.state"].get_singleton()
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
    audit_logs = env["itad.taxonomy.audit.log"].search(
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
            "archived": log.archived,
            "archived_at": log.archived_at.isoformat() if log.archived_at else None,
        })
    
    audit_logs_path = os.path.join(output_dir, "audit_logs.json")
    with open(audit_logs_path, "w") as f:
        json.dump(audit_logs_data, f, indent=2)
    
    # Get cache stats
    cache_model = env["itad.material.type.cache"]
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
        "files": [
            "sync_state.json",
            "audit_logs.json",
            "cache_stats.json",
        ],
        "audit_log_count": len(audit_logs_data),
        "correlation_id": f"evidence-{timestamp}",
    }
    
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    return {
        "output_dir": output_dir,
        "manifest": manifest_path,
        "sync_state": sync_state_path,
        "audit_logs": audit_logs_path,
        "cache_stats": cache_stats_path,
    }


# Add method to itad.material.sync model
def _export_sync_evidence_method():
    """
    This method should be added to itad.material.sync model.
    
    Example usage:
        env['itad.material.sync'].export_sync_evidence()
    """
    pass


if __name__ == "__main__":
    print("This script must be run within Odoo environment.")
    print("Use: env['itad.material.sync'].export_sync_evidence()")
    print("Or import export_sync_evidence_odoo and call with env parameter.")
