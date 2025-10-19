"""
Database migration utility to add contributions table
"""

import sqlite3
import sys

def migrate_database(db_path: str = "investment_data.db"):
    """Migrate existing database to include contributions tracking"""

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create contributions table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_name TEXT NOT NULL,
                contribution_amount REAL NOT NULL,
                contribution_date TEXT NOT NULL,
                position_id INTEGER,
                previous_value REAL NOT NULL,
                new_total_value REAL NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (position_id) REFERENCES positions(id)
            )
        """)
        print("  ✓ contributions table created/verified")

        # Create indexes for contributions table
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contributions_asset ON contributions(asset_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contributions_date ON contributions(contribution_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contributions_position ON contributions(position_id)")
        print("  ✓ Indexes created/verified")

        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\nYou can now use the 'Registrar Contribuição' feature to track contributions to your assets.")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "investment_data.db"
    migrate_database(db_path)
