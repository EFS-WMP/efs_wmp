import re
from pathlib import Path


def main():
    index_path = Path("docs/phase0/PHASE_0_EVIDENCE_INDEX.md")
    if not index_path.exists():
        raise SystemExit("Evidence index not found.")
    pattern = re.compile(r"`([^`]+)`")
    missing = set()
    for line in index_path.read_text().splitlines():
        for match in pattern.findall(line):
            path = Path(match)
            if path.is_absolute():
                continue
            if ".." in match:
                continue
            if not path.exists():
                missing.add(match)
    if missing:
        for path in sorted(missing):
            print("Missing referenced path:", path)
        raise SystemExit(1)
    print("All referenced paths exist.")


if __name__ == "__main__":
    main()
