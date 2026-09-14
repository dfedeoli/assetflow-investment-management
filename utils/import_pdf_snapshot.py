"""
Import a portfolio snapshot manually transcribed from a broker PDF statement
(e.g. XP "Posição Consolidada") directly into the database, bypassing the
Streamlit UI and the OpenAI Vision PDF parser.

Use this when you (or Claude) have already read the PDF and transcribed the
positions accurately — it's faster and cheaper than the AI vision import in
components/upload.py, and gives full control over asset names (so they match
existing asset_mappings and inherit the right custom_label/portfolio).

Usage:
    1. Copy utils/pdf_snapshot_data.py.example to utils/pdf_snapshot_data.py
       (gitignored — never tracked, so real data can't be committed through this workflow).
    2. Edit SNAPSHOT_DATE and POSITIONS in that local file for the statement you're importing.
    3. Run: python utils/import_pdf_snapshot.py
    4. The script prints a summary per portfolio; verify totals against the PDF before trusting the import.

Notes:
    - Position.value should be the "Posição" (gross) value from the PDF.
    - Use the EXACT asset name already present in asset_mappings when the asset already
      exists in the database (even if the broker changed its display name), so it inherits
      its existing custom_label/portfolio. Check with:
          python -c "from database.db import Database; db=Database(); [print(p.name, p.custom_label, p.portfolio) for p in db.get_latest_positions()]"
    - Assets with no existing mapping are imported with custom_label=None ("Não Classificado")
      and must be classified in the app afterward.
    - db.add_position() upserts on (name, date, portfolio), so re-running this script for the
      same date just updates the existing rows instead of duplicating them.
    - This file is tracked by git and the repo is public: it must never contain real fund
      names or values directly. All real snapshot data belongs only in
      utils/pdf_snapshot_data.py, which is gitignored.
"""

from database.db import Database


def load_snapshot_data():
    try:
        from utils.pdf_snapshot_data import SNAPSHOT_DATE, POSITIONS
    except ImportError:
        raise SystemExit(
            "utils/pdf_snapshot_data.py not found.\n\n"
            "This file holds your real snapshot data and is gitignored on purpose — real "
            "fund names/values must never be committed to this (public) repo.\n\n"
            "To use this script:\n"
            "  cp utils/pdf_snapshot_data.py.example utils/pdf_snapshot_data.py\n"
            "then edit SNAPSHOT_DATE and POSITIONS in the new local file."
        )
    return SNAPSHOT_DATE, POSITIONS


def main():
    snapshot_date, positions = load_snapshot_data()

    db = Database()

    existing = db.get_positions_by_date(snapshot_date)
    if existing:
        print(f"WARNING: {len(existing)} position(s) already exist for {snapshot_date.date()}.")
        print("add_position() will update them in place rather than duplicate. Continuing.")

    totals = {}
    unclassified = []

    for name, value, main_category, sub_category, portfolio in positions:
        from database.models import Position
        pos = Position(
            name=name,
            value=value,
            main_category=main_category,
            sub_category=sub_category,
            portfolio=portfolio,
            date=snapshot_date,
        )
        db.add_position(pos)

        mapping = db.get_asset_mapping(name)
        if not mapping:
            unclassified.append(name)

        totals[portfolio] = totals.get(portfolio, 0.0) + value

    print(f"Imported {len(positions)} positions for {snapshot_date.date()}.")
    for portfolio, total in totals.items():
        count = sum(1 for p in positions if p[4] == portfolio)
        print(f"  {portfolio}: {count} positions, R$ {total:,.2f}")

    if unclassified:
        print("\nUnclassified assets (no existing asset_mappings entry, need classification in-app):")
        for name in unclassified:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
