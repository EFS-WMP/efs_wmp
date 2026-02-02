from unittest.mock import Mock, patch

from odoo.tests.common import TransactionCase


class TestMaterialSyncContract(TransactionCase):
    """
    Ensure degraded responses are handled gracefully (no crash, warning logged).
    """

    @patch("odoo.addons.itad_core.models.itad_material_sync.requests.get")
    def test_missing_items_meta_logs_warning(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"foo": "bar"}  # Missing items/meta wrapper
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        sync_model = self.env["itad.material.sync"]

        with self.assertLogs("odoo.addons.itad_core.models.itad_material_sync", level="WARNING"):
            result = sync_model._sync_from_itad_core(manual=True)

        self.assertFalse(result.get("success"))
        self.assertIn("missing 'items' or 'meta'", result.get("error"))
        stats = result.get("stats")
        expected = {"created": 0, "updated": 0, "disabled": 0, "unchanged": 0}
        self.assertIsInstance(stats, dict)
        for key, value in expected.items():
            self.assertEqual(stats.get(key), value)
        self.assertEqual(stats.get("deactivated", 0), 0)
        self.assertIsNone(result.get("cursor"))

        sync_state = self.env["itad.taxonomy.sync.state"].sudo().get_singleton()
        self.assertTrue(sync_state.last_error)
