import unittest
from contextlib import contextmanager

from odoo.tests.common import TransactionCase
from odoo.tools import config
from odoo.exceptions import UserError

# Patch TransactionCase._assertRaises to handle tuples and UserError without savepoint side-effects
if config["test_enable"]:
    _original_assert_raises = TransactionCase._assertRaises

    @contextmanager
    def _assert_raises_safe(self, exception, *, msg=None):
        exc_types = exception if isinstance(exception, tuple) else (exception,)
        use_unittest = len(exc_types) > 1 or any(
            isinstance(exc, type) and issubclass(exc, UserError) for exc in exc_types
        )
        if use_unittest:
            with unittest.TestCase.assertRaises(self, exc_types, msg=msg) as cm:
                yield cm
            return
        with _original_assert_raises(self, exc_types[0], msg=msg) as cm:
            yield cm

    TransactionCase._assertRaises = _assert_raises_safe
