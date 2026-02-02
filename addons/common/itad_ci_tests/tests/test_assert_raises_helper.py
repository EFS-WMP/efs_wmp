from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestAssertRaisesHelper(TransactionCase):
    def test_tuple_expected_matches(self):
        with self._assertRaises((AccessError, ValidationError)):
            raise AccessError("denied")

    def test_tuple_expected_mismatch_raises_assertion(self):
        with self.assertRaises(AssertionError):
            with self._assertRaises((AccessError, ValidationError)):
                raise UserError("wrong type")

    def test_single_expected_still_works(self):
        with self._assertRaises(ValidationError):
            raise ValidationError("boom")
