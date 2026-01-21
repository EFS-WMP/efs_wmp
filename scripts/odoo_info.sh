#!/usr/bin/env bash
set -euo pipefail

ODOO_SRC="${ODOO_SRC:-$HOME/odoo18}"

echo "python: $(command -v python || true)"
echo "venv: ${VIRTUAL_ENV:-<none>}"

if [[ -f "$ODOO_SRC/odoo-bin" ]]; then
  echo "odoo-bin: $ODOO_SRC/odoo-bin"
  python "$ODOO_SRC/odoo-bin" --version || true
  if command -v git >/dev/null 2>&1 && [[ -d "$ODOO_SRC/.git" ]]; then
    (cd "$ODOO_SRC" && echo "git branch: $(git rev-parse --abbrev-ref HEAD)" && echo "git commit: $(git rev-parse --short HEAD)")
  fi
else
  echo "odoo-bin: NOT FOUND at $ODOO_SRC"
fi

python - <<'PY'
import sys
try:
    import odoo
    print("odoo imported from:", odoo.__file__)
except Exception as e:
    print("odoo import failed:", e)
print("sys.path[0]:", sys.path[0])
print("python:", sys.executable)
PY
