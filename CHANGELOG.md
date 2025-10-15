# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- Upload component now has three tabs: "Entrada Manual", "Upload XLSX", and "Atualizar Posições"
- Dashboard "Rebalanceamento" tab now includes detailed asset-level breakdown below category-level analysis
- Rebalancing UI now emphasizes adding new money over selling existing positions

### Technical Details
- Added `_render_update_positions()` function to handle the update workflow (components/upload.py:193)
- Added `_save_updated_positions()` helper function for batch saving (components/upload.py:393)
- Added `_clear_editing_state()` helper function for session state cleanup (components/upload.py:411)
- Session state variables added: `editing_positions`, `base_date`, `new_date`, `positions_to_remove`, `new_positions`, `original_values`
- Added `_render_asset_level_rebalancing()` function to display detailed asset recommendations (components/dashboard.py:267)
- Asset recommendations sorted by priority: categories needing action first, then by adjustment amount
- Conditional display logic: selling recommendations only shown when `additional_investment == 0`

## [Previous Versions]

No previous changelog entries exist. This is the first version of the CHANGELOG.
