# File: itad_core/tests/test_sor_guardrails.py

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase

from ._helpers import create_test_fsm_order, create_test_location, create_test_partner


class TestSoRGuardrails(TransactionCase):
    """Phase 2.2 Hardening: System-of-Record guardrails for outbox + taxonomy."""

    PROTECTED_OPERATIONAL_FIELDS = [
        "stage_id",
        "date_start",
        "date_end",
        "scheduled_date",
        "location_id",
        "partner_id",
        "team_id",
        "priority",
        "name",
    ]

    PROTECTED_COMPLIANCE_FIELDS = [
        "itad_receipt_weight_lbs",
        "itad_receipt_material_code",
        "itad_receipt_confirmed_at",
        "itad_receipt_notes",
        "itad_receipt_idempotency_key",
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_integration = cls.env.ref("itad_core.group_itad_integration")
        cls.group_receiving = cls.env.ref("itad_core.group_receiving_manager")

        cls.user_no_group = cls.env["res.users"].create(
            {
                "name": "User No Group SoR",
                "login": "user_no_group_sor",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )

        cls.user_receiving = cls.env["res.users"].create(
            {
                "name": "Receiving Manager SoR",
                "login": "user_receiving_sor",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.group_receiving.id),
                ],
            }
        )

        cls.user_integration = cls.env["res.users"].create(
            {
                "name": "Integration User SoR",
                "login": "user_integration_sor",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.group_integration.id),
                ],
            }
        )

    def _create_order(self):
        partner = create_test_partner(self.env, name="SoR Guardrail Partner")
        location = create_test_location(self.env, partner, name="SoR Guardrail Location")
        order = create_test_fsm_order(
            self.env,
            location,
            name="SO-R-GUARD-ORDER",
        )
        now = fields.Datetime.now()
        order.write(
            {
                "date_start": now,
                "date_end": now,
                "itad_receipt_weight_lbs": 123.45,
                "itad_receipt_material_code": "SOR-MAT",
                "itad_receipt_confirmed_at": now,
                "itad_receipt_notes": "Do not mutate receipt notes",
                "itad_receipt_idempotency_key": "receipt-key-123",
            }
        )
        if "stage_id" in order._fields and not order.stage_id:
            stage = self.env["fsm.stage"].search([("stage_type", "=", "order")], limit=1)
            if stage:
                order.write({"stage_id": stage.id})
        if "scheduled_date" in order._fields:
            order.write({"scheduled_date": now})
        return order

    def _snapshot_fields(self, record, field_names):
        snapshot = {}
        for field_name in field_names:
            if field_name not in record._fields:
                continue
            value = record[field_name]
            if hasattr(value, "id"):
                snapshot[field_name] = value.id
            else:
                snapshot[field_name] = value
        return snapshot

    def _assert_fields_unchanged(self, before, record, field_names, label):
        for field_name in field_names:
            if field_name not in record._fields:
                continue
            value = record[field_name]
            if hasattr(value, "id"):
                value = value.id
            self.assertEqual(
                before.get(field_name),
                value,
                f"{label}: field '{field_name}' mutated by outbox handler",
            )

    def _create_outbox(self, order):
        return self.env["itad.core.outbox"].create(
            {
                "order_id": order.id,
                "idempotency_key": "sor-idempotency",
                "correlation_id": "sor-correlation",
                "payload_json": "{}",
                "payload_sha256": "deadbeef",
            }
        )

    def test_outbox_success_does_not_mutate_operational_or_compliance_fields(self):
        order = self._create_order()
        outbox = self._create_outbox(order)
        before_operational = self._snapshot_fields(order, self.PROTECTED_OPERATIONAL_FIELDS)
        before_compliance = self._snapshot_fields(order, self.PROTECTED_COMPLIANCE_FIELDS)

        outbox._record_success(
            {
                "pickup_manifest_id": "PM-001",
                "manifest_no": "MN-001",
                "status": "sent",
                "bol_id": "BOL-001",
                "geocode_gate": "GATE-1",
                "receiving_id": "RCV-001",
                "receiving_weight_record_id": "RWR-001",
            }
        )

        order._invalidate_cache()
        self._assert_fields_unchanged(
            before_operational,
            order,
            self.PROTECTED_OPERATIONAL_FIELDS,
            "Operational truth",
        )
        self._assert_fields_unchanged(
            before_compliance,
            order,
            self.PROTECTED_COMPLIANCE_FIELDS,
            "Compliance snapshot",
        )

    def test_outbox_failure_and_retry_do_not_mutate_operational_or_compliance_fields(self):
        order = self._create_order()
        outbox = self._create_outbox(order)
        before_operational = self._snapshot_fields(order, self.PROTECTED_OPERATIONAL_FIELDS)
        before_compliance = self._snapshot_fields(order, self.PROTECTED_COMPLIANCE_FIELDS)

        outbox._record_failure("Simulated failure")
        outbox.with_user(self.user_receiving).action_retry()

        order._invalidate_cache()
        self._assert_fields_unchanged(
            before_operational,
            order,
            self.PROTECTED_OPERATIONAL_FIELDS,
            "Operational truth",
        )
        self._assert_fields_unchanged(
            before_compliance,
            order,
            self.PROTECTED_COMPLIANCE_FIELDS,
            "Compliance snapshot",
        )

    def test_taxonomy_sync_state_rejects_non_integration_users(self):
        sync_state_model = self.env["itad.taxonomy.sync.state"]
        sync_state_model.sudo().search([]).unlink()

        with self.assertRaises((AccessError, UserError)):
            sync_state_model.with_user(self.user_no_group).create({"name": "Should Fail"})

        record = sync_state_model.sudo().create({"name": "Material Taxonomy Sync State"})

        with self.assertRaises((AccessError, UserError)):
            record.with_user(self.user_no_group).write({"last_error": "nope"})

        with self.assertRaises((AccessError, UserError)):
            record.with_user(self.user_receiving).write({"last_error": "still nope"})

        record.with_user(self.user_integration).write({"last_error": "integration ok"})
        self.assertEqual(record.last_error, "integration ok")

    def test_material_type_cache_permissions(self):
        cache_model = self.env["itad.material.type.cache"]

        with self.assertRaises((AccessError, UserError)):
            cache_model.with_user(self.user_no_group).create(
                {
                    "itad_core_uuid": "sor-cache-uuid",
                    "code": "SOR-CACHE-001",
                    "name": "SoR Cache",
                    "stream": "test",
                    "requires_photo": False,
                    "requires_weight": False,
                    "active": True,
                }
            )

        record = cache_model.with_user(self.user_integration).create(
            {
                "itad_core_uuid": "sor-cache-uuid-2",
                "code": "SOR-CACHE-002",
                "name": "SoR Cache 2",
                "stream": "test",
                "requires_photo": False,
                "requires_weight": False,
                "active": True,
            }
        )
        record.with_user(self.user_integration).write({"name": "SoR Cache 2 Updated"})
        self.assertEqual(record.name, "SoR Cache 2 Updated")
