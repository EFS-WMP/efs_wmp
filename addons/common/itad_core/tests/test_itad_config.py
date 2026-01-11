from odoo.tests.common import SavepointCase


class TestItadConfig(SavepointCase):
    def test_config_reads_params_and_fallback(self):
        config = self.env["itad.core.config"]
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("itad_core.base_url", "")
        icp.set_param("itad_core.token", "")
        icp.set_param("itad_core.port", "8010")

        base_url, token = config.get_itad_core_config()
        self.assertEqual(base_url, "http://host.docker.internal:8010")
        self.assertEqual(token, "")

        icp.set_param("itad_core.base_url", "http://example.local:9999")
        icp.set_param("itad_core.token", "token-123")
        base_url, token = config.get_itad_core_config()
        self.assertEqual(base_url, "http://example.local:9999")
        self.assertEqual(token, "token-123")
