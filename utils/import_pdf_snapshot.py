"""
Import a portfolio snapshot manually transcribed from a broker PDF statement
(e.g. XP "Posição Consolidada") directly into the database, bypassing the
Streamlit UI and the OpenAI Vision PDF parser.

Use this when you (or Claude) have already read the PDF and transcribed the
positions accurately — it's faster and cheaper than the AI vision import in
components/upload.py, and gives full control over asset names (so they match
existing asset_mappings and inherit the right custom_label/portfolio).

Usage:
    1. Edit SNAPSHOT_DATE and the POSITIONS list below for the statement you're importing.
    2. Run: python utils/import_pdf_snapshot.py
    3. The script prints a summary per portfolio; verify totals against the PDF before trusting the import.

Notes:
    - Position.value should be the "Posição" (gross) value from the PDF.
    - Use the EXACT asset name already present in asset_mappings when the asset already
      exists in the database (even if the broker changed its display name), so it inherits
      its existing custom_label/portfolio. Check with:
          sqlite3-less check: python -c "from database.db import Database; db=Database(); [print(p.name, p.custom_label, p.portfolio) for p in db.get_latest_positions()]"
    - Assets with no existing mapping are imported with custom_label=None ("Não Classificado")
      and must be classified in the app afterward.
    - db.add_position() upserts on (name, date, portfolio), so re-running this script for the
      same date just updates the existing rows instead of duplicating them.
    - POSITIONS below is a template with example rows — replace with your own transcribed
      data before running. Never commit real fund names/values here (this file is tracked
      by git and the repo is public); keep your actual snapshot data local-only.
"""

from datetime import datetime

from database.db import Database, PORTFOLIO_INVESTIMENTOS, PORTFOLIO_PREVIDENCIA
from database.models import Position

# ---------------------------------------------------------------------------
# Edit below for each new snapshot
# ---------------------------------------------------------------------------

SNAPSHOT_DATE = datetime(2026, 8, 31)

# Each tuple: (name, value, main_category, sub_category, portfolio)
# Example/template rows only - replace with your own transcribed PDF data.
POSITIONS = [
    # -- Investimentos --
    ("Example FII ABCD11", 8057.28, "Fundos Imobiliários", "Fundos Listados", PORTFOLIO_INVESTIMENTOS),
    ("Example Fixed Income Fund RF Simples", 67059.66, "Fundos de Investimentos", "Pós-Fixado", PORTFOLIO_INVESTIMENTOS),
    ("Example Multimarket Fund FIM", 34889.71, "Fundos de Investimentos", "Multimercados", PORTFOLIO_INVESTIMENTOS),
    ("Example Equity Fund FIA", 9006.92, "Fundos de Investimentos", "Renda Variável Brasil", PORTFOLIO_INVESTIMENTOS),
    ("Example COE Product", 43347.55, "COE", "COE", PORTFOLIO_INVESTIMENTOS),

    # -- Previdência --
    ("Example PGBL Fund I", 1388.92, "Previdência Privada", "PGBL", PORTFOLIO_PREVIDENCIA),
    ("Example PGBL Fund II", 2052.49, "Previdência Privada", "PGBL", PORTFOLIO_PREVIDENCIA),
]


def main():
    db = Database()

    existing = db.get_positions_by_date(SNAPSHOT_DATE)
    if existing:
        print(f"WARNING: {len(existing)} position(s) already exist for {SNAPSHOT_DATE.date()}.")
        print("add_position() will update them in place rather than duplicate. Continuing.")

    totals = {}
    unclassified = []

    for name, value, main_category, sub_category, portfolio in POSITIONS:
        pos = Position(
            name=name,
            value=value,
            main_category=main_category,
            sub_category=sub_category,
            portfolio=portfolio,
            date=SNAPSHOT_DATE,
        )
        db.add_position(pos)

        mapping = db.get_asset_mapping(name)
        if not mapping:
            unclassified.append(name)

        totals[portfolio] = totals.get(portfolio, 0.0) + value

    print(f"Imported {len(POSITIONS)} positions for {SNAPSHOT_DATE.date()}.")
    for portfolio, total in totals.items():
        count = sum(1 for p in POSITIONS if p[4] == portfolio)
        print(f"  {portfolio}: {count} positions, R$ {total:,.2f}")

    if unclassified:
        print("\nUnclassified assets (no existing asset_mappings entry, need classification in-app):")
        for name in unclassified:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
