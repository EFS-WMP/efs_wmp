#!/usr/bin/env python3
# File: scripts/migrate_phase2.1_to_2.2.py
"""
Repo-root wrapper for Phase 2.1 -> 2.2 migration.

This script is a thin wrapper that delegates to the addon-mounted script.
Run inside Odoo container for proper environment access.
"""

import sys
import os

# Add addon path to Python path
addon_path = "/mnt/extra-addons-custom/itad_core"
if os.path.exists(addon_path):
    sys.path.insert(0, addon_path)

# Import and run migration from addon
try:
    from scripts.migrate_phase2_1_to_2_2 import main
    main()
except ImportError as e:
    print(f"ERROR: Could not import migration script: {e}")
    print("Ensure this script is run inside the Odoo container.")
    sys.exit(1)
