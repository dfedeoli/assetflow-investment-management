#!/usr/bin/env python3
"""
Backfill Contributions Utility

This script backfills the contributions table with missing contribution records
for initial positions (positions that have no prior history).

Use case:
- When positions were added before the contributions tracking feature was implemented
- To populate contribution history for existing assets
- After importing historical data that lacks contribution records

The script is idempotent - it's safe to run multiple times as it skips positions
that already have contribution records.

Usage:
    python utils/backfill_contributions.py [db_path]

Examples:
    python utils/backfill_contributions.py
    python utils/backfill_contributions.py investment_data.db
    python utils/backfill_contributions.py /path/to/custom.db
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional


def connect_db(db_path: str) -> sqlite3.Connection:
    """Connect to SQLite database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def find_initial_positions_without_contributions(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """
    Find positions that are "initial" (no prior position for that asset)
    and don't have a corresponding contribution record.

    Returns list of position rows that need contribution records.
    """
    cursor = conn.cursor()

    # Find all positions
    cursor.execute("""
        SELECT
            p.id,
            p.name,
            p.value,
            p.invested_value,
            p.date,
            p.custom_label
        FROM positions p
        ORDER BY p.name, p.date
    """)

    all_positions = cursor.fetchall()

    # Group by asset name to find initial positions
    positions_by_asset = {}
    for pos in all_positions:
        asset_name = pos['name']
        if asset_name not in positions_by_asset:
            positions_by_asset[asset_name] = []
        positions_by_asset[asset_name].append(pos)

    # Find initial positions (earliest date for each asset)
    initial_positions = []
    for asset_name, positions in positions_by_asset.items():
        # Sort by date and get the first position
        sorted_positions = sorted(positions, key=lambda p: p['date'])
        initial_position = sorted_positions[0]
        initial_positions.append(initial_position)

    # Filter out positions that already have contribution records
    positions_needing_backfill = []

    for pos in initial_positions:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM contributions
            WHERE position_id = ?
        """, (pos['id'],))

        result = cursor.fetchone()
        if result['count'] == 0:
            # No contribution record exists for this position
            positions_needing_backfill.append(pos)

    return positions_needing_backfill


def create_contribution_record(
    conn: sqlite3.Connection,
    position: sqlite3.Row
) -> int:
    """
    Create a contribution record for an initial position.

    Returns the contribution ID.
    """
    cursor = conn.cursor()

    # Use invested_value if available, otherwise use value
    contribution_amount = position['invested_value'] if position['invested_value'] else position['value']

    cursor.execute("""
        INSERT INTO contributions (
            asset_name,
            contribution_amount,
            contribution_date,
            previous_value,
            new_total_value,
            notes,
            position_id,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        position['name'],
        contribution_amount,
        position['date'],
        0.0,  # Initial contribution has no previous value
        position['value'],
        "Initial contribution (backfilled)",
        position['id'],
        datetime.now().isoformat()
    ))

    conn.commit()
    return cursor.lastrowid


def backfill_contributions(db_path: str, verbose: bool = True) -> Tuple[int, float]:
    """
    Backfill missing contribution records for initial positions.

    Returns:
        Tuple of (number of contributions created, total amount backfilled)
    """
    conn = connect_db(db_path)

    try:
        # Find positions needing backfill
        positions = find_initial_positions_without_contributions(conn)

        if not positions:
            if verbose:
                print("✓ No positions need backfilling. All initial positions have contribution records.")
            return 0, 0.0

        if verbose:
            print(f"\nBackfilling contributions from initial positions...")
            print(f"Found {len(positions)} initial positions without contribution records.\n")

        # Create contribution records
        total_amount = 0.0
        created_count = 0

        if verbose:
            print("Backfilling contributions:")

        for pos in positions:
            contribution_amount = pos['invested_value'] if pos['invested_value'] else pos['value']

            contrib_id = create_contribution_record(conn, pos)

            total_amount += contribution_amount
            created_count += 1

            if verbose:
                # Format date
                date_obj = datetime.fromisoformat(pos['date'])
                date_str = date_obj.strftime('%Y-%m-%d')

                # Show custom label if available
                label_info = f" [{pos['custom_label']}]" if pos['custom_label'] else ""

                print(f"  ✓ {pos['name']}{label_info}: R$ {contribution_amount:,.2f} ({date_str})")

        if verbose:
            print(f"\n{'='*80}")
            print(f"Total backfilled: R$ {total_amount:,.2f} across {created_count} contributions.")
            print(f"{'='*80}\n")

        return created_count, total_amount

    finally:
        conn.close()


def main():
    """Main entry point for CLI usage"""
    # Determine database path
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Default to investment_data.db in current directory
        db_path = "investment_data.db"

    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Error: Database not found at '{db_path}'")
        print("\nUsage: python utils/backfill_contributions.py [db_path]")
        sys.exit(1)

    print(f"Database: {db_path}")
    print("="*80)

    try:
        count, total = backfill_contributions(db_path, verbose=True)

        if count > 0:
            print("✓ Backfill completed successfully!")
            print(f"\nYour PGBL planning and contribution history will now show these {count} contributions.")

    except Exception as e:
        print(f"\n❌ Error during backfill: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
