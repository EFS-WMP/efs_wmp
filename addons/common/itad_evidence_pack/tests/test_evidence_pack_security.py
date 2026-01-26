from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestEvidencePackSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_integration = cls.env.ref("itad_core.group_itad_integration")
        cls.user_no_group = cls.env["res.users"].create(
            {
                "name": "Evidence Pack User",
                "login": "evidence_pack_user",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )
        cls.user_integration = cls.env["res.users"].create(
            {
                "name": "Evidence Pack Integration",
                "login": "evidence_pack_integration",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.group_integration.id),
                ],
            }
        )

    def test_non_integration_user_cannot_create(self):
        with self.assertRaises(AccessError):
            self.env["itad.evidence.pack"].with_user(self.user_no_group).create(
                {
                    "name": "Snapshot",
                    "source_model": "fsm.order",
                    "source_record_ref": "FSM-001",
                    "snapshot_json": "{}",
                }
            )

    def test_integration_user_can_create_and_write(self):
        record = self.env["itad.evidence.pack"].with_user(self.user_integration).create(
            {
                "name": "Snapshot",
                "source_model": "fsm.order",
                "source_record_ref": "FSM-002",
                "snapshot_json": "{}",
            }
        )
        record.with_user(self.user_integration).write({"notes": "ok"})
        self.assertEqual(record.notes, "ok")
