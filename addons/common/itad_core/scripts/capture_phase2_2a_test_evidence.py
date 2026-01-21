#!/usr/bin/env python3
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root(start_path: Path) -> Path:
    for parent in [start_path] + list(start_path.parents):
        compose_file = parent / "docker" / "odoo18" / "docker-compose.odoo18.yml"
        if compose_file.exists():
            return parent
    raise FileNotFoundError("Unable to locate repo root (missing docker/odoo18/docker-compose.odoo18.yml).")


def _ensure_docker_compose():
    if not shutil.which("docker"):
        raise RuntimeError("docker executable not found in PATH.")
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "docker compose is not available. "
            f"stdout: {result.stdout.strip()} stderr: {result.stderr.strip()}"
        )


def _run_and_capture(cmd, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, text=True, check=False)
    return proc.returncode


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_sha256(path: Path, sha256_hex: str):
    sha_path = path.with_suffix(path.suffix + ".sha256")
    sha_path.write_text(f"{sha256_hex}  {path.name}\n", encoding="utf-8")


def main() -> int:
    try:
        _ensure_docker_compose()
        repo_root = _find_repo_root(Path(__file__).resolve())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    evidence_dir = repo_root / "docs" / "evidence" / "phase2.2a"
    compose_file = repo_root / "docker" / "odoo18" / "docker-compose.odoo18.yml"

    odoo_cmd = [
        "docker",
        "compose",
        "-p",
        "odoo18",
        "-f",
        str(compose_file),
        "run",
        "--rm",
        "-T",
        "odoo18",
        "odoo",
        "--test-enable",
        "-d",
        "odoo18_db",
        "-c",
        "/etc/odoo/odoo.conf",
        "-u",
        "itad_core",
        "--stop-after-init",
        "--no-http",
    ]
    odoo_log = evidence_dir / "odoo_test_run.log"
    odoo_exit = _run_and_capture(odoo_cmd, odoo_log)

    psql_cmd = [
        "docker",
        "compose",
        "-p",
        "odoo18",
        "-f",
        str(compose_file),
        "exec",
        "-T",
        "db18",
        "psql",
        "-U",
        "odoo",
        "-d",
        "postgres",
        "-c",
        "\\l+",
    ]
    psql_log = evidence_dir / "psql_list_dbs.txt"
    psql_exit = _run_and_capture(psql_cmd, psql_log)

    odoo_sha = _sha256_file(odoo_log)
    psql_sha = _sha256_file(psql_log)
    _write_sha256(odoo_log, odoo_sha)
    _write_sha256(psql_log, psql_sha)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commands": {
            "odoo_test": " ".join(odoo_cmd),
            "psql_list_dbs": " ".join(psql_cmd),
        },
        "exit_code": odoo_exit,
        "psql_exit_code": psql_exit,
        "sha256": {
            "odoo_test_run.log": odoo_sha,
            "psql_list_dbs.txt": psql_sha,
        },
        "compose_file": "docker/odoo18/docker-compose.odoo18.yml",
    }
    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return odoo_exit if odoo_exit != 0 else psql_exit


if __name__ == "__main__":
    sys.exit(main())
