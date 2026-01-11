{
    "name": "ITAD Core Bridge (Phase 1)",
    "summary": "Odoo 18 Field Service → ITAD Core pickup_manifest outbox bridge",
    "description": """
Phase 1 vertical slice:
- Odoo 18 (SoR dispatch) submits pickup_manifest via outbox (idempotent)
- ITAD Core (SoR compliance) returns manifest_id/bol_id/status/geocode gate
- Odoo stores returned IDs as read-only references only (no dual writes)
""",
    "category": "Services",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    "depends": [
        "base",
        "fieldservice",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/itad_outbox_views.xml",
        "views/fsm_order_itad.xml",
        "data/itad_outbox_cron.xml",
    ],
    "installable": True,
    "application": False,
}
