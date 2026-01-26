from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ItadEvidencePack(models.Model):
    _name = "itad.evidence.pack"
    _description = "ITAD Evidence Pack Snapshot"
    _order = "captured_at desc, id desc"

    name = fields.Char(required=True, default=lambda self: "Evidence Pack")
    source_model = fields.Char(required=True, help="Source model for snapshot reference")
    source_record_ref = fields.Char(
        help="External/source identifier (snapshot only; no SoR ownership)"
    )
    snapshot_json = fields.Text(
        help="Serialized snapshot payload for evidence (read-only in Odoo)."
    )
    captured_at = fields.Datetime(default=fields.Datetime.now, required=True)
    captured_by = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group("itad_core.group_itad_integration"):
            raise AccessError(_("Evidence Pack snapshots are integration-only."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.user.has_group("itad_core.group_itad_integration"):
            raise AccessError(_("Evidence Pack snapshots are integration-only."))
        return super().write(vals)
