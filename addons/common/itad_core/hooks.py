# File: itad_core/hooks.py

def post_init_hook(cr_or_env, registry=None):
    """
    Phase 2.2: Idempotent initialization of system parameters.
    
    Sets default values only if parameters don't already exist.
    Preserves existing custom values.
    """
    from odoo import api, SUPERUSER_ID

    if registry is None and hasattr(cr_or_env, "cr"):
        env = cr_or_env
    else:
        env = api.Environment(cr_or_env, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"].sudo()
    
    # Define default parameters
    defaults = {
        "itad_core.default_container_type": "PALLET",
        "itad_core.default_scale_id": "DOCK-SCALE-01",
        "itad_core.receipt_timeout_seconds": "30",
        "itad_core.max_receipt_weight_lbs": "100000",
    }
    
    # Set only if not already present (idempotent)
    for key, value in defaults.items():
        if not icp.get_param(key):
            icp.set_param(key, value)
