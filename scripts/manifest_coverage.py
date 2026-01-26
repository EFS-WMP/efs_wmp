#!/usr/bin/env python3
import ast
from pathlib import Path
import sys


MANIFEST_KEYS = ("data", "demo", "qweb", "assets")


def load_manifest(manifest_path: Path) -> set[str]:
    """
    Odoo __manifest__.py is a Python dict literal.
    We parse it via ast.literal_eval to avoid executing code.
    """
    txt = manifest_path.read_text(encoding="utf-8")
    data = ast.literal_eval(txt)

    declared: set[str] = set()

    for k in MANIFEST_KEYS:
        v = data.get(k)
        if isinstance(v, list):
            declared |= {str(x) for x in v}
        elif isinstance(v, dict):  # assets bundles dict
            for _, lst in v.items():
                if isinstance(lst, list):
                    declared |= {str(x) for x in lst}

    return declared


def iter_candidate_files(module_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for folder in ("views", "data", "security", "report"):
        p = module_dir / folder
        if not p.exists():
            continue
        candidates += list(p.rglob("*.xml"))
        candidates += list(p.rglob("*.csv"))
    return candidates


def main() -> int:
    repo_root = Path(".").resolve()
    manifests = list(repo_root.rglob("__manifest__.py"))

    if not manifests:
        print("No __manifest__.py files found.")
        return 0

    failed = False

    for mf in manifests:
        mod_dir = mf.parent
        declared = load_manifest(mf)
        candidates = iter_candidate_files(mod_dir)

        missing: list[str] = []
        for f in candidates:
            rel = f.relative_to(mod_dir).as_posix()
            if rel not in declared:
                missing.append(rel)

        if missing:
            failed = True
            print(f"\n[FAIL] {mod_dir.name}: files not referenced in __manifest__.py")
            for m in missing:
                print(f"  - {m}")

    if failed:
        print("\nManifest coverage failed.")
        return 1

    print("Manifest coverage OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
