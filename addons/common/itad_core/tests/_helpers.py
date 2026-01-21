# addons/common/itad_core/tests/_helpers.py
import uuid
from typing import Any


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
