"""
Database migration utility — run once to upgrade existing databases.
Safe to re-run; all operations are idempotent.
"""

import sqlite3
import sys

FIXED_CATEGORIES = ["Estabilidade", "Diversificação", "Valorização", "Antifragilidade"]
PORTFOLIO_INVESTIMENTOS = "investimentos"
PORTFOLIO_PREVIDENCIA = "previdencia"


def migrate_database(db_path: str = "investment_data.db"):
    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        _migrate_positions(cursor)
        _migrate_asset_mappings(cursor)
        _migrate_target_allocations(cursor)
        _migrate_previdencia_mappings(cursor)
        _create_asset_category_targets(cursor)
        _seed_fixed_categories(cursor)
        _fix_seguranca_target(cursor)
        _create_indexes(cursor)

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_positions(cursor):
    cursor.execute("PRAGMA table_info(positions)")
    cols = [row[1] for row in cursor.fetchall()]

    if 'sub_label' not in cols:
        cursor.execute("ALTER TABLE positions ADD COLUMN sub_label TEXT")
        print("  ✓ Added sub_label to positions")

    if 'portfolio' not in cols:
        cursor.execute(f"ALTER TABLE positions ADD COLUMN portfolio TEXT NOT NULL DEFAULT '{PORTFOLIO_INVESTIMENTOS}'")
        print("  ✓ Added portfolio to positions")
    else:
        print("  ✓ positions.portfolio already exists")


def _migrate_asset_mappings(cursor):
    cursor.execute("PRAGMA table_info(asset_mappings)")
    cols = [row[1] for row in cursor.fetchall()]

    if 'portfolio' not in cols:
        cursor.execute(f"ALTER TABLE asset_mappings ADD COLUMN portfolio TEXT NOT NULL DEFAULT '{PORTFOLIO_INVESTIMENTOS}'")
        print("  ✓ Added portfolio to asset_mappings")
    else:
        print("  ✓ asset_mappings.portfolio already exists")


def _migrate_target_allocations(cursor):
    """Recreate target_allocations with (custom_label, portfolio) unique constraint."""
    cursor.execute("PRAGMA table_info(target_allocations)")
    cols = [row[1] for row in cursor.fetchall()]

    if 'portfolio' not in cols:
        # Rename old table
        cursor.execute("ALTER TABLE target_allocations RENAME TO target_allocations_old")

        # Create new table with portfolio column and composite unique constraint
        cursor.execute("""
            CREATE TABLE target_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                custom_label TEXT NOT NULL,
                portfolio TEXT NOT NULL DEFAULT 'investimentos',
                target_percentage REAL NOT NULL,
                reserve_amount REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(custom_label, portfolio)
            )
        """)

        # Copy existing data (skip "Previdência" — no longer a category)
        cursor.execute("""
            INSERT INTO target_allocations (custom_label, portfolio, target_percentage, reserve_amount, created_at, updated_at)
            SELECT custom_label, 'investimentos', target_percentage, reserve_amount, created_at, updated_at
            FROM target_allocations_old
            WHERE custom_label != 'Previdência'
        """)

        cursor.execute("DROP TABLE target_allocations_old")
        print("  ✓ Recreated target_allocations with portfolio column")
    else:
        print("  ✓ target_allocations.portfolio already exists")


def _migrate_previdencia_mappings(cursor):
    """
    Assets previously labeled "Previdência" can't be auto-migrated to a category.
    Delete their asset_mappings so they appear as uncategorized in the Previdência dashboard.
    Move their positions to portfolio='previdencia' and clear custom_label.
    """
    # Delete mappings for Previdência assets (they'll need re-classification)
    cursor.execute("DELETE FROM asset_mappings WHERE custom_label = 'Previdência'")
    count = cursor.rowcount
    if count:
        print(f"  ✓ Removed {count} Previdência asset_mappings (assets need re-classification)")

    # For positions: set portfolio='previdencia', clear custom_label
    # Need to handle NOT NULL on custom_label in old schema — use empty string as placeholder
    # In new schema custom_label is nullable; old schema it's NOT NULL
    # Check if custom_label allows NULL
    cursor.execute("PRAGMA table_info(positions)")
    col_info = {row[1]: row[3] for row in cursor.fetchall()}  # name -> notnull
    if col_info.get('custom_label', 0) == 1:
        # Old schema: NOT NULL — set to empty string as "uncategorized" placeholder
        cursor.execute("""
            UPDATE positions
            SET portfolio = 'previdencia', custom_label = ''
            WHERE custom_label = 'Previdência'
        """)
    else:
        cursor.execute("""
            UPDATE positions
            SET portfolio = 'previdencia', custom_label = NULL
            WHERE custom_label = 'Previdência'
        """)
    pos_count = cursor.rowcount
    if pos_count:
        print(f"  ✓ Moved {pos_count} Previdência positions to previdencia portfolio (needs re-classification)")


def _create_asset_category_targets(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_category_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_name TEXT NOT NULL,
            category_name TEXT NOT NULL,
            portfolio TEXT NOT NULL DEFAULT 'investimentos',
            target_pct REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asset_name, category_name, portfolio)
        )
    """)
    print("  ✓ asset_category_targets table created/verified")


def _seed_fixed_categories(cursor):
    """Seed the 9 fixed category rows if they don't exist."""
    rows = (
        [(cat, PORTFOLIO_INVESTIMENTOS) for cat in FIXED_CATEGORIES]
        + [("Segurança", PORTFOLIO_INVESTIMENTOS)]
        + [(cat, PORTFOLIO_PREVIDENCIA) for cat in FIXED_CATEGORIES]
    )
    seeded = 0
    for custom_label, portfolio in rows:
        cursor.execute(
            "SELECT COUNT(*) FROM target_allocations WHERE custom_label = ? AND portfolio = ?",
            (custom_label, portfolio)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO target_allocations (custom_label, portfolio, target_percentage) VALUES (?, ?, 0.0)",
                (custom_label, portfolio)
            )
            seeded += 1
    if seeded:
        print(f"  ✓ Seeded {seeded} missing fixed category rows")
    else:
        print("  ✓ All fixed categories already present")


def _fix_seguranca_target(cursor):
    """Ensure Segurança always has target_percentage = 0."""
    cursor.execute(
        "UPDATE target_allocations SET target_percentage = 0.0 WHERE custom_label = 'Segurança'"
    )
    if cursor.rowcount:
        print("  ✓ Reset Segurança target_percentage to 0")


def _create_indexes(cursor):
    safe_indexes = [
        ("idx_positions_sub_label", "positions(sub_label)"),
        ("idx_positions_portfolio", "positions(portfolio)"),
        ("idx_mappings_portfolio", "asset_mappings(portfolio)"),
        ("idx_targets_portfolio", "target_allocations(portfolio)"),
        ("idx_act_category", "asset_category_targets(category_name, portfolio)"),
    ]
    optional_indexes = [
        ("idx_sub_label_mappings_parent", "sub_label_mappings(parent_label)"),
        ("idx_sub_label_targets_parent", "sub_label_targets(parent_label)"),
    ]
    for name, definition in safe_indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {definition}")
    for name, definition in optional_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {definition}")
        except Exception:
            pass
    print("  ✓ Indexes created/verified")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "investment_data.db"
    migrate_database(db_path)
