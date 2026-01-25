{
    "name": "ITAD Core Bridge (Phase 2.3)",
    "summary": "Odoo 18 Field Service → ITAD Core pickup_manifest + receiving confirmation with material taxonomy sync",
    "description": """
Phase 1: Pickup manifest submission (idempotent outbox bridge)
Phase 2.1: Receiving Dashboard MVP
Phase 2.2: Transition Hardening
- Configurable defaults via ir.config_parameter
- Idempotent retry mechanism (stable Idempotency-Key)
- RBAC group for receiving managers
- Enhanced validation (BOL format + weight sanity)
- Monitoring fields + audit log model
- Prevent forbidden Odoo XML syntax (no attrs/states)
Phase 2.3: Material Taxonomy Sync
- Read-only material type cache from ITAD Core (SoR)
- Automated hourly sync with incremental cursor
- Validation flags (requires_weight, requires_photo, hazard_class)
- Degraded mode handling (empty cache, stale sync blocking)
- Concurrency-safe sync with PostgreSQL advisory locks
""",
    "category": "Services",
    "version": "18.0.2.3.0",
    "license": "LGPL-3",
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    "depends": [
        "base",
        "fieldservice",
    ],
    "data": [
        "security/itad_core_groups.xml",
        "security/itad_core_integration_group.xml",
        "security/ir.model.access.csv",
        "data/itad_core_system_parameters.xml",
        "views/templates.xml",
        "views/views.xml",
        "views/itad_menu_root.xml",
        "views/itad_outbox_views.xml",
        "data/itad_taxonomy_sync_cron.xml",
        "data/itad_material_type_sync_action.xml",
        "views/fsm_order_itad.xml",
        "views/itad_receiving_views.xml",
        "views/itad_material_type_cache_views.xml",
        "views/itad_taxonomy_sync_state_views.xml",
        "views/itad_taxonomy_audit_log_views.xml",
        "views/itad_operational_reports_views.xml",
        "views/itad_ops_health_views.xml",
        "views/itad_ops_menu.xml",
        "data/itad_outbox_cron.xml",
        "data/itad_receipt_audit_archiving_cron.xml",
        "data/itad_taxonomy_audit_retention_cron.xml",
        "data/itad_ops_cron.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
