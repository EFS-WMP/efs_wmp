import unittest
from contextlib import contextmanager

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tools import config

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

from . import test_itad_config
from . import test_outbox_idempotency
from . import test_no_attrs_states
from . import test_phase1_vertical_slice
from . import test_receiving_wizard_hardening
from . import test_receiving_contract_integration
from . import test_receiving_api_compat_check
from . import test_receiving_rate_limit
from . import test_receiving_audit_archiving
from . import test_migration_phase2_1_to_2_2
from . import test_phase2_2a_evidence_docs

