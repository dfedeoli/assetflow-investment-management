"""
Calculation utilities for portfolio analysis and rebalancing
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class AllocationAnalysis:
    """Analysis of current vs target allocation"""
    label: str
    current_value: float
    current_percentage: float
    target_percentage: float
    difference_percentage: float
    rebalance_amount: float  # Positive = need to add, Negative = need to reduce
    status: str  # 'overweight', 'underweight', 'balanced'


@dataclass
class RebalancingPlan:
    """Complete rebalancing plan"""
    total_portfolio_value: float
    analyses: List[AllocationAnalysis]
    additional_investment_needed: float
    suggestions: List[str]


class PortfolioCalculator:
    """Calculate portfolio metrics and rebalancing recommendations"""

    TOLERANCE = 0.5  # 0.5% tolerance for "balanced"

    @staticmethod
    def calculate_current_allocation(positions: List, use_custom_labels: bool = True) -> Dict[str, float]:
        """
        Calculate current allocation by category

        Args:
            positions: List of Position objects
            use_custom_labels: If True, group by custom_label, else by sub_category

        Returns:
            Dictionary of {category: total_value}
        """
        allocation = {}

        for position in positions:
            if use_custom_labels:
                key = position.custom_label if position.custom_label else "Não Classificado"
            else:
                key = position.sub_category

            if key not in allocation:
                allocation[key] = 0.0

            allocation[key] += position.value

        return allocation

    @staticmethod
    def calculate_allocation_percentages(allocation: Dict[str, float]) -> Dict[str, float]:
        """Calculate percentage allocation"""
        total = sum(allocation.values())

        if total == 0:
            return {k: 0.0 for k in allocation.keys()}

        return {k: (v / total * 100) for k, v in allocation.items()}

    @staticmethod
    def analyze_allocation(
        current_allocation: Dict[str, float],
        target_allocations: Dict[str, float]
    ) -> List[AllocationAnalysis]:
        """
        Analyze current vs target allocation

        Args:
            current_allocation: {label: current_value}
            target_allocations: {label: target_percentage}

        Returns:
            List of AllocationAnalysis objects
        """
        total_value = sum(current_allocation.values())
        current_percentages = PortfolioCalculator.calculate_allocation_percentages(current_allocation)

        analyses = []

        # Get all labels (from both current and target)
        all_labels = set(current_allocation.keys()) | set(target_allocations.keys())

        for label in all_labels:
            current_value = current_allocation.get(label, 0.0)
            current_pct = current_percentages.get(label, 0.0)
            target_pct = target_allocations.get(label, 0.0)

            diff_pct = current_pct - target_pct

            # Calculate rebalance amount
            target_value = (target_pct / 100) * total_value
            rebalance_amount = target_value - current_value

            # Determine status
            if abs(diff_pct) <= PortfolioCalculator.TOLERANCE:
                status = 'balanced'
            elif diff_pct > 0:
                status = 'overweight'
            else:
                status = 'underweight'

            analyses.append(AllocationAnalysis(
                label=label,
                current_value=current_value,
                current_percentage=current_pct,
                target_percentage=target_pct,
                difference_percentage=diff_pct,
                rebalance_amount=rebalance_amount,
                status=status
            ))

        # Sort by absolute difference (most out of balance first)
        analyses.sort(key=lambda x: abs(x.difference_percentage), reverse=True)

        return analyses

    @staticmethod
    def create_rebalancing_plan(
        current_allocation: Dict[str, float],
        target_allocations: Dict[str, float],
        additional_investment: float = 0.0
    ) -> RebalancingPlan:
        """
        Create a complete rebalancing plan

        Args:
            current_allocation: {label: current_value}
            target_allocations: {label: target_percentage}
            additional_investment: Additional money to invest

        Returns:
            RebalancingPlan object
        """
        total_value = sum(current_allocation.values())
        new_total = total_value + additional_investment

        # Recalculate with new total
        analyses = []
        all_labels = set(current_allocation.keys()) | set(target_allocations.keys())

        for label in all_labels:
            current_value = current_allocation.get(label, 0.0)
            current_pct = (current_value / total_value * 100) if total_value > 0 else 0
            target_pct = target_allocations.get(label, 0.0)

            # Calculate target value with new total
            target_value = (target_pct / 100) * new_total
            rebalance_amount = target_value - current_value

            # Current percentage relative to NEW total
            new_current_pct = (current_value / new_total * 100) if new_total > 0 else 0
            diff_pct = new_current_pct - target_pct

            # Determine status
            if abs(diff_pct) <= PortfolioCalculator.TOLERANCE:
                status = 'balanced'
            elif diff_pct > 0:
                status = 'overweight'
            else:
                status = 'underweight'

            analyses.append(AllocationAnalysis(
                label=label,
                current_value=current_value,
                current_percentage=new_current_pct,
                target_percentage=target_pct,
                difference_percentage=diff_pct,
                rebalance_amount=rebalance_amount,
                status=status
            ))

        # Sort by status and difference
        analyses.sort(key=lambda x: (x.status != 'underweight', abs(x.difference_percentage)), reverse=True)

        # Generate suggestions
        suggestions = PortfolioCalculator._generate_suggestions(analyses, additional_investment)

        return RebalancingPlan(
            total_portfolio_value=new_total,
            analyses=analyses,
            additional_investment_needed=0 if additional_investment > 0 else sum(
                max(0, a.rebalance_amount) for a in analyses
            ),
            suggestions=suggestions
        )

    @staticmethod
    def _generate_suggestions(analyses: List[AllocationAnalysis], additional_investment: float) -> List[str]:
        """Generate human-readable rebalancing suggestions"""
        suggestions = []

        if additional_investment > 0:
            suggestions.append(f"Você tem R$ {additional_investment:,.2f} para investir.")

            # Suggest allocation for new money
            underweight = [a for a in analyses if a.status == 'underweight' and a.rebalance_amount > 0]

            if underweight:
                suggestions.append("\nSugestão de alocação do novo investimento:")
                remaining = additional_investment

                for analysis in underweight:
                    if remaining <= 0:
                        break

                    amount = min(analysis.rebalance_amount, remaining)
                    suggestions.append(
                        f"  - Investir R$ {amount:,.2f} em {analysis.label} "
                        f"({analysis.current_percentage:.1f}% → {analysis.target_percentage:.1f}%)"
                    )
                    remaining -= amount

                if remaining > 0:
                    # Distribute remaining proportionally
                    suggestions.append(
                        f"\nSobram R$ {remaining:,.2f}. Distribua proporcionalmente entre as categorias "
                        f"ou mantenha em reserva."
                    )
        else:
            # No new investment - suggest reallocation
            overweight = [a for a in analyses if a.status == 'overweight']
            underweight = [a for a in analyses if a.status == 'underweight']

            if overweight and underweight:
                suggestions.append("Para rebalancear sem novo investimento:")

                for analysis in overweight[:3]:  # Top 3 overweight
                    suggestions.append(
                        f"  - Reduzir {analysis.label}: "
                        f"R$ {abs(analysis.rebalance_amount):,.2f} "
                        f"({analysis.current_percentage:.1f}% → {analysis.target_percentage:.1f}%)"
                    )

                suggestions.append("\nAlocar em:")
                for analysis in underweight[:3]:  # Top 3 underweight
                    suggestions.append(
                        f"  - Aumentar {analysis.label}: "
                        f"R$ {analysis.rebalance_amount:,.2f} "
                        f"({analysis.current_percentage:.1f}% → {analysis.target_percentage:.1f}%)"
                    )

        return suggestions

    @staticmethod
    def calculate_historical_growth(
        old_allocation: Dict[str, float],
        new_allocation: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        Calculate growth between two time periods

        Returns:
            {label: {'old_value': float, 'new_value': float, 'growth': float, 'growth_pct': float}}
        """
        all_labels = set(old_allocation.keys()) | set(new_allocation.keys())
        growth_data = {}

        for label in all_labels:
            old_value = old_allocation.get(label, 0.0)
            new_value = new_allocation.get(label, 0.0)
            growth = new_value - old_value
            growth_pct = (growth / old_value * 100) if old_value > 0 else 0

            growth_data[label] = {
                'old_value': old_value,
                'new_value': new_value,
                'growth': growth,
                'growth_pct': growth_pct
            }

        return growth_data
