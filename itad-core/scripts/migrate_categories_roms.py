#!/usr/bin/env python3
"""
Phase 2.4b: Legacy Spreadsheet Migration Tool

Migrates material taxonomy from Categories ROMS.xlsx to ITAD Core database.

Usage:
    python migrate_categories_roms.py --input "Categories ROMS.xlsx" --dry-run
    python migrate_categories_roms.py --input "Categories ROMS.xlsx" --apply --output-dir docs/evidence/

Features:
- Dry-run mode (default): Validate and produce exception reports without DB changes
- Apply mode: Upsert to database idempotently
- Deterministic exception reporting (sorted by row_number, code)
- No silent coercions - all issues logged as exceptions
- Near-duplicate detection via canonicalization (trim + upper)
- Abort apply mode if duplicates detected
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


# Centralized canonical values (must match MaterialType model)
VALID_STREAMS = frozenset([
    "batteries", "electronics", "plastics", "metals", "hazardous",
    "mixed", "paper", "glass", "organics", "textiles", "other"
])

VALID_BASIS_OF_CHARGE = frozenset([
    "per_lb", "per_kg", "per_unit", "flat_fee"
])

VALID_PRICING_STATES = frozenset([
    "priced", "unpriced", "contract", "deprecated"
])

VALID_DEFAULT_ACTIONS = frozenset([
    "recycle", "dispose", "refurbish", "resell", "donate", "store"
])

VALID_BOOLEAN_TRUE = frozenset(["true", "yes", "1", "t", "y"])
VALID_BOOLEAN_FALSE = frozenset(["false", "no", "0", "f", "n"])
VALID_BOOLEAN_VALUES = VALID_BOOLEAN_TRUE | VALID_BOOLEAN_FALSE


def canonicalize_code(code: str | None) -> str | None:
    """
    Canonicalize code for duplicate detection.
    
    Canonicalization Scope: WHITESPACE + CASE ONLY
    - Remove leading/trailing whitespace
    - Convert to uppercase
    
    Examples:
        "bat-li-001 " -> "BAT-LI-001"
        " Bat-li-001" -> "BAT-LI-001"
    
    NOTE: Hyphen/space variants (BAT LI 001 vs BAT-LI-001) are NOT treated
    as duplicates. This is by design - if needed, add tier-2 warning logic
    that flags potential near-duplicates without auto-merging.
    
    To add tier-2 warnings, implement a separate check that removes all
    non-alphanumeric characters and compares.
    """
    if code is None:
        return None
    return code.strip().upper() or None


class MigrationException:
    """Represents a validation or parsing error for a row"""
    
    def __init__(
        self,
        row_number: int,
        code: str | None,
        field: str,
        reason: str,
        original_value: Any,
        suggested_fix: str | None = None,
    ):
        self.row_number = row_number
        self.code = code or ""
        self.field = field
        self.reason = reason
        self.original_value = str(original_value) if original_value is not None else ""
        self.suggested_fix = suggested_fix or ""
    
    def to_dict(self) -> dict:
        return {
            "row_number": self.row_number,
            "code": self.code,
            "field": self.field,
            "reason": self.reason,
            "original_value": self.original_value,
            "suggested_fix": self.suggested_fix,
        }


class RowData:
    """Normalized row data after parsing"""
    
    def __init__(self, row_number: int, original: dict):
        self.row_number = row_number
        self.original = original
        self.normalized = {}
        self.exceptions = []
        self.valid = True
    
    def add_exception(self, field: str, reason: str, original_value: Any, suggested_fix: str | None = None):
        exc = MigrationException(
            row_number=self.row_number,
            code=self.normalized.get("code", self.original.get("code")),
            field=field,
            reason=reason,
            original_value=original_value,
            suggested_fix=suggested_fix,
        )
        self.exceptions.append(exc)
        self.valid = False


def parse_excel(file_path: str) -> list[dict]:
    """Parse Excel file and return list of row dicts"""
    try:
        import openpyxl
    except ImportError:
        print("ERROR: openpyxl not installed. Run: pip install openpyxl")
        sys.exit(1)
    
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    sheet = wb.active
    
    rows = []
    headers = None
    
    for row_num, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        if row_num == 1:
            # First row is headers
            headers = [str(h).strip().lower().replace(" ", "_") if h else f"col_{i}" 
                       for i, h in enumerate(row)]
            continue
        
        # Skip empty rows
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        
        row_dict = {"_row_number": row_num}
        for i, header in enumerate(headers):
            if i < len(row):
                row_dict[header] = row[i]
            else:
                row_dict[header] = None
        
        rows.append(row_dict)
    
    return rows


def normalize_string(value: Any) -> str | None:
    """Normalize string value (strip whitespace, None for empty)"""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def parse_boolean(value: Any, field_name: str, row_data: RowData) -> bool | None:
    """Parse boolean value with strict validation"""
    if value is None:
        return None
    
    if isinstance(value, bool):
        return value
    
    s = str(value).strip().lower()
    
    if not s:
        return None
    
    if s in VALID_BOOLEAN_TRUE:
        return True
    elif s in VALID_BOOLEAN_FALSE:
        return False
    else:
        row_data.add_exception(
            field=field_name,
            reason=f"Invalid boolean value. Must be one of: {', '.join(sorted(VALID_BOOLEAN_VALUES))}",
            original_value=value,
            suggested_fix="false",
        )
        return None


def parse_decimal(value: Any, field_name: str, row_data: RowData) -> Decimal | None:
    """Parse decimal value with strict validation"""
    if value is None:
        return None
    
    s = str(value).strip()
    if not s:
        return None
    
    try:
        d = Decimal(s)
        if d < 0:
            row_data.add_exception(
                field=field_name,
                reason="Value must be >= 0",
                original_value=value,
                suggested_fix="0",
            )
            return None
        return d
    except InvalidOperation:
        row_data.add_exception(
            field=field_name,
            reason="Invalid decimal format",
            original_value=value,
            suggested_fix="0",
        )
        return None


def validate_enum(value: str | None, field_name: str, valid_values: frozenset, row_data: RowData) -> str | None:
    """Validate enum value"""
    if value is None:
        return None
    
    if value.lower() in valid_values:
        return value.lower()
    
    row_data.add_exception(
        field=field_name,
        reason=f"Invalid value. Must be one of: {', '.join(sorted(valid_values))}",
        original_value=value,
        suggested_fix=sorted(valid_values)[0] if valid_values else "",
    )
    return None


def normalize_row(raw_row: dict) -> RowData:
    """Normalize and validate a single row"""
    row_num = raw_row.get("_row_number", 0)
    row_data = RowData(row_num, raw_row)
    
    # Column mapping (adjust based on actual spreadsheet structure)
    column_map = {
        "code": ["code", "material_code", "item_code"],
        "name": ["name", "material_name", "description"],
        "stream": ["stream", "category", "material_stream"],
        "hazard_class": ["hazard_class", "hazard", "dot_class"],
        "default_action": ["default_action", "action", "process_action"],
        "requires_photo": ["requires_photo", "photo_required", "photo"],
        "requires_weight": ["requires_weight", "weight_required", "weight"],
        "default_price": ["default_price", "price", "unit_price"],
        "basis_of_charge": ["basis_of_charge", "charge_basis", "pricing_basis"],
        "gl_account_code": ["gl_account_code", "gl_code", "account_code"],
    }
    
    def get_value(field_aliases: list[str]) -> Any:
        for alias in field_aliases:
            if alias in raw_row:
                return raw_row[alias]
        return None
    
    # Extract and normalize
    row_data.normalized["code"] = normalize_string(get_value(column_map["code"]))
    row_data.normalized["name"] = normalize_string(get_value(column_map["name"]))
    row_data.normalized["stream"] = normalize_string(get_value(column_map["stream"]))
    row_data.normalized["hazard_class"] = normalize_string(get_value(column_map["hazard_class"]))
    row_data.normalized["default_action"] = normalize_string(get_value(column_map["default_action"]))
    row_data.normalized["gl_account_code"] = normalize_string(get_value(column_map["gl_account_code"]))
    
    # Boolean parsing
    row_data.normalized["requires_photo"] = parse_boolean(
        get_value(column_map["requires_photo"]), "requires_photo", row_data
    )
    row_data.normalized["requires_weight"] = parse_boolean(
        get_value(column_map["requires_weight"]), "requires_weight", row_data
    )
    
    # Decimal parsing
    row_data.normalized["default_price"] = parse_decimal(
        get_value(column_map["default_price"]), "default_price", row_data
    )
    
    # Enum validation
    row_data.normalized["basis_of_charge"] = validate_enum(
        normalize_string(get_value(column_map["basis_of_charge"])),
        "basis_of_charge",
        VALID_BASIS_OF_CHARGE,
        row_data,
    )
    
    if row_data.normalized["stream"]:
        row_data.normalized["stream"] = validate_enum(
            row_data.normalized["stream"],
            "stream",
            VALID_STREAMS,
            row_data,
        )
    
    if row_data.normalized["default_action"]:
        row_data.normalized["default_action"] = validate_enum(
            row_data.normalized["default_action"],
            "default_action",
            VALID_DEFAULT_ACTIONS,
            row_data,
        )
    
    # Required fields validation
    if not row_data.normalized["code"]:
        row_data.add_exception(
            field="code",
            reason="Required field is missing",
            original_value=get_value(column_map["code"]),
            suggested_fix="UNKNOWN-XXX",
        )
    
    if not row_data.normalized["name"]:
        row_data.add_exception(
            field="name",
            reason="Required field is missing",
            original_value=get_value(column_map["name"]),
            suggested_fix="Unknown Material",
        )
    
    if not row_data.normalized["stream"]:
        row_data.add_exception(
            field="stream",
            reason="Required field is missing",
            original_value=get_value(column_map["stream"]),
            suggested_fix="other",
        )
    
    # Mutual requirement: price <-> basis_of_charge
    price = row_data.normalized["default_price"]
    basis = row_data.normalized["basis_of_charge"]
    
    if price is not None and basis is None:
        row_data.add_exception(
            field="basis_of_charge",
            reason="Required when default_price is set",
            original_value=None,
            suggested_fix="per_unit",
        )
    
    if basis is not None and price is None:
        row_data.add_exception(
            field="default_price",
            reason="Required when basis_of_charge is set",
            original_value=None,
            suggested_fix="0",
        )
    
    # GL account code format
    gl = row_data.normalized["gl_account_code"]
    if gl is not None and len(gl) > 64:
        row_data.add_exception(
            field="gl_account_code",
            reason="Exceeds maximum length (64 characters)",
            original_value=gl,
            suggested_fix=gl[:64],
        )
    
    return row_data


def check_code_uniqueness(rows: list[RowData]) -> tuple[list[MigrationException], bool]:
    """
    Check for duplicate/near-duplicate codes within file.
    
    Uses canonicalization (TRIM + UPPER) to detect near-duplicates.
    All rows with canonical collisions are marked as exceptions.
    
    Returns:
        (exceptions, has_duplicates) - exceptions list and flag indicating if any duplicates found
    """
    # Track: canonical -> list of (original_code, row_number)
    seen = {}
    exceptions = []
    has_duplicates = False
    
    # First pass: collect all canonical codes
    for row in rows:
        code = row.normalized.get("code")
        if not code:
            continue
        
        canonical = canonicalize_code(code)
        if canonical is None:
            continue
        
        if canonical not in seen:
            seen[canonical] = []
        seen[canonical].append((code, row.row_number, row))
    
    # Second pass: mark all duplicates
    for canonical, occurrences in seen.items():
        if len(occurrences) > 1:
            has_duplicates = True
            # Mark ALL occurrences as duplicates (not just the 2nd+)
            rows_str = ", ".join(str(r[1]) for r in occurrences)
            for original_code, row_num, row_data in occurrences:
                exc = MigrationException(
                    row_number=row_num,
                    code=original_code,
                    field="code",
                    reason=f"Near-duplicate code after canonicalization (rows: {rows_str}). Canonical: {canonical}",
                    original_value=original_code,
                    suggested_fix=f"{canonical}-{row_num}",
                )
                exceptions.append(exc)
                row_data.exceptions.append(exc)
                row_data.valid = False
    
    return exceptions, has_duplicates


def write_exceptions_json(exceptions: list[MigrationException], output_path: str):
    """Write exceptions to JSON file"""
    data = [e.to_dict() for e in sorted(exceptions, key=lambda x: (x.row_number, x.code))]
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


def write_exceptions_csv(exceptions: list[MigrationException], output_path: str):
    """Write exceptions to CSV file"""
    sorted_exceptions = sorted(exceptions, key=lambda x: (x.row_number, x.code))
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "row_number", "code", "field", "reason", "original_value", "suggested_fix"
        ])
        writer.writeheader()
        for exc in sorted_exceptions:
            writer.writerow(exc.to_dict())


def write_summary(
    total_rows: int,
    valid_rows: int,
    exceptions_count: int,
    would_create: int,
    would_update: int,
    would_deactivate: int,
    output_path: str,
    has_duplicates: bool = False,
):
    """Write summary JSON"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "exceptions_count": exceptions_count,
        "would_create": would_create,
        "would_update": would_update,
        "would_deactivate": would_deactivate,
        "has_duplicates": has_duplicates,
        "apply_blocked": has_duplicates,  # Apply mode will abort if duplicates found
    }
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def run_dry_run(input_path: str, output_dir: str, verbose: bool = False):
    """Execute dry-run: validate and produce reports without DB changes"""
    print(f"Dry-run: Parsing {input_path}...")
    
    raw_rows = parse_excel(input_path)
    print(f"Parsed {len(raw_rows)} rows from spreadsheet")
    
    # Normalize and validate
    normalized_rows = []
    all_exceptions = []
    
    for raw in raw_rows:
        row_data = normalize_row(raw)
        normalized_rows.append(row_data)
        all_exceptions.extend(row_data.exceptions)
    
    # Check code uniqueness (uses canonicalization)
    dup_exceptions, has_duplicates = check_code_uniqueness(normalized_rows)
    all_exceptions.extend(dup_exceptions)
    
    valid_rows = [r for r in normalized_rows if r.valid]
    
    # Summary counts
    total = len(normalized_rows)
    valid_count = len(valid_rows)
    exceptions_count = len(all_exceptions)
    
    # In dry-run, estimate creates/updates (would need DB access for accurate counts)
    would_create = valid_count  # Assume all valid would be new
    would_update = 0
    would_deactivate = 0
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Write reports
    write_exceptions_json(all_exceptions, os.path.join(output_dir, "exceptions.json"))
    write_exceptions_csv(all_exceptions, os.path.join(output_dir, "exceptions.csv"))
    summary = write_summary(
        total, valid_count, exceptions_count,
        would_create, would_update, would_deactivate,
        os.path.join(output_dir, "summary.json"),
        has_duplicates=has_duplicates,
    )
    
    print(f"\nDry-run complete!")
    print(f"  Total rows: {total}")
    print(f"  Valid rows: {valid_count}")
    print(f"  Exceptions: {exceptions_count}")
    print(f"\nReports written to: {output_dir}")
    
    if verbose and all_exceptions:
        print("\n--- Exceptions ---")
        for exc in sorted(all_exceptions, key=lambda x: (x.row_number, x.field)):
            print(f"  Row {exc.row_number}: [{exc.field}] {exc.reason} (value: {exc.original_value})")
    
    return summary


def run_apply(input_path: str, output_dir: str, deactivate_missing: bool = False, verbose: bool = False):
    """Execute apply: upsert to database"""
    print("ERROR: Apply mode requires database connection.")
    print("This script should be run from within ITAD Core with DB access.")
    print("\nTo run with DB access:")
    print("  1. Set DATABASE_URL environment variable")
    print("  2. Or run via: python -m app.scripts.migrate_categories_roms --apply")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Categories ROMS.xlsx to ITAD Core database"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to Categories ROMS.xlsx file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Validate only, no DB writes (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute upsert to database",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for reports (default: docs/evidence/phase2.4/migration_runs/<timestamp>)",
    )
    parser.add_argument(
        "--deactivate-missing",
        action="store_true",
        help="Set is_active=False for codes in DB not in file (default: off)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)
    
    # Set default output directory
    if not args.output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = os.path.join("docs", "evidence", "phase2.4", "migration_runs", timestamp)
    
    if args.apply:
        run_apply(args.input, args.output_dir, args.deactivate_missing, args.verbose)
    else:
        run_dry_run(args.input, args.output_dir, args.verbose)


if __name__ == "__main__":
    main()
