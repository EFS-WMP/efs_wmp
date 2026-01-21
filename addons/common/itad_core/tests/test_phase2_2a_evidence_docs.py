# File: itad_core/tests/test_phase2_2a_evidence_docs.py

from pathlib import Path

from odoo.tests.common import TransactionCase


class TestPhase22aEvidenceDocs(TransactionCase):
    def _read_doc(self, relative_path: str) -> str:
        repo_root = Path("/mnt/odoo-dev")
        self.assertTrue(repo_root.exists(), "Repo root mount missing at /mnt/odoo-dev.")
        doc_path = repo_root / relative_path
        self.assertTrue(doc_path.exists(), f"Missing required doc: {relative_path}")
        return doc_path.read_text(encoding="utf-8")

    def test_phase2_2a_docs_reference_evidence_and_commands(self):
        tasks_md = self._read_doc("tasks.md")
        implementation_plan = self._read_doc("implementation_plan.md")

        evidence_path = "docs/evidence/phase2.2a"
        self.assertIn(evidence_path, tasks_md)
        self.assertIn(evidence_path, implementation_plan)

        canonical_cmd = (
            "docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 "
            "odoo --test-enable -d odoo18_db -c /etc/odoo/odoo.conf -u itad_core --stop-after-init --no-http"
        )
        self.assertIn(canonical_cmd, tasks_md)
        self.assertIn(canonical_cmd, implementation_plan)

        psql_cmd = (
            "docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml exec -T db18 "
            "psql -U odoo -d postgres -c \"\\l+\""
        )
        self.assertIn(psql_cmd, tasks_md)
