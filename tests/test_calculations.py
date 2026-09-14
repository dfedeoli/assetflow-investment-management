"""
Regression tests for rebalancing budget math.

Run directly with: python3 tests/test_calculations.py
(no pytest dependency required - uses plain asserts)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.calculations import PortfolioCalculator


def test_capped_investment_amounts_never_exceed_additional_investment():
    """
    Multiple underweight categories competing for one additional_investment pool:
    the sum of what's actually allocated per category must never exceed the pool.
    """
    current_allocation = {
        "Diversificação": 74077.74,
        "Estabilidade": 30000.0,
        "Valorização": 20000.0,
    }
    target_allocations = {
        "Diversificação": 40.0,
        "Estabilidade": 22.5,
        "Valorização": 30.0,
    }
    additional_investment = 20000.0

    plan = PortfolioCalculator.create_rebalancing_plan(
        current_allocation, target_allocations, additional_investment
    )

    total_capped = sum(a.capped_investment_amount for a in plan.analyses)
    assert total_capped <= additional_investment + 0.01, (
        f"Sum of capped category amounts ({total_capped}) exceeds the actual "
        f"additional_investment ({additional_investment})"
    )
    for a in plan.analyses:
        assert a.capped_investment_amount <= max(a.rebalance_amount, 0) + 0.01, (
            f"{a.label}: capped amount ({a.capped_investment_amount}) exceeds its own "
            f"uncapped rebalance_amount ({a.rebalance_amount})"
        )
    print("test_capped_investment_amounts_never_exceed_additional_investment: PASS")


def test_asset_investments_fit_within_category_budget_reproducing_user_bug():
    """
    Reproduces the reported bug: a category needs R$18k per the category-level
    budget, but one asset has a per-asset target far above its near-zero current
    value, which previously caused the per-asset table to recommend investing
    far more than the category budget.
    """
    category_budget = 18000.0  # the amount actually allocated to this category

    assets_with_targets = [
        ("Fund A", 34889.71, 25.0),
        ("Fund B", 17835.39, 24.0),
        ("Fund C", 15853.28, 24.0),
        ("Fund D", 0.01, 24.0),  # near-zero balance, 24% target
    ]
    assets_without_targets = [
        ("Fund E", 5934.86),
    ]

    investments = PortfolioCalculator.fit_asset_investments_to_budget(
        assets_with_targets=assets_with_targets,
        assets_without_targets=assets_without_targets,
        budget=category_budget,
    )

    total_invested = sum(investments.values())
    assert total_invested <= category_budget + 0.01, (
        f"Per-asset investments sum to {total_invested}, exceeding the category "
        f"budget of {category_budget} - this is the bug the user hit."
    )
    assert total_invested >= category_budget - 0.01, (
        "Full budget should be allocated when demand exceeds supply"
    )
    for name, amount in investments.items():
        assert amount >= 0, f"{name}: negative investment ({amount})"
    print("test_asset_investments_fit_within_category_budget_reproducing_user_bug: PASS")


def test_asset_investments_leave_remainder_for_untargeted_assets_when_under_budget():
    """When targeted assets don't consume the whole budget, untargeted assets get the rest."""
    category_budget = 10000.0
    assets_with_targets = [
        ("Asset A", 1000.0, 20.0),  # small target gap
    ]
    assets_without_targets = [
        ("Asset B", 3000.0),
        ("Asset C", 1000.0),
    ]

    investments = PortfolioCalculator.fit_asset_investments_to_budget(
        assets_with_targets=assets_with_targets,
        assets_without_targets=assets_without_targets,
        budget=category_budget,
    )

    total_invested = sum(investments.values())
    assert abs(total_invested - category_budget) < 0.01, (
        f"Expected full budget ({category_budget}) to be distributed, got {total_invested}"
    )
    assert investments["Asset B"] > 0
    assert investments["Asset C"] > 0
    print("test_asset_investments_leave_remainder_for_untargeted_assets_when_under_budget: PASS")


def test_no_new_money_behaves_as_before():
    """With additional_investment=0, capped_investment_amount stays 0 and doesn't affect anything."""
    current_allocation = {"A": 100.0, "B": 50.0}
    target_allocations = {"A": 50.0, "B": 50.0}

    plan = PortfolioCalculator.create_rebalancing_plan(current_allocation, target_allocations, 0.0)

    for a in plan.analyses:
        assert a.capped_investment_amount == 0.0
    print("test_no_new_money_behaves_as_before: PASS")


if __name__ == "__main__":
    test_capped_investment_amounts_never_exceed_additional_investment()
    test_asset_investments_fit_within_category_budget_reproducing_user_bug()
    test_asset_investments_leave_remainder_for_untargeted_assets_when_under_budget()
    test_no_new_money_behaves_as_before()
    print("\nAll tests passed.")
