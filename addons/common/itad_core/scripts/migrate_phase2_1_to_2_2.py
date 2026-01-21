#!/usr/bin/env python3
# File: itad_core/scripts/migrate_phase2_1_to_2_2.py
"""
Phase 2.1 -> 2.2 Migration Script

Backfills idempotency keys for legacy receipt exception records to enable retry.
"""

import argparse
import sys
import uuid
from datetime import datetime, timedelta


def migrate_legacy_receipts(env, dry_run=True, limit=None, since_days=None, verbose=False):
    """
    Migrate legacy receipt exception records to Phase 2.2 retry-capable state.
    
    Args:
        env: Odoo environment
        dry_run: If True, no changes are written
        limit: Max records to process
        since_days: Only process records updated within N days
        verbose: Print detailed progress
        
    Returns:
        dict: Migration report with counts
    """
    # Migration namespace (constant)
    NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000222")
    
    # Initialize report
    report = {
        "scanned": 0,
        "eligible": 0,
        "fixed": 0,
        "skipped": 0,
        "errors": 0,
        "sample_fixed": [],
        "sample_skipped": [],
        "sample_errors": [],
    }
    
    # Build domain for legacy records
    domain = []
    
    # Optional: filter by recent updates
    if since_days:
        cutoff = datetime.now() - timedelta(days=since_days)
        domain.append(("write_date", ">=", cutoff))
    
    # Find all orders with receipt state
    FsmOrder = env["fsm.order"].sudo()
    all_orders = FsmOrder.search(domain, limit=limit)
    report["scanned"] = len(all_orders)
    
    if verbose:
        print(f"Scanned {report['scanned']} fsm.order records")
    
    for order in all_orders:
        try:
            env.cr.execute(
                """
                SELECT itad_receipt_idempotency_key,
                       itad_receipt_state,
                       itad_bol_id,
                       itad_manifest_no
                  FROM fsm_order
                 WHERE id = %s
                """,
                [order.id],
            )
            (
                db_idempotency_key,
                db_receipt_state,
                db_bol_id,
                db_manifest_no,
            ) = env.cr.fetchone()

            # Determine if eligible for migration
            # Eligible: exception state OR missing idempotency key (and has receipt data)
            is_exception = db_receipt_state == "exception"
            has_key = bool(db_idempotency_key)
            has_bol = bool(db_bol_id)
            has_manifest = bool(db_manifest_no)
            
            # Skip if already has key
            if has_key:
                continue
            
            # Skip if successfully received (no need for retry)
            if db_receipt_state == "received":
                continue
            
            # Eligible if exception OR pending with receipt data
            if not (is_exception or (db_receipt_state == "pending" and has_bol)):
                continue
            
            # Must have stable identifiers for deterministic key
            if not (has_bol and has_manifest):
                report["skipped"] += 1
                if len(report["sample_skipped"]) < 5:
                    report["sample_skipped"].append({
                        "id": order.id,
                        "name": order.name,
                        "reason": "Missing BOL or manifest number",
                    })
                continue
            
            report["eligible"] += 1
            
            # Generate deterministic idempotency key
            name_str = f"fsm.order:{order.id}:{db_bol_id}:{db_manifest_no}"
            idempotency_key = f"receipt-{uuid.uuid5(NAMESPACE, name_str)}"
            
            if not dry_run:
                env.cr.execute(
                    """
                    UPDATE fsm_order
                       SET itad_receipt_idempotency_key = %s
                     WHERE id = %s
                    """,
                    [idempotency_key, order.id],
                )
                report["fixed"] += 1
                if len(report["sample_fixed"]) < 5:
                    report["sample_fixed"].append({
                        "id": order.id,
                        "name": order.name,
                        "bol_id": db_bol_id,
                        "state": db_receipt_state,
                        "key": idempotency_key,
                    })
            
            if verbose and report["fixed"] % 10 == 0:
                print(f"  Processed {report['fixed']} records...")
                
        except Exception as exc:
            report["errors"] += 1
            if len(report["sample_errors"]) < 5:
                report["sample_errors"].append({
                    "id": order.id,
                    "name": order.name,
                    "error": str(exc),
                })
            if verbose:
                print(f"  ERROR processing order {order.id}: {exc}")
    
    return report


def print_report(report, dry_run):
    """Print migration report"""
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"\n{'='*60}")
    print(f"Phase 2.1 -> 2.2 Migration Report ({mode})")
    print(f"{'='*60}")
    print(f"Scanned:  {report['scanned']}")
    print(f"Eligible: {report['eligible']}")
    print(f"Fixed:    {report['fixed']}")
    print(f"Skipped:  {report['skipped']}")
    print(f"Errors:   {report['errors']}")
    
    if report["sample_fixed"]:
        print(f"\nSample Fixed Records:")
        for sample in report["sample_fixed"]:
            print(f"  - Order {sample['id']} ({sample['name']}): {sample['state']}")
            print(f"    BOL: {sample['bol_id']}")
            print(f"    Key: {sample['key']}")
    
    if report["sample_skipped"]:
        print(f"\nSample Skipped Records:")
        for sample in report["sample_skipped"]:
            print(f"  - Order {sample['id']} ({sample['name']}): {sample['reason']}")
    
    if report["sample_errors"]:
        print(f"\nSample Errors:")
        for sample in report["sample_errors"]:
            print(f"  - Order {sample['id']} ({sample['name']}): {sample['error']}")
    
    print(f"{'='*60}\n")


def main():
    """Main entry point for CLI execution"""
    parser = argparse.ArgumentParser(
        description="Migrate Phase 2.1 receipt exceptions to Phase 2.2 retry-capable state"
    )
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Dry-run mode (default)")
    parser.add_argument("--apply", action="store_true",
                       help="Apply changes (overrides --dry-run)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Max records to process")
    parser.add_argument("--since-days", type=int, default=None,
                       help="Only process records updated within N days")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Determine mode
    dry_run = not args.apply
    
    # Import Odoo environment
    try:
        import odoo
        from odoo import api, SUPERUSER_ID
        from odoo.tools import config
    except ImportError:
        print("ERROR: Must run inside Odoo environment")
        sys.exit(1)
    
    # Get database name from config
    db_name = config["db_name"]
    if not db_name:
        print("ERROR: No database configured")
        sys.exit(1)
    
    # Create environment
    with odoo.api.Environment.manage():
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            
            # Run migration
            report = migrate_legacy_receipts(
                env,
                dry_run=dry_run,
                limit=args.limit,
                since_days=args.since_days,
                verbose=args.verbose
            )
            
            # Print report
            print_report(report, dry_run)
            
            # Commit if apply mode
            if not dry_run:
                cr.commit()
                print("Changes committed.")
            else:
                print("Dry-run complete. No changes made.")
                print("Run with --apply to execute migration.")


if __name__ == "__main__":
    main()
