# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an investment portfolio management application built with Streamlit. The application allows users to:
- Import investment positions from messy XLSX files or manual entry
- Classify assets into custom categories
- Define target allocation percentages
- View portfolio analysis and rebalancing recommendations
- Track historical evolution across multiple snapshots

## Technology Stack

- **Python 3.11+** (managed via `uv`)
- **Streamlit** - Web application framework
- **Pandas** - Data manipulation and analysis
- **OpenPyXL** - Reading Excel files
- **SQLite** - Local database for storing positions, mappings, and targets

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies using uv
uv sync
```

### Running the Application
```bash
# Run the Streamlit app
streamlit run main.py

# Run with auto-reload on file changes
streamlit run main.py --server.runOnSave true
```

### Package Management
```bash
# Add a new dependency
uv add <package-name>

# Update dependencies
uv sync
```

## Architecture

The application follows a modular architecture with clear separation of concerns:

### Directory Structure
```
├── main.py                    # Main Streamlit app and navigation
├── database/
│   ├── db.py                  # SQLite database operations
│   └── models.py              # Data models (Position, AssetMapping, TargetAllocation, SubLabelMapping, SubLabelTarget)
├── parsers/
│   └── xlsx_parser.py         # XLSX file parser for messy investment files
├── components/
│   ├── upload.py              # File upload and manual entry UI
│   ├── classification.py      # Asset classification and target management
│   ├── dashboard.py           # Portfolio dashboard and rebalancing view
│   ├── previdencia.py         # Specialized Previdência component with sub-classification
│   └── history.py             # Historical evolution and comparison
└── utils/
    ├── calculations.py        # Portfolio calculations and rebalancing logic
    └── migrate_db.py          # Database migration utility
