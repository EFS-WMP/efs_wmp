from odoo import api, models


class ItadCoreConfig(models.AbstractModel):
    _name = "itad.core.config"
    _description = "ITAD Core Config Helper"

    @api.model
    def get_itad_core_config(self):
        icp = self.env["ir.config_parameter"].sudo()
        base_url = icp.get_param("itad_core.base_url") or ""
        token = icp.get_param("itad_core.token") or ""
        if not base_url:
            port = icp.get_param("itad_core.port") or "8001"
            base_url = f"http://host.docker.internal:{port}"
        return base_url, token
