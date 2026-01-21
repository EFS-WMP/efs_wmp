# file: scripts/odoo_xml_lint.py
"""
Odoo XML linter for version-specific deprecated fields.

Primary goal:
- Fail fast in pre-commit/CI BEFORE running Odoo, e.g. catch deprecated fields
  like `numbercall`/`doall` in ir.cron for Odoo 18.

Usage:
  python3 scripts/odoo_xml_lint.py --odoo-major 18 addons/common

Pre-commit (recommended): see snippet at bottom of this code block.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "odoo_src",
}


DEPRECATED_FIELDS_BY_VERSION = {
    # Odoo 18: `numbercall` and `doall` are removed from ir.cron
    # (this is exactly what your docker log shows).
    18: {
        "ir.cron": {"numbercall", "doall"},
    },
}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def iter_xml_files(paths: list[Path], exclude_dirs: set[str]) -> Iterable[Path]:
    for p in paths:
        if p.is_file():
            if p.suffix.lower() == ".xml":
                yield p
            continue

        if not p.is_dir():
            continue

        for f in p.rglob("*.xml"):
            if any(part in exclude_dirs for part in f.parts):
                continue
            yield f


def safe_parse_xml(path: Path) -> ET.Element | None:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError:
        return None


def find_line_numbers(path: Path, needle: str) -> list[int]:
    # cheap line mapping for actionable output
    lines: list[int] = []
    try:
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if needle in line:
                lines.append(idx)
    except OSError:
        pass
    return lines


def lint_deprecated_fields(root: ET.Element, path: Path, odoo_major: int) -> list[Violation]:
    violations: list[Violation] = []

    rules = DEPRECATED_FIELDS_BY_VERSION.get(odoo_major, {})
    if not rules:
        return violations

    # Odoo XML: <record id="..." model="..."><field name="...">...</field></record>
    for record in root.iter("record"):
        model = (record.get("model") or "").strip()
        if not model or model not in rules:
            continue

        banned = rules[model]
        record_id = (record.get("id") or "").strip()

        for field in record.findall("field"):
            fname = (field.get("name") or "").strip()
            if fname in banned:
                # Try to map to a line that contains the offending field
                needles = [f'name="{fname}"', f"name='{fname}'"]
                line = 1
                for n in needles:
                    hits = find_line_numbers(path, n)
                    if hits:
                        line = hits[0]
                        break

                hint = f"Remove <field name=\"{fname}\"> from model=\"{model}\" for Odoo {odoo_major}."
                if record_id:
                    hint += f" (record id={record_id})"
                violations.append(Violation(path=path, line=line, message=hint))

    return violations


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="odoo_xml_lint",
        description="Static XML checks for Odoo addons (version-aware deprecated fields).",
    )
    p.add_argument(
        "--odoo-major",
        type=int,
        default=18,
        help="Target Odoo major version (default: 18).",
    )
    p.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude (repeatable).",
    )
    p.add_argument(
        "paths",
        nargs="*",
        default=["addons"],
        help="Files or directories to scan (default: addons).",
    )
    return p


def main(argv: list[str]) -> int:
    args = build_arg_parser().parse_args(argv)

    exclude_dirs = set(DEFAULT_EXCLUDE_DIR_NAMES)
    exclude_dirs.update(args.exclude_dir)

    scan_paths = [Path(p) for p in args.paths]
    xml_files = list(iter_xml_files(scan_paths, exclude_dirs=exclude_dirs))

    all_violations: list[Violation] = []
    for xml_path in xml_files:
        root = safe_parse_xml(xml_path)
        if root is None:
            # non-fatal: just warn; you can make this fatal if you want
            print(f"{xml_path}:1: XML parse error (skipped)", file=sys.stderr)
            continue
        all_violations.extend(lint_deprecated_fields(root, xml_path, odoo_major=args.odoo_major))

    if all_violations:
        for v in all_violations:
            print(v.format(), file=sys.stderr)
        print(f"\nFound {len(all_violations)} violation(s).", file=sys.stderr)
        return 1

    print(f"OK: scanned {len(xml_files)} xml file(s), no violations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


# ----------------------------
# file: .pre-commit-config.yaml (snippet)
#
# - repo: local
#   hooks:
#     - id: odoo-xml-deprecated
#       name: Odoo XML deprecated fields (Odoo 18)
#       entry: python3 scripts/odoo_xml_lint.py --odoo-major 18
#       language: system
#       files: \.xml$
#
# Optional (nice-to-have): OCA general hooks (XML/manifest hygiene)
# - repo: https://github.com/OCA/odoo-pre-commit-hooks
#   rev: v0.0.0  # pick a real tag/commit
#   hooks:
#     - id: xml-check
#     - id: manifest-required-author
# ----------------------------