```

### Data Flow

1. **Import**: XLSX files or manual entries → Parser → Database (positions table)
2. **Classification**: User maps assets to custom labels → Database (asset_mappings table)
3. **Targets**: User defines target allocations → Database (target_allocations table)
4. **Analysis**: Positions + Mappings + Targets → PortfolioCalculator → Carteira de Investimento visualization

### Key Components

**XLSXParser** (parsers/xlsx_parser.py)
- Handles messy Excel files with varying structures
- Detects main categories (Fundos, Renda Fixa, FIIs, Previdência, COE)
- Extracts sub-categories (Pós-Fixado, Multimercados, etc.)
- Parses Brazilian currency format (R$ 1.234,56)
- Returns list of InvestmentPosition objects

**Database** (database/db.py)
- SQLite connection with five main tables:
  - `positions`: Historical snapshots of all investments (includes sub_label column)
  - `asset_mappings`: Maps asset names to custom labels
  - `target_allocations`: Target percentage per custom label
  - `sub_label_mappings`: Maps assets within a parent category to sub-labels
  - `sub_label_targets`: Target percentages for sub-labels within parent category
- Automatic custom_label application when positions are added
- Query methods for date-based filtering and historical analysis
- **Default Labels**: Automatically creates "Previdência" and "Segurança" custom labels on database initialization (with 0% target allocation)
- **Important**: Uses `sqlite3.Row` - access columns with `row['column']` not `row.get('column')`

**PortfolioCalculator** (utils/calculations.py)
- Calculates current allocation by category
- Compares current vs target allocations
- Generates rebalancing recommendations
- Supports "new money" scenarios (where to invest additional funds)
- Calculates historical growth between periods

### Database Schema

**positions table:**
- Stores all investment positions with timestamps
- Links to custom_label via asset_mappings
- Supports multiple snapshots for the same date
- Includes `sub_label` column for hierarchical classification

**asset_mappings table:**
- One-to-one mapping: asset_name → custom_label
- Updating a mapping auto-updates all positions with that asset

**target_allocations table:**
- One target percentage per custom_label
- Used for rebalancing calculations

**sub_label_mappings table:**
- Maps assets within a parent category (e.g., "Previdência") to sub-labels (e.g., "Conservadora")
- Unique constraint on (asset_name, parent_label)
- Used for detailed classification within a custom label

**sub_label_targets table:**
- Target percentages for sub-labels within a parent category
- Percentages are relative to parent category total (not portfolio total)
- Must sum to 100% within each parent_label
- Unique constraint on (parent_label, sub_label)

### Component Interactions

- `main.py` initializes Database in session_state (singleton pattern)
- Each component receives the Database instance
- Components use `st.rerun()` after data modifications to refresh UI
- Sidebar displays real-time statistics from database

**Previdência Component** (components/previdencia.py)
- Specialized dashboard for Previdência category with sub-classification support
- Four sub-tabs:
  1. **Visão Geral**: Distribution charts by sub-labels
  2. **Sub-Classificação**: UI to classify assets into sub-categories
  3. **Definir Metas**: Set target allocations (must sum to 100% of Previdência)
  4. **Rebalanceamento**: Within-category rebalancing analysis
- **Important**: Uses "Previdência" (with accent ê) - ensure consistency when querying
- Pattern can be extended to other categories needing sub-classification

## Key Workflows

### Importing XLSX Files
1. User uploads file in components/upload.py
2. XLSXParser detects structure and extracts positions
3. Preview shown with metadata (date, account, total value)
4. User confirms import (with duplicate detection)
5. Positions saved to database with auto-mapping if available

### Rebalancing Analysis
1. PortfolioCalculator gets latest positions from database
2. Calculates current allocation by custom_label
3. Compares with target_allocations from database
4. Generates AllocationAnalysis for each category
5. Produces suggestions for rebalancing or new investments

### Historical Comparison
1. Database provides all unique dates with positions
2. User selects two dates to compare
3. Calculator computes growth per category
4. UI shows value changes and percentage shifts
5. Identifies new/removed positions between periods

### Database Migration
1. Run `python utils/migrate_db.py [db_path]` to update existing databases
2. Migration safely adds:
   - `sub_label` column to positions table (if missing)
   - `sub_label_mappings` table
   - `sub_label_targets` table
   - Necessary indexes
3. Migration is idempotent (safe to run multiple times)
4. Use after pulling code updates that modify schema

## Important Implementation Notes

### Documentation Requirements
- **ALWAYS update CHANGELOG.md** when making any code changes
- Document new features, bug fixes, and breaking changes in the `[Unreleased]` section
- Follow the [Keep a Changelog](https://keepachangelog.com/) format
- Include technical implementation details for developers
- When releasing a version, move unreleased changes to a dated version section

### Data Formats
- The XLSX parser assumes Brazilian format (R$, comma as decimal separator)
- Position dates are stored as ISO format strings in SQLite
- Currency values stored as REAL (float) in database

### Classification System
- Custom labels must be defined before setting targets
- **Carteira de Investimento filtering**: Only positions with defined targets appear in the main Carteira de Investimento
- Unmapped assets show as "Não Classificado" in analysis
- **Sub-labels**: Hierarchical classification within parent categories (e.g., Previdência → Conservadora/Moderada)
- Sub-label targets are percentages within the parent category (not the total portfolio)
- Sub-label targets must sum to 100% within each parent category

### Database Access Patterns
- **Critical**: `sqlite3.Row` objects don't have `.get()` method - use `row['column']` with try-except
- Example pattern for optional columns:
  ```python
  try:
      sub_label = row['sub_label']
  except (KeyError, IndexError):
      sub_label = None
  ```
- Always use exact spelling for custom labels (e.g., "Previdência" with accent, not "Previdencia")

### Portfolio Calculations
- The 0.5% tolerance for "balanced" status is configurable in PortfolioCalculator
- Rebalancing calculations support "new money" scenarios
- Sub-category rebalancing operates independently within parent category

### Common Pitfalls
1. **Spelling inconsistencies**: Portuguese labels with accents (Previdência, not Previdencia)
2. **sqlite3.Row access**: Use bracket notation, not .get()
3. **Sub-label percentage context**: Always relative to parent category, not total portfolio
4. **Missing migrations**: Run migrate_db.py when schema changes
