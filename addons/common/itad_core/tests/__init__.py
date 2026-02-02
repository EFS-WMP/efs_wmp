import unittest
import importlib
import pkgutil
import logging
from contextlib import contextmanager

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tools import config

_logger = logging.getLogger(__name__)

if config["test_enable"]:
    _original_assert_raises = TransactionCase._assertRaises

    @contextmanager
    def _assert_raises_no_savepoint(self, exception, *, msg=None):
        if issubclass(exception, UserError):
            with unittest.TestCase.assertRaises(self, exception, msg=msg) as cm:
                yield cm
        else:
            with _original_assert_raises(self, exception, msg=msg) as cm:
                yield cm

    TransactionCase._assertRaises = _assert_raises_no_savepoint

def _import_all_test_modules():
    """
    Ensure all test modules are loaded when Odoo test runner imports itad_core.tests.
    This prevents "false-green" runs when new test_*.py files are added but not imported.
    """
    module_names = sorted(
        m.name for m in pkgutil.iter_modules(__path__)
        if m.name.startswith("test_")
    )
    for name in module_names:
        importlib.import_module(f"{__name__}.{name}")

_import_all_test_modules()

# Explicit imports to ensure Odoo test loader picks up new suites in all environments
from . import test_fsm_itad_outbox_access_basic  # noqa: F401,E402
from . import test_fsm_itad_outbox_access_requeue  # noqa: F401,E402
from . import test_material_sync_contract  # noqa: F401,E402

