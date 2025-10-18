"""
PGBL Tax Calculator Utility Functions

Calculations based on Brazilian tax rules for PGBL (Plano Gerador de Benefício Livre):
- Allows deduction of up to 12% of annual gross taxable income
- Taxable income includes: salaries, vacation pay, vacation bonus (1/3), pensions, rental income
- Non-taxable (excluded): 13th salary, PLR (Profit Sharing), severance payments
- Requirement: Must contribute to INSS or public pension system
"""

from typing import List, Dict, Tuple
from database.models import AnnualIncomeEntry


# Income type constants
INCOME_TYPES = {
    'salary': 'Salário',
    'vacation': 'Férias',
    'vacation_bonus': '1/3 Férias',
    'pension': 'Pensão/Aposentadoria',
    'rental': 'Aluguel',
    'thirteenth': '13º Salário',
    'plr': 'PLR',
    'other': 'Outro'
}

# Non-taxable income types (excluded from PGBL calculation)
NON_TAXABLE_TYPES = ['thirteenth', 'plr']


def calculate_taxable_income(entries: List[AnnualIncomeEntry]) -> float:
    """
    Calculate total taxable income from entries.
    Excludes 13th salary and PLR (they have exclusive taxation).

    Args:
        entries: List of income entries

    Returns:
        Total taxable income amount
    """
    taxable_total = 0.0

    for entry in entries:
        if entry.is_taxable:
            taxable_total += entry.amount

    return taxable_total


def calculate_pgbl_limit(taxable_income: float) -> float:
    """
    Calculate the maximum PGBL contribution that can be deducted (12% of taxable income).

    Args:
        taxable_income: Annual gross taxable income

    Returns:
        Maximum deductible PGBL contribution (12% of taxable income)
    """
    return taxable_income * 0.12


def calculate_remaining_investment(pgbl_limit: float, current_pgbl_contributions: float) -> float:
    """
    Calculate how much more can be invested in PGBL to reach the 12% limit.

    Args:
        pgbl_limit: Maximum deductible amount (12% of taxable income)
        current_pgbl_contributions: Amount already invested in PGBL this year

    Returns:
        Remaining amount that can be invested (can be negative if over limit)
    """
    return pgbl_limit - current_pgbl_contributions


def project_annual_income(ytd_income: float, months_entered: int) -> float:
    """
    Project annual income based on year-to-date data.

    Args:
        ytd_income: Total income for months entered so far
        months_entered: Number of months with data

    Returns:
        Projected annual income (extrapolated to 12 months)
    """
    if months_entered == 0:
        return 0.0

    avg_monthly = ytd_income / months_entered
    return avg_monthly * 12


def calculate_tax_benefit(contribution: float, tax_bracket: float = 0.275) -> float:
    """
    Estimate tax savings from PGBL contribution.

    The PGBL allows you to deduct contributions from your taxable base,
    so you save the tax you would have paid on that amount.

    Args:
        contribution: Amount contributed to PGBL
        tax_bracket: Your marginal tax rate (default 27.5% - highest bracket)

    Returns:
        Estimated tax savings
    """
    return contribution * tax_bracket


def categorize_income_by_type(entries: List[AnnualIncomeEntry]) -> Dict[str, float]:
    """
    Group income entries by type and sum amounts.

    Args:
        entries: List of income entries

    Returns:
        Dictionary mapping entry_type to total amount
    """
    categories = {}

    for entry in entries:
        if entry.entry_type not in categories:
            categories[entry.entry_type] = 0.0
        categories[entry.entry_type] += entry.amount

    return categories


def categorize_income_by_month(entries: List[AnnualIncomeEntry]) -> Dict[int, float]:
    """
    Group income entries by month and sum amounts.

    Args:
        entries: List of income entries

    Returns:
        Dictionary mapping month (1-12) to total income
    """
    monthly = {}

    for entry in entries:
        if entry.month not in monthly:
            monthly[entry.month] = 0.0
        monthly[entry.month] += entry.amount

    return monthly


def calculate_completion_percentage(pgbl_limit: float, current_pgbl_contributions: float) -> float:
    """
    Calculate what percentage of the PGBL limit has been used.

    Args:
        pgbl_limit: Maximum deductible amount (12% of taxable income)
        current_pgbl_contributions: Amount already invested in PGBL this year

    Returns:
        Percentage of limit used (0-100+, can exceed 100 if over limit)
    """
    if pgbl_limit == 0:
        return 0.0

    return (current_pgbl_contributions / pgbl_limit) * 100


def get_status_info(completion_pct: float) -> Tuple[str, str, str]:
    """
    Get status information based on completion percentage.

    Args:
        completion_pct: Percentage of PGBL limit used

    Returns:
        Tuple of (status, emoji, color) where:
        - status: Text status ("optimized", "room_to_invest", "over_limit")
        - emoji: Emoji for visual indicator
        - color: Streamlit color for status ("green", "yellow", "red")
    """
    if completion_pct >= 100:
        return ("optimized", "✅", "green")
    elif completion_pct >= 90:
        return ("almost_complete", "⚠️", "orange")
    else:
        return ("room_to_invest", "📊", "blue")


def calculate_days_until_deadline(current_year: int) -> int:
    """
    Calculate days remaining until December 31st deadline for PGBL contributions.

    Args:
        current_year: Current year

    Returns:
        Number of days until deadline
    """
    from datetime import datetime

    today = datetime.now()
    deadline = datetime(current_year, 12, 31, 23, 59, 59)

    if today > deadline:
        return 0

    delta = deadline - today
    return delta.days


def get_income_type_display_name(entry_type: str) -> str:
    """
    Get display name for income type.

    Args:
        entry_type: Income type code

    Returns:
        Display name in Portuguese
    """
    return INCOME_TYPES.get(entry_type, entry_type.capitalize())


def is_taxable_income_type(entry_type: str) -> bool:
    """
    Check if an income type is taxable for PGBL purposes.

    Args:
        entry_type: Income type code

    Returns:
        True if taxable, False if excluded (13th salary, PLR)
    """
    return entry_type not in NON_TAXABLE_TYPES
