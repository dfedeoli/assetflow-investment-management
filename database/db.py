"""
Database connection and operations for AssetFlow
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from pathlib import Path

from .models import Position, AssetMapping, TargetAllocation, SubLabelMapping, SubLabelTarget


class Database:
    """SQLite database manager for investment data"""

    def __init__(self, db_path: str = "investment_data.db"):
        self.db_path = db_path
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                main_category TEXT NOT NULL,
                sub_category TEXT NOT NULL,
                custom_label TEXT,
                sub_label TEXT,
                date TEXT NOT NULL,
                invested_value REAL,
                percentage REAL,
                quantity INTEGER,
                additional_info TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Asset mappings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asset_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_name TEXT UNIQUE NOT NULL,
                custom_label TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Target allocations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS target_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                custom_label TEXT UNIQUE NOT NULL,
                target_percentage REAL NOT NULL,
                reserve_amount REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sub-label mappings table
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

        # Sub-label targets table
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

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_date ON positions(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_label ON positions(custom_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_name ON positions(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_sub_label ON positions(sub_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_label_mappings_parent ON sub_label_mappings(parent_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_label_targets_parent ON sub_label_targets(parent_label)")

        # Initialize default custom labels
        self._initialize_default_labels(cursor)

        self.conn.commit()

    def _initialize_default_labels(self, cursor):
        """Initialize default custom labels if they don't exist"""
        default_labels = [
            {
                'custom_label': 'Previdência',
                'target_percentage': 0.0,
                'reserve_amount': None
            },
            {
                'custom_label': 'Segurança',
                'target_percentage': 0.0,
                'reserve_amount': None
            }
        ]

        for label_data in default_labels:
            # Check if label already exists
            cursor.execute(
                "SELECT COUNT(*) as count FROM target_allocations WHERE custom_label = ?",
                (label_data['custom_label'],)
            )
            exists = cursor.fetchone()['count'] > 0

            # Insert only if it doesn't exist
            if not exists:
                cursor.execute("""
                    INSERT INTO target_allocations (custom_label, target_percentage, reserve_amount)
                    VALUES (?, ?, ?)
                """, (
                    label_data['custom_label'],
                    label_data['target_percentage'],
                    label_data['reserve_amount']
                ))

    # ==================== Position Operations ====================

    def add_position(self, position: Position) -> int:
        """Add a new position to the database"""
        cursor = self.conn.cursor()

        # Check if there's a mapping for this asset
        mapping = self.get_asset_mapping(position.name)
        if mapping:
            position.custom_label = mapping.custom_label

        # Check if there's a sub-label mapping for this asset
        if position.custom_label:
            sub_mapping = self.get_sub_label_mapping(position.name, position.custom_label)
            if sub_mapping:
                position.sub_label = sub_mapping.sub_label

        cursor.execute("""
            INSERT INTO positions (
                name, value, main_category, sub_category, custom_label, sub_label,
                date, invested_value, percentage, quantity, additional_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position.name,
            position.value,
            position.main_category,
            position.sub_category,
            position.custom_label,
            position.sub_label,
            position.date.isoformat() if position.date else datetime.now().isoformat(),
            position.invested_value,
            position.percentage,
            position.quantity,
            position.additional_info
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_positions_by_date(self, date: datetime) -> List[Position]:
        """Get all positions for a specific date"""
        cursor = self.conn.cursor()
        date_str = date.date().isoformat()

        cursor.execute("""
            SELECT * FROM positions
            WHERE date(date) = date(?)
            ORDER BY value DESC
        """, (date_str,))

        return [self._row_to_position(row) for row in cursor.fetchall()]

    def get_latest_positions(self) -> List[Position]:
        """Get positions from the most recent date"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM positions
            WHERE date(date) = (SELECT date(date) FROM positions ORDER BY date DESC LIMIT 1)
            ORDER BY value DESC
        """)

        return [self._row_to_position(row) for row in cursor.fetchall()]

    def get_all_dates(self) -> List[datetime]:
        """Get all unique dates with positions"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT DISTINCT date(date) as d FROM positions
            ORDER BY d DESC
        """)

        return [datetime.fromisoformat(row['d']) for row in cursor.fetchall()]

    def get_positions_between_dates(self, start_date: datetime, end_date: datetime) -> List[Position]:
        """Get positions between two dates"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM positions
            WHERE date(date) BETWEEN date(?) AND date(?)
            ORDER BY date DESC, value DESC
        """, (start_date.isoformat(), end_date.isoformat()))

        return [self._row_to_position(row) for row in cursor.fetchall()]

    def delete_positions_by_date(self, date: datetime) -> int:
        """Delete all positions for a specific date"""
        cursor = self.conn.cursor()
        date_str = date.date().isoformat()

        cursor.execute("DELETE FROM positions WHERE date(date) = date(?)", (date_str,))
        self.conn.commit()

        return cursor.rowcount

    # ==================== Asset Mapping Operations ====================

    def add_or_update_mapping(self, asset_name: str, custom_label: str) -> int:
        """Add or update an asset mapping"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO asset_mappings (asset_name, custom_label, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(asset_name) DO UPDATE SET
                custom_label = excluded.custom_label,
                updated_at = excluded.updated_at
        """, (asset_name, custom_label, datetime.now().isoformat()))

        self.conn.commit()

        # Update all positions with this asset name
        cursor.execute("""
            UPDATE positions
            SET custom_label = ?
            WHERE name = ?
        """, (custom_label, asset_name))

        self.conn.commit()

        return cursor.lastrowid

    def get_asset_mapping(self, asset_name: str) -> Optional[AssetMapping]:
        """Get mapping for a specific asset"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM asset_mappings WHERE asset_name = ?", (asset_name,))
        row = cursor.fetchone()

        return self._row_to_mapping(row) if row else None

    def get_all_mappings(self) -> List[AssetMapping]:
        """Get all asset mappings"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM asset_mappings ORDER BY custom_label, asset_name")

        return [self._row_to_mapping(row) for row in cursor.fetchall()]

    def delete_mapping(self, asset_name: str) -> bool:
        """Delete an asset mapping and clear custom_label from positions"""
        cursor = self.conn.cursor()

        cursor.execute("DELETE FROM asset_mappings WHERE asset_name = ?", (asset_name,))

        # Clear custom_label from all positions with this asset name
        cursor.execute("""
            UPDATE positions
            SET custom_label = NULL
            WHERE name = ?
        """, (asset_name,))

        self.conn.commit()

        return cursor.rowcount > 0

    def get_unmapped_assets(self) -> List[str]:
        """Get list of assets that don't have custom labels"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT DISTINCT name FROM positions
            WHERE custom_label IS NULL
            ORDER BY name
        """)

        return [row['name'] for row in cursor.fetchall()]

    # ==================== Target Allocation Operations ====================

    def add_or_update_target(self, custom_label: str, target_percentage: float, reserve_amount: float = None) -> int:
        """Add or update a target allocation"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO target_allocations (custom_label, target_percentage, reserve_amount, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(custom_label) DO UPDATE SET
                target_percentage = excluded.target_percentage,
                reserve_amount = excluded.reserve_amount,
                updated_at = excluded.updated_at
        """, (custom_label, target_percentage, reserve_amount, datetime.now().isoformat()))

        self.conn.commit()
        return cursor.lastrowid

    def get_target(self, custom_label: str) -> Optional[TargetAllocation]:
        """Get target allocation for a label"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM target_allocations WHERE custom_label = ?", (custom_label,))
        row = cursor.fetchone()

        return self._row_to_target(row) if row else None

    def get_all_targets(self) -> List[TargetAllocation]:
        """Get all target allocations"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM target_allocations ORDER BY custom_label")

        return [self._row_to_target(row) for row in cursor.fetchall()]

    def delete_target(self, custom_label: str) -> bool:
        """Delete a target allocation"""
        cursor = self.conn.cursor()

        cursor.execute("DELETE FROM target_allocations WHERE custom_label = ?", (custom_label,))
        self.conn.commit()

        return cursor.rowcount > 0

    # ==================== Helper Methods ====================

    def _row_to_position(self, row: sqlite3.Row) -> Position:
        """Convert database row to Position object"""
        # Check if sub_label column exists in the row
        try:
            sub_label = row['sub_label']
        except (KeyError, IndexError):
            sub_label = None

        return Position(
            id=row['id'],
            name=row['name'],
            value=row['value'],
            main_category=row['main_category'],
            sub_category=row['sub_category'],
            custom_label=row['custom_label'],
            sub_label=sub_label,
            date=datetime.fromisoformat(row['date']),
            invested_value=row['invested_value'],
            percentage=row['percentage'],
            quantity=row['quantity'],
            additional_info=row['additional_info']
        )

    def _row_to_mapping(self, row: sqlite3.Row) -> AssetMapping:
        """Convert database row to AssetMapping object"""
        return AssetMapping(
            id=row['id'],
            asset_name=row['asset_name'],
            custom_label=row['custom_label'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    def _row_to_target(self, row: sqlite3.Row) -> TargetAllocation:
        """Convert database row to TargetAllocation object"""
        # Check if reserve_amount column exists
        try:
            reserve_amount = row['reserve_amount']
        except (KeyError, IndexError):
            reserve_amount = None

        return TargetAllocation(
            id=row['id'],
            custom_label=row['custom_label'],
            target_percentage=row['target_percentage'],
            reserve_amount=reserve_amount,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    # ==================== Sub-Label Operations ====================

    def add_or_update_sub_label_mapping(self, asset_name: str, parent_label: str, sub_label: str) -> int:
        """Add or update a sub-label mapping for an asset within a parent category"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO sub_label_mappings (asset_name, parent_label, sub_label, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(asset_name, parent_label) DO UPDATE SET
                sub_label = excluded.sub_label,
                updated_at = excluded.updated_at
        """, (asset_name, parent_label, sub_label, datetime.now().isoformat()))

        self.conn.commit()

        # Update all positions with this asset name and parent label
        cursor.execute("""
            UPDATE positions
            SET sub_label = ?
            WHERE name = ? AND custom_label = ?
        """, (sub_label, asset_name, parent_label))

        self.conn.commit()

        return cursor.lastrowid

    def get_sub_label_mapping(self, asset_name: str, parent_label: str) -> Optional[SubLabelMapping]:
        """Get sub-label mapping for a specific asset within a parent category"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM sub_label_mappings
            WHERE asset_name = ? AND parent_label = ?
        """, (asset_name, parent_label))
        row = cursor.fetchone()

        return self._row_to_sub_label_mapping(row) if row else None

    def get_all_sub_label_mappings(self, parent_label: str) -> List[SubLabelMapping]:
        """Get all sub-label mappings for a parent category"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM sub_label_mappings
            WHERE parent_label = ?
            ORDER BY sub_label, asset_name
        """, (parent_label,))

        return [self._row_to_sub_label_mapping(row) for row in cursor.fetchall()]

    def delete_sub_label_mapping(self, asset_name: str, parent_label: str) -> bool:
        """Delete a sub-label mapping"""
        cursor = self.conn.cursor()

        cursor.execute("""
            DELETE FROM sub_label_mappings
            WHERE asset_name = ? AND parent_label = ?
        """, (asset_name, parent_label))
        self.conn.commit()

        # Clear sub_label from positions
        cursor.execute("""
            UPDATE positions
            SET sub_label = NULL
            WHERE name = ? AND custom_label = ?
        """, (asset_name, parent_label))
        self.conn.commit()

        return cursor.rowcount > 0

    def get_unmapped_sub_assets(self, parent_label: str) -> List[str]:
        """Get assets in parent_label that don't have sub_labels"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT DISTINCT name FROM positions
            WHERE custom_label = ? AND sub_label IS NULL
            ORDER BY name
        """, (parent_label,))

        return [row['name'] for row in cursor.fetchall()]

    def add_or_update_sub_label_target(self, parent_label: str, sub_label: str, target_percentage: float) -> int:
        """Add or update a target allocation for a sub-label"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO sub_label_targets (parent_label, sub_label, target_percentage, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(parent_label, sub_label) DO UPDATE SET
                target_percentage = excluded.target_percentage,
                updated_at = excluded.updated_at
        """, (parent_label, sub_label, target_percentage, datetime.now().isoformat()))

        self.conn.commit()
        return cursor.lastrowid

    def get_sub_label_target(self, parent_label: str, sub_label: str) -> Optional[SubLabelTarget]:
        """Get target allocation for a sub-label"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM sub_label_targets
            WHERE parent_label = ? AND sub_label = ?
        """, (parent_label, sub_label))
        row = cursor.fetchone()

        return self._row_to_sub_label_target(row) if row else None

    def get_all_sub_label_targets(self, parent_label: str) -> List[SubLabelTarget]:
        """Get all target allocations for sub-labels within a parent category"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM sub_label_targets
            WHERE parent_label = ?
            ORDER BY sub_label
        """, (parent_label,))

        return [self._row_to_sub_label_target(row) for row in cursor.fetchall()]

    def delete_sub_label_target(self, parent_label: str, sub_label: str) -> bool:
        """Delete a sub-label target allocation"""
        cursor = self.conn.cursor()

        cursor.execute("""
            DELETE FROM sub_label_targets
            WHERE parent_label = ? AND sub_label = ?
        """, (parent_label, sub_label))
        self.conn.commit()

        return cursor.rowcount > 0

    def get_positions_by_custom_label(self, custom_label: str, date: Optional[datetime] = None) -> List[Position]:
        """Get positions for a specific custom label, optionally filtered by date"""
        cursor = self.conn.cursor()

        if date:
            date_str = date.date().isoformat()
            cursor.execute("""
                SELECT * FROM positions
                WHERE custom_label = ? AND date(date) = date(?)
                ORDER BY value DESC
            """, (custom_label, date_str))
        else:
            cursor.execute("""
                SELECT * FROM positions
                WHERE custom_label = ?
                AND date(date) = (SELECT date(date) FROM positions ORDER BY date DESC LIMIT 1)
                ORDER BY value DESC
            """, (custom_label,))

        return [self._row_to_position(row) for row in cursor.fetchall()]

    def _row_to_sub_label_mapping(self, row: sqlite3.Row) -> SubLabelMapping:
        """Convert database row to SubLabelMapping object"""
        return SubLabelMapping(
            id=row['id'],
            asset_name=row['asset_name'],
            parent_label=row['parent_label'],
            sub_label=row['sub_label'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    def _row_to_sub_label_target(self, row: sqlite3.Row) -> SubLabelTarget:
        """Convert database row to SubLabelTarget object"""
        return SubLabelTarget(
            id=row['id'],
            parent_label=row['parent_label'],
            sub_label=row['sub_label'],
            target_percentage=row['target_percentage'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    def get_summary_statistics(self) -> Dict:
        """Get overall database statistics"""
        cursor = self.conn.cursor()

        stats = {}

        # Total positions
        cursor.execute("SELECT COUNT(*) as count FROM positions")
        stats['total_positions'] = cursor.fetchone()['count']

        # Unique dates
        cursor.execute("SELECT COUNT(DISTINCT date(date)) as count FROM positions")
        stats['total_dates'] = cursor.fetchone()['count']

        # Total mappings
        cursor.execute("SELECT COUNT(*) as count FROM asset_mappings")
        stats['total_mappings'] = cursor.fetchone()['count']

        # Total targets
        cursor.execute("SELECT COUNT(*) as count FROM target_allocations")
        stats['total_targets'] = cursor.fetchone()['count']

        # Unmapped assets
        cursor.execute("""
            SELECT COUNT(DISTINCT name) as count FROM positions
            WHERE custom_label IS NULL
        """)
        stats['unmapped_assets'] = cursor.fetchone()['count']

        return stats

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
