"""
XLSX Parser for Investment Position Files

Handles messy Excel files with:
- Header rows with metadata
- Category sections with varying structures
- Empty rows and columns
- Sub-category headers
"""

import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class InvestmentPosition:
    """Represents a single investment position"""
    def __init__(
        self,
        name: str,
        value: float,
        main_category: str,
        sub_category: str,
        date: datetime,
        invested_value: Optional[float] = None,
        percentage: Optional[float] = None,
        quantity: Optional[int] = None,
        additional_info: Optional[Dict] = None
    ):
        self.name = name
        self.value = value
        self.main_category = main_category
        self.sub_category = sub_category
        self.date = date
        self.invested_value = invested_value
        self.percentage = percentage
        self.quantity = quantity
        self.additional_info = additional_info or {}

    def __repr__(self):
        return f"<Position {self.name}: R$ {self.value:,.2f} ({self.sub_category})>"


class XLSXParser:
    """Parser for messy investment XLSX files"""

    # Main category indicators
    MAIN_CATEGORIES = {
        'Fundos de Investimentos': 'Fundos de Investimentos',
        'Renda Fixa': 'Renda Fixa',
        'Posição de Fundos Imobiliários': 'Fundos Imobiliários',
        'Previdência Privada': 'Previdência Privada',
        'COE': 'COE'
    }

    # Sub-category pattern (e.g., "28,3% | Pós-Fixado")
    SUBCATEGORY_PATTERN = re.compile(r'[\d,\.]+%\s*\|\s*(.+)')

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = pd.read_excel(file_path, header=None)
        self.positions: List[InvestmentPosition] = []
        self.metadata = {}

    def parse(self) -> Tuple[List[InvestmentPosition], Dict]:
        """Parse the entire file and extract positions"""
        self._extract_metadata()
        self._extract_positions()
        return self.positions, self.metadata

    def _extract_metadata(self):
        """Extract account info, date, etc. from header"""
        # Look for metadata in first few rows
        for idx in range(min(5, len(self.df))):
            row_text = ' '.join([str(x) for x in self.df.iloc[idx] if pd.notna(x)])

            # Extract account number
            if 'Conta:' in row_text:
                account_match = re.search(r'Conta:\s*(\d+)', row_text)
                if account_match:
                    self.metadata['account'] = account_match.group(1)

                # Extract position date
                date_match = re.search(r'Data da Posição Histórica:\s*(\d{2}/\d{2}/\d{4})', row_text)
                if date_match:
                    date_str = date_match.group(1)
                    self.metadata['position_date'] = datetime.strptime(date_str, '%d/%m/%Y')

            # Extract advisor info
            if 'Nome do assessor' in row_text or 'Código do Assessor' in row_text:
                for col in self.df.columns:
                    if pd.notna(self.df.iloc[idx, col]):
                        value = str(self.df.iloc[idx, col])
                        if not value.startswith('A') and not value.isdigit() and len(value) > 5:
                            self.metadata['advisor'] = value
                            break

    def _extract_positions(self):
        """Extract all investment positions from the file"""
        current_main_category = None
        current_sub_category = None
        position_date = self.metadata.get('position_date', datetime.now())

        for idx in range(len(self.df)):
            row = self.df.iloc[idx]

            # Check if this is a main category header
            first_cell = str(row[0]) if pd.notna(row[0]) else ''
            main_cat = self._identify_main_category(first_cell)
            if main_cat:
                current_main_category = main_cat
                current_sub_category = None
                continue

            # Check if this is a sub-category header
            sub_cat = self._identify_sub_category(first_cell)
            if sub_cat:
                current_sub_category = sub_cat
                continue

            # Try to extract position data
            if current_main_category and current_sub_category:
                position = self._extract_position_from_row(
                    row,
                    current_main_category,
                    current_sub_category,
                    position_date
                )
                if position:
                    self.positions.append(position)

    def _identify_main_category(self, text: str) -> Optional[str]:
        """Identify if text is a main category"""
        for pattern, category in self.MAIN_CATEGORIES.items():
            if pattern in text:
                return category
        return None

    def _identify_sub_category(self, text: str) -> Optional[str]:
        """Identify if text is a sub-category (e.g., '28,3% | Pós-Fixado')"""
        match = self.SUBCATEGORY_PATTERN.match(text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_position_from_row(
        self,
        row: pd.Series,
        main_category: str,
        sub_category: str,
        date: datetime
    ) -> Optional[InvestmentPosition]:
        """Extract position data from a row"""
        # Get position name (usually first column)
        name = str(row[0]) if pd.notna(row[0]) else None

        # Skip if name looks like a header or is too short
        if not name or len(name) < 5 or 'Posição' in name or '%' in name:
            return None

        # Try to find value in the row
        value = self._extract_value_from_row(row, main_category)
        if value is None or value == 0:
            return None

        # Extract additional data based on category
        invested_value = self._find_invested_value(row)
        percentage = self._find_percentage(row)
        quantity = self._find_quantity(row)

        return InvestmentPosition(
            name=name,
            value=value,
            main_category=main_category,
            sub_category=sub_category,
            date=date,
            invested_value=invested_value,
            percentage=percentage,
            quantity=quantity
        )

    def _extract_value_from_row(self, row: pd.Series, main_category: str) -> Optional[float]:
        """Extract the main value from a row (position value)"""
        # Different categories have values in different columns
        # Look for patterns like "R$ X,XXX.XX" or numeric values

        for col_idx in [1, 6, 7]:  # Common value positions
            if col_idx >= len(row):
                continue

            cell = row[col_idx]
            if pd.isna(cell):
                continue

            # Try to parse as monetary value
            value = self._parse_currency(str(cell))
            if value and value > 0:
                return value

        return None

    def _find_invested_value(self, row: pd.Series) -> Optional[float]:
        """Find 'Valor aplicado' in the row"""
        for idx, cell in enumerate(row):
            if pd.isna(cell):
                continue
            text = str(cell)
            if 'R$' in text and idx > 2:  # Skip name and position columns
                value = self._parse_currency(text)
                if value and value > 0:
                    return value
        return None

    def _find_percentage(self, row: pd.Series) -> Optional[float]:
        """Find percentage allocation in the row"""
        for cell in row:
            if pd.isna(cell):
                continue
            text = str(cell)
            # Look for percentage like "15,51%"
            match = re.search(r'([\d,\.]+)%', text)
            if match:
                try:
                    pct = float(match.group(1).replace(',', '.'))
                    return pct
                except ValueError:
                    continue
        return None

    def _find_quantity(self, row: pd.Series) -> Optional[int]:
        """Find quantity (for stocks, FIIs, etc.)"""
        for idx, cell in enumerate(row):
            if pd.isna(cell):
                continue
            # Look for integer values in later columns
            if idx > 5 and isinstance(cell, (int, float)) and cell > 0 and cell < 10000:
                return int(cell)
        return None

    def _parse_currency(self, text: str) -> Optional[float]:
        """Parse Brazilian currency format (R$ 1.234,56)"""
        # Remove R$ and whitespace
        text = text.replace('R$', '').strip()

        # Check if it's already a number
        if isinstance(text, (int, float)):
            return float(text)

        # Handle Brazilian format: 1.234,56 -> 1234.56
        try:
            # Remove thousand separators (.)
            text = text.replace('.', '')
            # Replace decimal separator (,) with .
            text = text.replace(',', '.')
            # Remove any remaining non-numeric characters except . and -
            text = re.sub(r'[^\d\.\-]', '', text)
            return float(text)
        except (ValueError, AttributeError):
            return None

    def get_summary(self) -> Dict:
        """Get summary statistics of parsed data"""
        if not self.positions:
            return {}

        total_value = sum(p.value for p in self.positions)
        categories = {}

        for position in self.positions:
            key = f"{position.main_category} - {position.sub_category}"
            if key not in categories:
                categories[key] = {'count': 0, 'value': 0}
            categories[key]['count'] += 1
            categories[key]['value'] += position.value

        return {
            'total_positions': len(self.positions),
            'total_value': total_value,
            'categories': categories,
            'date': self.metadata.get('position_date')
        }
