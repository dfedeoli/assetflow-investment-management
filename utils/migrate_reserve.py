"""
Migration script to add reserve_amount column to target_allocations table
"""

import sqlite3
import sys
from pathlib import Path


def migrate_add_reserve_column(db_path: str = "investment_data.db"):
    """Add reserve_amount column to target_allocations table"""

    print(f"Migrating database: {db_path}")

    if not Path(db_path).exists():
        print(f"Error: Database file '{db_path}' not found")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if reserve_amount column already exists
        cursor.execute("PRAGMA table_info(target_allocations)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'reserve_amount' in columns:
            print("✓ reserve_amount column already exists")
            return True

        # Add reserve_amount column
        print("Adding reserve_amount column to target_allocations table...")
        cursor.execute("""
            ALTER TABLE target_allocations
            ADD COLUMN reserve_amount REAL
        """)

        conn.commit()
        print("✓ Successfully added reserve_amount column")

        return True

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "investment_data.db"

    print("=" * 60)
    print("AssetFlow - Reserve Amount Migration")
    print("=" * 60)
    print()

    success = migrate_add_reserve_column(db_path)

    print()
    if success:
        print("✓ Migration completed successfully!")
    else:
        print("✗ Migration failed!")
        sys.exit(1)
