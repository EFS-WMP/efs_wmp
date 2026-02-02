from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestAssertRaisesNoSavepoint(TransactionCase):
    def test_single_class(self):
        with self._assertRaises(ValidationError):
            raise ValidationError("boom")

    def test_tuple_with_usererror_uses_plain_context(self):
        with self._assertRaises((AccessError, UserError)):
            raise UserError("user error path")

    def test_tuple_mismatch_raises_assertion(self):
        with self.assertRaises(AssertionError):
            with self._assertRaises((AccessError, ValidationError)):
                raise UserError("not expected")
