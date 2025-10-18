# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Default Custom Labels**: "Previdência" (retirement funds) and "Segurança" (safety reserve) custom labels are now automatically created when initializing a new database, ensuring all users start with these essential categories available
- **Edit Existing Positions**: "Atualizar Posições" tab now supports editing positions on the same date to fix incorrect values. New "✏️ Editar na mesma data" checkbox allows users to choose between editing existing data or creating a new snapshot
- **Inline Editing for Invested Values**: Dashboard "Detalhes por Ativo" tab now allows inline editing of "Investido" (invested_value) column. Click any cell to correct wrong values, and "Ganho" (gain/loss) automatically recalculates. Changes are saved with a single button click
- **Update Positions Feature**: New "Atualizar Posições" tab in the upload component that allows users to:
  - Load positions from a previous date as a starting point
  - Edit individual position values
  - Remove positions that were sold
  - Add new positions that were acquired
  - View real-time summary of changes (total positions, total value, percentage change)
  - Preserve custom labels and classifications when updating
  - Handle duplicate date detection with options to delete or merge
- Session state management for tracking original values to prevent UI updates from affecting displayed original values
- **Asset-Level Rebalancing Details**: Granular breakdown in Dashboard "Rebalanceamento" tab showing:
  - Individual assets within each category with current values and percentages
  - Specific investment recommendations for each asset when categories are underweight
  - Multiple allocation strategies:
    - **Proportional distribution**: Maintains current asset weights within category
    - **Equal distribution**: Spreads investment equally across all assets in category
    - **Manual selection**: Guidance for custom allocation decisions
  - Smart selling recommendations only when no new investment is provided
  - Warning messages encouraging adding new money instead of selling positions
  - Automatic expansion of categories requiring significant action (>R$ 100 adjustment)
  - Clear visual status indicators (✅ balanced, 🔴 underweight, ⚠️ overweight)

### Changed
- **Dashboard Filtering**: Labels with 0% target allocation are now excluded from "Visão Geral" and "Rebalanceamento" tabs, but all assets remain visible in "Detalhes por Ativo" tab. This allows users to have custom labels (like Previdência and Segurança) that don't participate in active portfolio management but can still be tracked
- **Detalhes por Ativo UI**: Filters are now hidden in a collapsible expander (collapsed by default) to reduce visual clutter. Sort dropdown remains visible for easy access
- Upload component now has three tabs: "Entrada Manual", "Upload XLSX", and "Atualizar Posições"
- Dashboard "Rebalanceamento" tab now includes detailed asset-level breakdown below category-level analysis
- Rebalancing UI now emphasizes adding new money over selling existing positions

### Technical Details
- Added `_initialize_default_labels()` method in Database class (database/db.py:110-142)
- Default labels are inserted only if they don't already exist (idempotent operation)
- Labels created with 0% target allocation and no reserve amount (can be customized later)
- Updated dashboard filtering logic to exclude labels with `target_percentage == 0` (components/dashboard.py:24)
- Rebalancing analysis now excludes 0% targets from target_allocations dictionary (components/dashboard.py:183)
- "Detalhes por Ativo" tab now receives `all_positions` to show complete portfolio (components/dashboard.py:94)
- Filters in "Detalhes por Ativo" wrapped in `st.expander()` for cleaner UI (components/dashboard.py:429)
- Added `edit_same_date` session state variable to track edit mode (components/upload.py:213)
- Same-date editing automatically deletes old positions before saving edited ones (components/upload.py:395)
- Dynamic button labels based on edit mode: "Salvar Alterações" for same date, "Salvar Posições Atualizadas" for new date
- Added `update_position_invested_value(position_id, invested_value)` method in Database class (database/db.py:241-252)
- Replaced `st.dataframe` with `st.data_editor` in asset details for inline editing (components/dashboard.py:516-522)
- Only "Investido (R$)" column is editable; all other columns are read-only for data safety
- Change detection compares original vs edited DataFrame to show save button only when needed
- Ganho columns automatically recalculate based on formula: `value - invested_value`
- Added `_render_update_positions()` function to handle the update workflow (components/upload.py:193)
- Added `_save_updated_positions()` helper function for batch saving (components/upload.py:393)
- Added `_clear_editing_state()` helper function for session state cleanup (components/upload.py:411)
- Session state variables added: `editing_positions`, `base_date`, `new_date`, `positions_to_remove`, `new_positions`, `original_values`
- Added `_render_asset_level_rebalancing()` function to display detailed asset recommendations (components/dashboard.py:267)
- Asset recommendations sorted by priority: categories needing action first, then by adjustment amount
- Conditional display logic: selling recommendations only shown when `additional_investment == 0`

## [Previous Versions]

No previous changelog entries exist. This is the first version of the CHANGELOG.
