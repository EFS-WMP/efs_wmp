#!/usr/bin/env python3
"""
Odoo addon hygiene checks for CI.

Checks:
- Fail if any *.DISABLED files exist.
- Fail if any addon directory in addons_path lacks __manifest__.py.
- Report XML/CSV files under standard addon folders that are not referenced in
  __manifest__.py (data/demo/qweb/assets), with allowlist support.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = ROOT / "scripts" / "odoo_ci_allowlist.txt"
DEFAULT_ODOO_CONF = ROOT / "docker" / "odoo18" / "odoo.conf"
DEFAULT_COMPOSE = ROOT / "docker" / "odoo18" / "docker-compose.odoo18.yml"

IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".github",
    ".idea",
    ".vscode",
    ".oca",
    "setup",
    "readme",
    "docs",
    "dist",
    "build",
}

CANDIDATE_DIRS = {"views", "data", "demo", "security", "report", "wizard"}
CANDIDATE_SUFFIXES = {".xml", ".csv"}


def _to_posix(path: Path) -> str:
    return path.as_posix()


def _normalize_rel(value: str) -> str:
    value = value.strip().replace("\\", "/")
    return PurePosixPath(value).as_posix().lstrip("./")


def _load_allowlist(path: Path) -> dict[str, set[str]]:
    allow = {
        "missing_manifest": set(),
        "manifest_coverage": set(),
        "disabled": set(),
    }
    if not path.exists():
        return allow
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            category, value = line.split(":", 1)
        else:
            category, value = "manifest_coverage", line
        category = category.strip()
        if category not in allow:
            continue
        allow[category].add(_normalize_rel(value))
    return allow


def _parse_addons_path(conf_path: Path) -> list[str]:
    if not conf_path.exists():
        return []
    for line in conf_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("addons_path"):
            _, value = line.split("=", 1)
            return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _parse_volume_mappings(compose_path: Path) -> dict[str, Path]:
    if not compose_path.exists():
        return {}
    mappings: dict[str, Path] = {}
    quoted = re.compile(r'^\s*-\s*"(.+):(/[^"]+)"\s*$')
    unquoted = re.compile(r"^\s*-\s*(.+):(/\\S+)\s*$")
    for line in compose_path.read_text(encoding="utf-8").splitlines():
        match = quoted.match(line) or unquoted.match(line)
        if not match:
            continue
        host_raw = match.group(1).strip()
        container = match.group(2).strip().rstrip("/")
        host_raw = host_raw.replace("\\\\", "\\")
        host_path = Path(host_raw)
        if not host_path.is_absolute():
            host_path = compose_path.parent / host_path
        mappings[container] = host_path
    return mappings


def _resolve_addons_roots(addons_paths: list[str], volume_map: dict[str, Path]) -> list[Path]:
    roots = []
    for container_path in addons_paths:
        key = container_path.rstrip("/")
        host_path = volume_map.get(key)
        if host_path is None:
            candidates = [
                prefix
                for prefix in volume_map
                if key.startswith(prefix.rstrip("/") + "/")
            ]
            if candidates:
                best_prefix = max(candidates, key=len)
                suffix = key[len(best_prefix):].lstrip("/")
                host_path = volume_map[best_prefix] / suffix
        if host_path and host_path.exists():
            roots.append(host_path)
    return roots


def _find_disabled_files(allowlist: set[str]) -> list[str]:
    disabled = []
    for path in ROOT.rglob("*.DISABLED"):
        rel = _to_posix(path.relative_to(ROOT))
        if rel in allowlist:
            continue
        disabled.append(rel)
    return sorted(disabled)


def _find_missing_manifests(addons_roots: list[Path], allowlist: set[str]) -> list[str]:
    missing = []
    for root in addons_roots:
        if not root.exists():
            continue
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            if entry.name.startswith(".") or entry.name in IGNORE_DIRS:
                continue
            manifest = entry / "__manifest__.py"
            if manifest.exists():
                continue
            rel = _to_posix(entry.relative_to(ROOT))
            if rel in allowlist:
                continue
            missing.append(rel)
    return sorted(missing)


def _load_manifest(path: Path) -> dict:
    try:
        data = ast.literal_eval(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _collect_manifest_refs(manifest: dict) -> set[str]:
    refs: set[str] = set()

    def add(value):
        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)
        elif isinstance(value, dict):
            for item in value.values():
                add(item)
        elif isinstance(value, str):
            refs.add(_normalize_rel(value))

    add(manifest.get("data", []))
    add(manifest.get("demo", []))
    add(manifest.get("qweb", []))
    add(manifest.get("assets", {}))
    return refs


def _find_manifest_coverage_gaps(addons_roots: list[Path], allowlist: set[str]) -> list[str]:
    gaps = []
    for root in addons_roots:
        if not root.exists():
            continue
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / "__manifest__.py"
            if not manifest_path.exists():
                continue
            refs = _collect_manifest_refs(_load_manifest(manifest_path))
            for subdir in CANDIDATE_DIRS:
                base = entry / subdir
                if not base.exists():
                    continue
                for file_path in base.rglob("*"):
                    if not file_path.is_file():
                        continue
                    if file_path.suffix not in CANDIDATE_SUFFIXES:
                        continue
                    rel_module = _normalize_rel(_to_posix(file_path.relative_to(entry)))
                    if rel_module in refs:
                        continue
                    rel_root = _to_posix(file_path.relative_to(ROOT))
                    if rel_root in allowlist:
                        continue
                    gaps.append(rel_root)
    return sorted(set(gaps))


def main() -> int:
    parser = argparse.ArgumentParser(description="Odoo addon hygiene checks")
    parser.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST))
    parser.add_argument("--odoo-conf", default=str(DEFAULT_ODOO_CONF))
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE))
    parser.add_argument(
        "--addons-path",
        default="",
        help="Comma-separated host paths to addons roots (overrides odoo.conf/compose)",
    )
    args = parser.parse_args()

    allowlist = _load_allowlist(Path(args.allowlist))
    disabled = _find_disabled_files(allowlist["disabled"])

    if args.addons_path:
        addons_roots = [
            Path(path.strip())
            for path in args.addons_path.split(",")
            if path.strip()
        ]
    else:
        addons_paths = _parse_addons_path(Path(args.odoo_conf))
        volume_map = _parse_volume_mappings(Path(args.compose_file))
        addons_roots = _resolve_addons_roots(addons_paths, volume_map)

    missing_manifests = _find_missing_manifests(
        addons_roots, allowlist["missing_manifest"]
    )
    coverage_gaps = _find_manifest_coverage_gaps(
        addons_roots, allowlist["manifest_coverage"]
    )

    problems = []
    if disabled:
        problems.append(("DISABLED files", disabled))
    if missing_manifests:
        problems.append(("Missing __manifest__.py", missing_manifests))
    if coverage_gaps:
        problems.append(("Manifest coverage gaps", coverage_gaps))

    if not problems:
        print("odoo_ci_checks: no issues found")
        return 0

    print("odoo_ci_checks: issues found")
    for title, items in problems:
        print(f"\n{title}:")
        for item in items:
            print(f"  - {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
