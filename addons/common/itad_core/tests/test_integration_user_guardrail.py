# File: itad_core/tests/test_integration_user_guardrail.py
"""
Phase 2.3 Extra Hardening: Integration User Guardrail Test

SECURITY: This test ensures only whitelisted users (non-human, API-only credentials)
have the group_itad_integration. Fails if any non-whitelisted human user has the group.

Whitelisted logins (configurable via env/param):
- itad_integration (system sync account)
- admin (development only)
"""

from odoo.tests.common import TransactionCase
from odoo import fields
import os


class TestIntegrationUserGuardrail(TransactionCase):
    """
    CI/test gate: FAIL if any non-whitelisted human user has group_itad_integration.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.integration_group = cls.env.ref("itad_core.group_itad_integration")
        
        # Default whitelist (can be overridden via env or config parameter)
        cls.default_whitelist = {"itad_integration", "admin", "__system__"}

    def _get_whitelist(self):
        """
        Get whitelist from environment variable or config parameter.
        
        Priority:
        1. ITAD_INTEGRATION_USER_WHITELIST env var (comma-separated)
        2. itad_core.integration_user_whitelist config param
        3. Default: itad_integration, admin, __system__
        """
        env_whitelist = os.environ.get("ITAD_INTEGRATION_USER_WHITELIST")
        if env_whitelist:
            return set(login.strip() for login in env_whitelist.split(","))
        
        param_whitelist = self.env["ir.config_parameter"].sudo().get_param(
            "itad_core.integration_user_whitelist"
        )
        if param_whitelist:
            return set(login.strip() for login in param_whitelist.split(","))
        
        return self.default_whitelist

    def test_no_unauthorized_users_have_integration_group(self):
        """
        SECURITY CRITICAL: Fail if any non-whitelisted user has integration group.
        
        This test should run in CI to catch accidental group assignments.
        """
        whitelist = self._get_whitelist()
        
        # Find all users with integration group
        integration_users = self.env["res.users"].search([
            ("groups_id", "in", [self.integration_group.id]),
        ])
        
        violations = []
        for user in integration_users:
            if user.login not in whitelist:
                violations.append({
                    "id": user.id,
                    "login": user.login,
                    "name": user.name,
                })
        
        if violations:
            violation_details = "\n".join(
                f"  - {v['login']} (ID: {v['id']}, Name: {v['name']})"
                for v in violations
            )
            self.fail(
                f"SECURITY VIOLATION: Non-whitelisted users have group_itad_integration:\n"
                f"{violation_details}\n\n"
                f"Whitelisted logins: {whitelist}\n\n"
                f"To fix:\n"
                f"  1. Remove group from unauthorized users, OR\n"
                f"  2. Add login to whitelist via:\n"
                f"     - Env: ITAD_INTEGRATION_USER_WHITELIST=login1,login2\n"
                f"     - Param: itad_core.integration_user_whitelist"
            )

    def test_whitelist_documentation(self):
        """Test that whitelist is properly configured and documented."""
        whitelist = self._get_whitelist()
        
        # Should always include system accounts
        expected_minimum = {"admin", "__system__"}
        
        # Just log for awareness (don't fail)
        missing_recommended = expected_minimum - whitelist
        if missing_recommended:
            # Log warning but don't fail - user may have intentionally excluded
            pass
        
        # Whitelist should not be empty
        self.assertTrue(
            len(whitelist) > 0,
            "Integration user whitelist is empty. At least one account should be whitelisted."
        )
