# AssetFlow - Investment Management

A comprehensive Streamlit application for managing and analyzing your investment portfolio.

## Features

- **Import Investment Data**
  - Upload messy XLSX files from your broker
  - Manual entry for individual positions
  - Automatic parsing of complex file formats

- **Asset Classification**
  - Create custom investment categories
  - Map assets to personalized labels
  - Define target allocation percentages

- **Portfolio Analysis**
  - View current allocation breakdown
  - Compare against target allocations
  - Get rebalancing recommendations
  - Calculate where to invest new money

- **Historical Tracking**
  - Track portfolio evolution over time
  - Compare different time periods
  - Analyze category allocation changes
  - View investment growth trends

## Quick Start

1. **Install Dependencies**
   ```bash
   uv sync
   ```

2. **Run the Application**
   ```bash
   streamlit run main.py
   ```

3. **First Time Setup**
   - Go to "Importar Dados" and upload your first XLSX file or add positions manually
   - Go to "Classificação" to categorize your assets
   - Define your target allocations in the "Definir Metas" tab
   - View analysis in the "Dashboard"

## Project Structure

```
- main.py                    # Main application entry point
- database/                  # Database models and operations
- parsers/                   # XLSX file parser
- components/                # UI components (upload, dashboard, etc.)
- utils/                     # Calculation utilities
```

## Technology Stack

- Python 3.11+
- Streamlit
- Pandas
- SQLite
- OpenPyXL

## Database

The application uses SQLite to store:
- Investment positions (historical snapshots)
- Asset-to-category mappings
- Target allocation percentages

Database file: `investment_data.db` (created automatically on first run)

## XLSX File Format

The parser is designed to handle messy Excel files with:
- Multiple header rows
- Varying column structures per section
- Empty rows and columns
- Brazilian currency format (R$ 1.234,56)

Example categories supported:
- Fundos de Investimentos (Pos-Fixado, Multimercados, Renda Vari�vel)
- Renda Fixa (Prefixado, Inflacao)
- Fundos Imobiliarios
- Previdencia Privada
- COE

## Contributing

This is a personal project, but suggestions and improvements are welcome!
