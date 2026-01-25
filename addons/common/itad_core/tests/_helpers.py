# addons/common/itad_core/tests/_helpers.py
import uuid
from typing import Any

from odoo import fields


def create_test_partner(env, name: str | None = None, *, is_company: bool = True):
    partner_name = name or f"Test Partner {uuid.uuid4().hex[:8]}"
    values = {
        "name": partner_name,
        "is_company": is_company,
    }
    return env["res.partner"].create(values)


def _get_or_create_team(env):
    team = env["fsm.team"].search([], limit=1)
    if team:
        return team
    values = {
        "name": f"Test Team {uuid.uuid4().hex[:8]}",
        "sequence": 99,
    }
    return env["fsm.team"].create(values)


def create_test_location(env, partner, *, owner=None, team=None, **extra_vals: Any):
    """
    Creates fsm.location with required fields.

    `partner` is the related partner (_inherits target).
    `owner` is required by OCA; default is the same as `partner`.
    """
    team = team or _get_or_create_team(env)
    owner = owner or partner

    vals = {
        "partner_id": partner.id,
        "owner_id": owner.id,
        "team_id": team.id,
    }
    vals.update(extra_vals)
    return env["fsm.location"].create(vals)


def create_test_fsm_order(env, location, **vals: Any):
    values = dict(vals)
    values.setdefault("location_id", location.id)
    if "team_id" in env["fsm.order"]._fields and "team_id" not in values:
        location_team = location.sudo().team_id if location else False
        team = location_team or _get_or_create_team(env)
        values["team_id"] = team.id
    order = env["fsm.order"].sudo().create({"location_id": values["location_id"]})
    order.sudo().write(values)
    sql_fields = {
        "itad_pickup_manifest_id",
        "itad_manifest_no",
        "itad_bol_id",
        "itad_receipt_state",
        "itad_receipt_idempotency_key",
        "itad_receipt_confirmed_at",
        "itad_receipt_weight_lbs",
        "itad_receipt_material_code",
    }
    sql_updates = {field: values[field] for field in sql_fields if field in values}
    if sql_updates:
        set_clause = ", ".join(f"{field} = %s" for field in sql_updates.keys())
        params = list(sql_updates.values()) + [order.id]
        env.cr.execute(
            f"""
            UPDATE fsm_order
               SET {set_clause}
             WHERE id = %s
            """,
            params,
        )
    return order


def create_material_type_cache(env, **overrides: Any):
    """
    Create a material type cache record as superuser for tests.
    """
    cache_model = env["itad.material.type.cache"].sudo()
    code = overrides.get("code", "EW-CPU-001")
    existing = cache_model.search([("code", "=", code)], limit=1)
    if existing:
        return existing

    vals = {
        "itad_core_uuid": overrides.get("itad_core_uuid", str(uuid.uuid4())),
        "code": code,
        "name": overrides.get("name", f"Test Material {code}"),
        "stream": overrides.get("stream", "test"),
        "requires_photo": overrides.get("requires_photo", False),
        "requires_weight": overrides.get("requires_weight", False),
        "active": overrides.get("active", True),
    }
    vals.update({k: v for k, v in overrides.items() if k not in vals})
    return cache_model.create(vals)


def seed_taxonomy_cache(env, codes=None):
    """
    Ensure taxonomy cache has active records for tests.
    """
    records = []
    for code in codes or ["EW-CPU-001"]:
        records.append(create_material_type_cache(env, code=code, active=True))
    return records


def ensure_taxonomy_sync_state(env, *, last_success_at=None):
    """
    Ensure taxonomy sync state singleton exists with a recent last_success_at.
    """
    sync_model = env["itad.taxonomy.sync.state"].sudo()
    record = sync_model.search([], limit=1)
    if not record:
        record = sync_model.create({"name": "Material Taxonomy Sync State"})
    if last_success_at is None:
        last_success_at = fields.Datetime.now()
    record.write({"last_success_at": last_success_at, "last_error": False})
    return record
