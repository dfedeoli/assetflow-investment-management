"""
Database migration script to add PGBL tax tracker tables.

This script safely adds the new tables required for PGBL tax planning:
- annual_income_entries
- pgbl_year_settings

It is idempotent (safe to run multiple times).
"""

import sqlite3
import sys
from pathlib import Path


def migrate_database(db_path: str = "investment_data.db"):
    """
    Migrate database to add PGBL tracker tables.

    Args:
        db_path: Path to the database file
    """
    print(f"Starting migration for database: {db_path}")

    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if tables already exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('annual_income_entries', 'pgbl_year_settings')
        """)
        existing_tables = {row[0] for row in cursor.fetchall()}

        tables_to_create = []

        # Add annual_income_entries table if not exists
        if 'annual_income_entries' not in existing_tables:
            print("Creating table: annual_income_entries...")
            cursor.execute("""
                CREATE TABLE annual_income_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    entry_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    date_added TEXT DEFAULT CURRENT_TIMESTAMP,
                    CHECK(month >= 1 AND month <= 12)
                )
            """)
            tables_to_create.append("annual_income_entries")

            # Create indexes
            cursor.execute("CREATE INDEX idx_income_entries_year ON annual_income_entries(year)")
            cursor.execute("CREATE INDEX idx_income_entries_year_month ON annual_income_entries(year, month)")
            print("✓ Table 'annual_income_entries' created with indexes")
        else:
            print("✓ Table 'annual_income_entries' already exists, skipping")

        # Add pgbl_year_settings table if not exists
        if 'pgbl_year_settings' not in existing_tables:
            print("Creating table: pgbl_year_settings...")
            cursor.execute("""
                CREATE TABLE pgbl_year_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER UNIQUE NOT NULL,
                    contributes_to_inss INTEGER NOT NULL DEFAULT 1,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            tables_to_create.append("pgbl_year_settings")

            # Create index
            cursor.execute("CREATE INDEX idx_pgbl_year_settings_year ON pgbl_year_settings(year)")
            print("✓ Table 'pgbl_year_settings' created with index")
        else:
            print("✓ Table 'pgbl_year_settings' already exists, skipping")

        # Commit changes
        conn.commit()

        if tables_to_create:
            print(f"\n✅ Migration completed successfully!")
            print(f"   Created {len(tables_to_create)} new table(s): {', '.join(tables_to_create)}")
        else:
            print("\n✅ Database already up to date, no migration needed")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"❌ Error during migration: {e}")
        return False


def main():
    """Main function to run migration"""
    db_path = sys.argv[1] if len(sys.argv) > 1 else "investment_data.db"

    print("=" * 60)
    print("PGBL Tax Tracker - Database Migration")
    print("=" * 60)
    print()

    success = migrate_database(db_path)

    if success:
        print()
        print("You can now use the PGBL Planning tab in the Previdência component!")
        print()
        sys.exit(0)
    else:
        print()
        print("Migration failed. Please check the error messages above.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
