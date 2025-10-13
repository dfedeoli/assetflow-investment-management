"""
Database migration utility to add new columns and tables
"""

import sqlite3
import sys

def migrate_database(db_path: str = "investment_data.db"):
    """Migrate existing database to include sub_label support"""

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if sub_label column exists in positions table
        cursor.execute("PRAGMA table_info(positions)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'sub_label' not in columns:
            print("  Adding sub_label column to positions table...")
            cursor.execute("ALTER TABLE positions ADD COLUMN sub_label TEXT")
            print("  ✓ Added sub_label column")
        else:
            print("  ✓ sub_label column already exists")

        # Create sub_label_mappings table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_label_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_name TEXT NOT NULL,
                parent_label TEXT NOT NULL,
                sub_label TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asset_name, parent_label)
            )
        """)
        print("  ✓ sub_label_mappings table created/verified")

        # Create sub_label_targets table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_label_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_label TEXT NOT NULL,
                sub_label TEXT NOT NULL,
                target_percentage REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(parent_label, sub_label)
            )
        """)
        print("  ✓ sub_label_targets table created/verified")

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_sub_label ON positions(sub_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_label_mappings_parent ON sub_label_mappings(parent_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_label_targets_parent ON sub_label_targets(parent_label)")
        print("  ✓ Indexes created/verified")

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "investment_data.db"
    migrate_database(db_path)
