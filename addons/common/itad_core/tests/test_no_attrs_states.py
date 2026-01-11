from __future__ import annotations

import os
from odoo.tests.common import SavepointCase
from odoo.modules.module import get_module_path


class TestNoAttrsStates(SavepointCase):
    """Guardrail test: Ensure Odoo 17+ XML compliance (no attrs=/states=)"""

    def test_no_attrs_or_states_in_xml_views(self):
        module_path = get_module_path("itad_core")
        self.assertTrue(module_path, "itad_core module path not found; module not installed?")

        views_dir = os.path.join(module_path, "views")
        self.assertTrue(os.path.isdir(views_dir), f"Expected views directory at: {views_dir}")

        violations: list[str] = []
        for root, _dirs, files in os.walk(views_dir):
            for filename in sorted(files):
                if not filename.endswith(".xml"):
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as f:
                    for lineno, line in enumerate(f, 1):
                        # Strict check: any occurrence of attrs= or states= is a failure
                        if "attrs=" in line or "states=" in line:
                            violations.append(f"{path}:{lineno}: {line.strip()}")

        if violations:
            raise AssertionError(
                "Deprecated XML attributes detected (Odoo 17+ forbids attrs=/states=). "
                "Replace with modifiers= JSON or supported boolean attributes.\n"
                + "\n".join(violations)
            )
