"""
Portfolio dashboard component
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database.db import Database, FIXED_CATEGORIES, PORTFOLIO_INVESTIMENTOS, PORTFOLIO_PREVIDENCIA
from utils.calculations import PortfolioCalculator
from utils.ui_helpers import currency_input


def render_dashboard_component(db: Database):
    """Render portfolio dashboard"""
    st.header("📊 Carteira de Investimento")

    # Get investimentos portfolio positions only (Previdência is a separate dashboard)
    all_positions = db.get_latest_positions(portfolio=PORTFOLIO_INVESTIMENTOS)

    if not all_positions:
        st.info("📭 Nenhuma posição encontrada. Importe seus dados primeiro!")
        return

    # Get targets for the investimentos portfolio
    targets = db.get_targets_by_portfolio(PORTFOLIO_INVESTIMENTOS)
    # Include labels with target > 0% OR reserve amount set (for Segurança)
    target_labels = set(
        t.custom_label for t in targets
        if t.target_percentage > 0
    ) if targets else set()
    reserve_label = set(
        t.custom_label for t in targets
        if t.reserve_amount and t.reserve_amount > 0
    ) if targets else set()

    # Filter positions: only include those with custom labels that have targets > 0%
    positions = [p for p in all_positions if p.custom_label in target_labels]
    excluded_positions = [p for p in all_positions if p.custom_label not in target_labels]
    reserve_positions = [p for p in all_positions if p.custom_label in reserve_label]

    # Display date and total
    position_date = all_positions[0].date
    total_value = sum(p.value for p in positions)
    total_portfolio = sum(p.value for p in all_positions)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data da Posição", position_date.strftime('%d/%m/%Y'))
    with col2:
        if len(excluded_positions) > 0:
            st.metric(
                "Valor Gerenciado",
                f"R$ {total_value:,.2f}",
                delta=f"{len(positions)} de {len(all_positions)} posições",
                help="Apenas posições com metas definidas são exibidas"
            )
        else:
            st.metric("Valor Total", f"R$ {total_value:,.2f}")
    with col3:
        st.metric("Total de Posições", len(positions))

    # Show info about excluded positions
    if excluded_positions:
        excluded_value = sum(p.value for p in excluded_positions)
        excluded_labels = set(p.custom_label if p.custom_label else "Não Classificado" for p in excluded_positions)

        with st.expander(f"ℹ️ {len(excluded_positions)} posições excluídas (R$ {excluded_value:,.2f})"):
            st.write(
                f"**Posições sem meta definida não aparecem no dashboard.** "
                f"Para incluí-las, defina metas na aba 'Classificação de Ativos'."
            )
            st.write(f"\n**Categorias excluídas:** {', '.join(sorted(excluded_labels))}")

            # Show excluded positions detail
            excluded_data = []
            for p in sorted(excluded_positions, key=lambda x: x.value, reverse=True)[:10]:
                excluded_data.append({
                    'Nome': p.name,
                    'Categoria': p.custom_label if p.custom_label else "Não Classificado",
                    'Valor': f"R$ {p.value:,.2f}"
                })

            if excluded_data:
                st.dataframe(excluded_data, use_container_width=True, hide_index=True)
                if len(excluded_positions) > 10:
                    st.caption(f"Mostrando 10 de {len(excluded_positions)} posições excluídas")

    if not positions:
        st.warning("⚠️ Nenhuma posição com meta definida. Defina metas na aba 'Classificação de Ativos'.")
        return

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Visão Geral", "Classificação de Ativos", "Detalhes por Ativo",
        "Definir Metas", "Metas por Ativo", "Rebalanceamento"
    ])

    with tab1:
        _render_overview(positions, db)

    with tab2:
        _render_mapping_management(db)

    with tab3:
        _render_asset_details(all_positions, db)

    with tab4:
        _render_target_management(db)

    with tab5:
        _render_asset_targets_management(db)

    with tab6:
        _render_rebalancing(positions, reserve_positions, db, total_value)

def _render_overview(positions, db: Database):
    """Render portfolio overview"""
    st.subheader("Distribuição")

    # Calculate allocations by custom label and sub-category
    calc = PortfolioCalculator()

    # Try custom labels first
    custom_allocation = calc.calculate_current_allocation(positions, use_custom_labels=True)
    custom_percentages = calc.calculate_allocation_percentages(custom_allocation)

    # Check if we have custom labels
    has_custom_labels = any(p.custom_label for p in positions)

    if has_custom_labels:
        st.write("**Por Categoria Personalizada**")

        # Create DataFrame for display
        alloc_data = []
        for label, value in sorted(custom_allocation.items(), key=lambda x: x[1], reverse=True):
            pct = custom_percentages[label]
            alloc_data.append({
                'Categoria': label,
                'Valor': value,
                'Valor (Formatado)': f"R$ {value:,.2f}",
                'Porcentagem': pct,
                'Porcentagem (Formatada)': f"{pct:.1f}%"
            })

        df = pd.DataFrame(alloc_data)

        # Display as donut chart
        total_value = df['Valor'].sum()

        fig = go.Figure(data=[go.Pie(
            labels=df['Categoria'],
            values=df['Valor'],
            hole=0.40,  # Creates donut effect
            hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>',
            textinfo='label+percent',
            textposition='outside'
        )])

        fig.update_layout(
            annotations=[dict(
                text=f'<b>Total</b><br>R$ {total_value:,.0f}',
                x=0.5, y=0.5,
                font_size=16,
                showarrow=False,
                align='center'
            )],
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05),
            height=500,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

        # Display as table
        st.dataframe(
            df[['Categoria', 'Valor (Formatado)', 'Porcentagem (Formatada)']].rename(columns={
                'Valor (Formatado)': 'Valor',
                'Porcentagem (Formatada)': '%'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("⚠️ Classifique seus ativos primeiro para ver a distribuição por categoria personalizada.")

    # Always show by sub-category
    st.divider()
    st.write("**Por Subcategoria Original**")

    sub_allocation = calc.calculate_current_allocation(positions, use_custom_labels=False)
    sub_percentages = calc.calculate_allocation_percentages(sub_allocation)

    sub_data = []
    for cat, value in sorted(sub_allocation.items(), key=lambda x: x[1], reverse=True):
        pct = sub_percentages[cat]
        sub_data.append({
            'Subcategoria': cat,
            'Valor': f"R$ {value:,.2f}",
            '%': f"{pct:.1f}%"
        })

    st.dataframe(sub_data, use_container_width=True, hide_index=True)


def _render_rebalancing(positions, reserve_positions, db: Database, total_value: float):
    """Render rebalancing analysis"""
    st.subheader("Análise de Rebalanceamento")

    # Use only investimentos portfolio targets
    targets = db.get_targets_by_portfolio(PORTFOLIO_INVESTIMENTOS)

    if not targets:
        st.warning("⚠️ Defina suas metas de alocação primeiro na aba 'Definir Metas'.")
        return

    # Check if assets are mapped
    unmapped_count = len([p for p in positions if not p.custom_label])
    if unmapped_count > 0:
        st.warning(f"⚠️ {unmapped_count} ativos não estão classificados. Classifique-os para uma análise completa.")

    # Calculate current allocation
    calc = PortfolioCalculator()
    current_allocation = calc.calculate_current_allocation(positions, use_custom_labels=True)
    reserve_allocation = calc.calculate_current_allocation(reserve_positions, use_custom_labels=True)

    # Build target allocations — exclude Segurança (managed by reserve amount, not %)
    target_allocations = {
        t.custom_label: t.target_percentage
        for t in targets
        if t.target_percentage > 0 and t.custom_label != "Segurança"
    }

    seguranca_info = None

    seguranca_target = db.get_target("Segurança", PORTFOLIO_INVESTIMENTOS)
    if seguranca_target and seguranca_target.reserve_amount:
        # Calculate current Segurança value
        current_seguranca = reserve_allocation.get("Segurança", 0.0)
        reserve_amount = seguranca_target.reserve_amount

        # Calculate excess
        excess = current_seguranca - reserve_amount

        if excess > 0:
            seguranca_info = {
                'type': 'excess',
                'current': current_seguranca,
                'reserve': reserve_amount,
                'excess': excess
            }
        elif excess < 0:
            seguranca_info = {
                'type': 'below',
                'current': current_seguranca,
                'reserve': reserve_amount,
                'deficit': abs(excess)
            }
        else:
            seguranca_info = {
                'type': 'exact',
                'current': current_seguranca,
                'reserve': reserve_amount
            }

    # Calculate default investment value
    if seguranca_info and seguranca_info['type'] == 'excess':
        default_investment = seguranca_info['excess']
    else:
        default_investment = 0.0

    # Display Segurança reserve info
    if seguranca_info:
        if seguranca_info['type'] == 'excess':
            st.success(
                f"✅ **Segurança acima da reserva mínima** "
                f"(Atual: R\$ {seguranca_info['current']:,.2f} \| "
                f"Reserva: R\$ {seguranca_info['reserve']:,.2f}) \n\n "
                f"**Disponível: R\$ {seguranca_info['excess']:,.2f}**"
            )
        elif seguranca_info['type'] == 'below':
            st.warning(
                f"⚠️ **Segurança abaixo do mínimo!** "
                f"(Atual: R\$ {seguranca_info['current']:,.2f} \| "
                f"Reserva: R\$ {seguranca_info['reserve']:,.2f}) \n\n "
                f"**Faltam: R\$ {seguranca_info['deficit']:,.2f}**"
            )
        else:
            st.info(
                f"ℹ️ **Segurança exatamente na reserva**\n\n"
                f"Valor: R$ {seguranca_info['current']:,.2f}"
            )

    st.write("**Novo Investimento**")
    additional_investment = currency_input(
        "Valor adicional a investir (R$)",
        key="additional_investment_input",
        initial_value=default_investment
    )

    # Create rebalancing plan
    plan = calc.create_rebalancing_plan(
        current_allocation,
        target_allocations,
        additional_investment
    )

    # Display current vs target
    st.divider()
    st.write("**Alocação Atual vs Meta**")

    comparison_data = []

    # Don't add Segurança to the table - it's only used for calculating available funds
    # The reserve status is already shown above in the status messages

    # Calculate current percentages (always relative to current total, ignoring additional investment)
    current_total = sum(a.current_value for a in plan.analyses)

    # Add all categories from the plan
    for analysis in plan.analyses:
        status_emoji = {
            'balanced': '✅',
            'overweight': '⚠️',
            'underweight': '🔴'
        }

        # Calculate percentage of current total (not including additional investment)
        current_pct = (analysis.current_value / current_total * 100) if current_total > 0 else 0

        # Calculate difference based on current percentage vs target
        diff_pct = current_pct - analysis.target_percentage

        comparison_data.append({
            'Status': status_emoji.get(analysis.status, ''),
            'Categoria': analysis.label,
            'Atual': f"{current_pct:.1f}%",
            'Meta': f"{analysis.target_percentage:.1f}%",
            'Diferença': f"{diff_pct:+.1f}%",
            'Valor Atual': f"R$ {analysis.current_value:,.2f}",
            'Ajuste Necessário': f"R$ {analysis.rebalance_amount:+,.2f}" if abs(analysis.rebalance_amount) > 1 else "✓"
        })

    st.dataframe(comparison_data, use_container_width=True, hide_index=True)

    # Display suggestions - generate custom ones based on current percentages
    st.divider()
    st.write("**Sugestões de Rebalanceamento**")

    if additional_investment > 0:
        st.info(f"Você tem R$ {additional_investment:,.2f} para investir.")

        # Find categories that need investment
        underweight = [a for a in plan.analyses if a.rebalance_amount > 0]

        if underweight:
            st.write("\nSugestão de alocação do novo investimento:")
            remaining = additional_investment

            for analysis in underweight:
                if remaining <= 0:
                    break

                amount = min(analysis.rebalance_amount, remaining)
                # Calculate current percentage of current total
                current_pct = (analysis.current_value / current_total * 100) if current_total > 0 else 0
                st.write(
                    f"  - Investir R$ {amount:,.2f} em {analysis.label} "
                    f"(atual {current_pct:.1f}% → meta {analysis.target_percentage:.1f}%)"
                )
                remaining -= amount

            if remaining > 0:
                st.write(
                    f"\nSobram R$ {remaining:,.2f}. Distribua proporcionalmente entre as categorias "
                    f"ou mantenha em reserva."
                )
    else:
        # No new investment - suggest reallocation
        overweight = [a for a in plan.analyses if a.rebalance_amount < 0]
        underweight = [a for a in plan.analyses if a.rebalance_amount > 0]

        if overweight and underweight:
            st.info("Para rebalancear sem novo investimento:")

            for analysis in overweight[:3]:  # Top 3 overweight
                current_pct = (analysis.current_value / current_total * 100) if current_total > 0 else 0
                st.write(
                    f"  - Reduzir {analysis.label}: "
                    f"R$ {abs(analysis.rebalance_amount):,.2f} "
                    f"(atual {current_pct:.1f}% → meta {analysis.target_percentage:.1f}%)"
                )

            st.write("\nAlocar em:")
            for analysis in underweight[:3]:  # Top 3 underweight
                current_pct = (analysis.current_value / current_total * 100) if current_total > 0 else 0
                st.write(
                    f"  - Aumentar {analysis.label}: "
                    f"R$ {analysis.rebalance_amount:,.2f} "
                    f"(atual {current_pct:.1f}% → meta {analysis.target_percentage:.1f}%)"
                )
        else:
            st.success("✅ Seu portfólio está balanceado!")

    # Summary metrics
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        balanced_count = sum(1 for a in plan.analyses if a.status == 'balanced')
        st.metric("Categorias Balanceadas", f"{balanced_count}/{len(plan.analyses)}")

    with col2:
        if additional_investment > 0:
            st.metric("Novo Total", f"R$ {plan.total_portfolio_value:,.2f}")
        else:
            if plan.additional_investment_needed > 0:
                st.metric("Investimento Necessário", f"R$ {plan.additional_investment_needed:,.2f}")
            else:
                st.metric("Investimento Necessário", "R$ 0,00")

    with col3:
        max_deviation = max((abs(a.difference_percentage) for a in plan.analyses), default=0)
        st.metric("Maior Desvio", f"{max_deviation:.1f}%")

    # Asset-level recommendations
    st.divider()
    st.write("**📋 Detalhamento por Ativo**")
    st.caption("Veja quanto investir ou desinvestir em cada ativo dentro de cada categoria")

    _render_asset_level_rebalancing(positions, plan, additional_investment, db)


def _render_asset_level_rebalancing(positions, plan, additional_investment, db: Database):
    """Render asset-level rebalancing recommendations"""

    # Group positions by custom label
    positions_by_label = {}
    for pos in positions:
        label = pos.custom_label if pos.custom_label else "Não Classificado"
        if label not in positions_by_label:
            positions_by_label[label] = []
        positions_by_label[label].append(pos)

    # Sort analyses by those that need action first
    sorted_analyses = sorted(plan.analyses, key=lambda a: (
        a.status == 'balanced',  # Balanced last
        -abs(a.rebalance_amount)  # Larger amounts first
    ))

    for analysis in sorted_analyses:
        if analysis.label not in positions_by_label:
            continue

        category_positions = positions_by_label[analysis.label]

        # Determine emoji and color based on status
        if analysis.status == 'balanced':
            status_emoji = "✅"
            status_text = "Balanceado"
        elif analysis.status == 'underweight':
            status_emoji = "🔴"
            status_text = "Abaixo da meta"
        else:  # overweight
            status_emoji = "⚠️"
            status_text = "Acima da meta"

        # Create expander for each category
        with st.expander(
            f"{status_emoji} **{analysis.label}** - {status_text} | "
            f"Ajuste: R$ {analysis.rebalance_amount:+,.2f}"
        ):
            # Calculate percentages for display
            current_total = sum(a.current_value for a in plan.analyses)
            current_pct = (analysis.current_value / current_total * 100) if current_total > 0 else 0

            # Show three columns: Current, Post-Investment, Target
            if additional_investment > 0:
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Atual", f"R$ {analysis.current_value:,.2f}")
                    st.metric("Alocação", f"{current_pct:.1f}%")

                with col2:
                    new_value = analysis.current_value + analysis.rebalance_amount
                    post_investment_pct = (new_value / plan.total_portfolio_value * 100) if plan.total_portfolio_value > 0 else 0
                    st.metric("Pós-Investimento", f"R$ {new_value:,.2f}")
                    st.metric("Alocação", f"{post_investment_pct:.1f}%")

                with col3:
                    target_value = (analysis.target_percentage / 100) * plan.total_portfolio_value
                    st.metric("Meta", f"R$ {target_value:,.2f}")
                    st.metric("Alocação", f"{analysis.target_percentage:.1f}%")
            else:
                # No investment - show just Current and Target
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Valor Atual", f"R$ {analysis.current_value:,.2f}")
                    st.metric("Alocação Atual", f"{current_pct:.1f}%")

                with col2:
                    target_value = (analysis.target_percentage / 100) * plan.total_portfolio_value
                    st.metric("Valor Meta", f"R$ {target_value:,.2f}")
                    st.metric("Alocação Meta", f"{analysis.target_percentage:.1f}%")

            st.divider()

            # Show current assets in this category
            st.write("**Ativos nesta categoria:**")

            # Sort assets by value
            sorted_positions = sorted(category_positions, key=lambda p: p.value, reverse=True)

            total_category_value = sum(p.value for p in sorted_positions)

            # Load per-asset targets for this category
            asset_targets = {t.asset_name: t.target_pct for t in db.get_asset_category_targets(analysis.label, PORTFOLIO_INVESTIMENTOS)}

            asset_data = []
            for pos in sorted_positions:
                pct_of_category = (pos.value / total_category_value * 100) if total_category_value > 0 else 0
                asset_row = {
                    'Ativo': pos.name,
                    'Valor Atual': f"R$ {pos.value:,.2f}",
                    '% da Categoria': f"{pct_of_category:.1f}%",
                }
                if pos.name in asset_targets:
                    diff = pct_of_category - asset_targets[pos.name]
                    asset_row['Meta %'] = f"{asset_targets[pos.name]:.1f}%"
                    asset_row['Status Ativo'] = "✅" if abs(diff) < 2 else ("⚠️ Alto" if diff > 0 else "🔴 Baixo")
                if pos.sub_category:
                    asset_row['Subcategoria'] = pos.sub_category
                asset_data.append(asset_row)

            st.dataframe(asset_data, use_container_width=True, hide_index=True)

            # Recommendations
            st.divider()

            if abs(analysis.rebalance_amount) < 10:
                st.success("✅ Esta categoria está balanceada. Nenhuma ação necessária.")
            elif analysis.rebalance_amount > 0:
                # Need to add money
                st.info(
                    f"**Ação recomendada:** Investir R$ {analysis.rebalance_amount:,.2f} nesta categoria"
                )

                st.write("**💡 Estratégias de investimento:**")

                # Post-investment category total (current holdings + the rebalance amount for this category)
                post_category_total = total_category_value + analysis.rebalance_amount

                # Strategy: Target-driven (shown first when per-asset targets exist)
                assets_with_targets = [pos for pos in sorted_positions if pos.name in asset_targets]
                assets_without_targets = [pos for pos in sorted_positions if pos.name not in asset_targets]

                if assets_with_targets:
                    st.write("**Distribuição por Meta (Metas por Ativo):**")
                    st.caption(
                        "Quanto investir em cada ativo para que a categoria inteira atinja as metas definidas. "
                        "Ativos sem meta recebem o restante proporcional ao valor atual."
                    )

                    # Compute target values for assets that have targets
                    target_values = {
                        pos.name: (asset_targets[pos.name] / 100) * post_category_total
                        for pos in assets_with_targets
                    }
                    target_investments = {
                        name: max(0.0, tv - next(p.value for p in sorted_positions if p.name == name))
                        for name, tv in target_values.items()
                    }

                    # Remaining budget for assets without targets
                    budget_used = sum(target_investments.values())
                    remaining_budget = analysis.rebalance_amount - budget_used

                    # Distribute remaining proportionally among assets without targets
                    value_no_target = sum(p.value for p in assets_without_targets)
                    no_target_investments = {}
                    for pos in assets_without_targets:
                        proportion = pos.value / value_no_target if value_no_target > 0 else (1 / len(assets_without_targets) if assets_without_targets else 0)
                        no_target_investments[pos.name] = max(0.0, remaining_budget * proportion)

                    # Pre-compute new totals so the denominator is the actual post-investment sum
                    new_totals = {}
                    for pos in sorted_positions:
                        if pos.name in target_investments:
                            new_totals[pos.name] = pos.value + target_investments[pos.name]
                        else:
                            new_totals[pos.name] = pos.value + no_target_investments.get(pos.name, 0.0)
                    actual_post_total = sum(new_totals.values())

                    target_data = []
                    for pos in sorted_positions:
                        invest = target_investments.get(pos.name, no_target_investments.get(pos.name, 0.0))
                        new_total = new_totals[pos.name]
                        new_pct = (new_total / actual_post_total * 100) if actual_post_total > 0 else 0
                        target_data.append({
                            'Ativo': pos.name,
                            'Meta %': f"{asset_targets[pos.name]:.1f}%" if pos.name in asset_targets else '—',
                            'Valor a Investir': f"R$ {invest:,.2f}",
                            'Novo Total': f"R$ {new_total:,.2f}",
                            '% Pós-Invest.': f"{new_pct:.1f}%",
                        })

                    st.dataframe(target_data, use_container_width=True, hide_index=True)
                    st.divider()

                # Fallback strategies (always shown)
                st.write("**Opção - Proporcional aos ativos atuais:**")
                prop_data = []
                for pos in sorted_positions:
                    proportion = pos.value / total_category_value if total_category_value > 0 else (1 / len(sorted_positions))
                    amount_to_invest = analysis.rebalance_amount * proportion
                    prop_data.append({
                        'Ativo': pos.name,
                        'Valor a Investir': f"R$ {amount_to_invest:,.2f}",
                        'Novo Total': f"R$ {pos.value + amount_to_invest:,.2f}"
                    })
                st.dataframe(prop_data, use_container_width=True, hide_index=True)

                st.write("**Opção - Distribuição igual:**")
                equal_amount = analysis.rebalance_amount / len(sorted_positions)
                equal_data = []
                for pos in sorted_positions:
                    equal_data.append({
                        'Ativo': pos.name,
                        'Valor a Investir': f"R$ {equal_amount:,.2f}",
                        'Novo Total': f"R$ {pos.value + equal_amount:,.2f}"
                    })
                st.dataframe(equal_data, use_container_width=True, hide_index=True)

            else:
                # Need to reduce money - only show if no additional investment
                if additional_investment == 0:
                    st.warning(
                        f"**Ação recomendada:** Reduzir R$ {abs(analysis.rebalance_amount):,.2f} desta categoria"
                    )

                    st.write("**💡 Estratégias de desinvestimento:**")
                    st.caption("⚠️ Considere adicionar novo dinheiro ao invés de vender posições existentes")

                    # Strategy 1: Proportional reduction
                    st.write("**Opção 1 - Redução proporcional:**")
                    reduction_data = []
                    for pos in sorted_positions:
                        proportion = pos.value / total_category_value if total_category_value > 0 else (1 / len(sorted_positions))
                        amount_to_reduce = abs(analysis.rebalance_amount) * proportion
                        reduction_data.append({
                            'Ativo': pos.name,
                            'Valor a Reduzir': f"R$ {amount_to_reduce:,.2f}",
                            'Novo Total': f"R$ {max(0, pos.value - amount_to_reduce):,.2f}"
                        })
                    st.dataframe(reduction_data, use_container_width=True, hide_index=True)

                    # Strategy 2: Sell specific positions
                    st.write("**Opção 2 - Vender posições específicas:**")
                    st.caption("Considere vender ativos começando pelos de menor valor ou menor performance")
                else:
                    # Has additional investment but category is still overweight
                    st.info(
                        f"💡 Esta categoria está {abs(analysis.difference_percentage):.1f}% acima da meta. "
                        f"Considere não adicionar mais recursos aqui e focar nas categorias abaixo da meta."
                    )


def _render_asset_targets_management(db: Database):
    """Set per-asset target % within each category for the Investimentos portfolio."""
    st.subheader("Metas por Ativo — Investimentos")
    st.info(
        "Defina a porcentagem máxima que cada ativo pode representar dentro de sua categoria. "
        "Útil para limitar posições concentradas (ex: Bitcoin a no máximo 20% de Antifragilidade)."
    )

    category = st.selectbox("Categoria", FIXED_CATEGORIES, key="inv_act_category")

    positions = db.get_latest_positions(portfolio=PORTFOLIO_INVESTIMENTOS)
    cat_positions = [p for p in positions if p.custom_label == category]

    if not cat_positions:
        st.info(f"Nenhuma posição classificada em '{category}'.")
        return

    cat_total = sum(p.value for p in cat_positions)
    existing_targets = {t.asset_name: t.target_pct for t in db.get_asset_category_targets(category, PORTFOLIO_INVESTIMENTOS)}

    st.write(f"**Ativos em {category}** (Total: R$ {cat_total:,.2f})")

    updated = {}
    for p in sorted(cat_positions, key=lambda x: x.value, reverse=True):
        current_pct = p.value / cat_total * 100 if cat_total > 0 else 0
        target_pct = existing_targets.get(p.name, 0.0)
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.write(f"**{p.name}**")
            st.caption(f"Atual: {current_pct:.1f}%")
        with col2:
            updated[p.name] = st.number_input(
                "Meta %",
                min_value=0.0,
                max_value=100.0,
                value=target_pct,
                step=1.0,
                key=f"inv_act_{category}_{p.name}",
                label_visibility="collapsed"
            )
        with col3:
            if target_pct > 0:
                diff = current_pct - target_pct
                badge = "✅" if abs(diff) < 2 else ("⚠️ Alto" if diff > 0 else "🔴 Baixo")
                st.write(badge)

    if st.button("💾 Salvar Metas por Ativo", type="primary", key="inv_save_act"):
        for asset_name, pct in updated.items():
            if pct > 0:
                db.add_or_update_asset_category_target(asset_name, category, PORTFOLIO_INVESTIMENTOS, pct)
            else:
                db.delete_asset_category_target(asset_name, category, PORTFOLIO_INVESTIMENTOS)
        st.success("✓ Metas por ativo salvas!")
        st.rerun()


def _render_asset_details(positions, db: Database):
    """Render detailed asset list with inline editing for invested values"""
    st.subheader("Detalhes por Ativo")

    # Filters in collapsible expander
    with st.expander("🔍 Filtros", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            main_categories = sorted(set(p.main_category for p in positions))
            selected_main = st.multiselect("Categoria Principal", main_categories, default=main_categories)

        with col2:
            sub_categories = sorted(set(p.sub_category for p in positions))
            selected_sub = st.multiselect("Subcategoria", sub_categories, default=sub_categories)

        with col3:
            custom_labels = sorted(set(p.custom_label for p in positions if p.custom_label))
            if custom_labels:
                selected_custom = st.multiselect("Categoria Personalizada", custom_labels, default=custom_labels)
            else:
                selected_custom = []

    # Filter positions
    filtered_positions = [
        p for p in positions
        if p.main_category in selected_main
        and p.sub_category in selected_sub
        and (not custom_labels or not selected_custom or p.custom_label in selected_custom)
    ]

    # Sort options (kept visible outside expander)
    sort_by = st.selectbox("Ordenar por", ["Valor (Maior)", "Valor (Menor)", "Nome"])

    if sort_by == "Valor (Maior)":
        filtered_positions.sort(key=lambda x: x.value, reverse=True)
    elif sort_by == "Valor (Menor)":
        filtered_positions.sort(key=lambda x: x.value)
    else:
        filtered_positions.sort(key=lambda x: x.name)

    # Display table with editable invested values
    if filtered_positions:
        # Prepare data for editing
        details_data = []
        position_id_map = {}  # Map row index to position ID

        for idx, p in enumerate(filtered_positions):
            # Store position ID mapping
            position_id_map[idx] = p.id

            # Calculate gain
            invested = p.invested_value if p.invested_value else 0.0
            gain = p.value - invested
            gain_pct = (gain / invested * 100) if invested > 0 else 0

            row = {
                'ID': p.id,  # Hidden column for tracking
                'Nome': p.name,
                'Valor (R$)': p.value,
                'Investido (R$)': invested,
                'Ganho (R$)': gain,
                'Ganho (%)': gain_pct,
                'Categoria': p.main_category,
                'Subcategoria': p.sub_category,
            }

            if p.custom_label:
                row['Classificação'] = p.custom_label

            details_data.append(row)

        # Create DataFrame for editing
        import pandas as pd
        df = pd.DataFrame(details_data)

        # Configure column settings
        column_config = {
            'ID': None,  # Hide ID column
            'Nome': st.column_config.TextColumn('Nome', disabled=True, width='large'),
            'Valor (R$)': st.column_config.NumberColumn('Valor', format='R$ %.2f', disabled=True),
            'Investido (R$)': st.column_config.NumberColumn('Investido', format='R$ %.2f', help='Clique para editar'),
            'Ganho (R$)': st.column_config.NumberColumn('Ganho', format='R$ %+.2f', disabled=True),
            'Ganho (%)': st.column_config.NumberColumn('Ganho %', format='%+.1f%%', disabled=True),
            'Categoria': st.column_config.TextColumn('Categoria', disabled=True),
            'Subcategoria': st.column_config.TextColumn('Subcategoria', disabled=True),
        }

        if 'Classificação' in df.columns:
            column_config['Classificação'] = st.column_config.TextColumn('Classificação', disabled=True)

        # Display editable dataframe
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key='asset_details_editor'
        )

        # Detect changes and show save button
        if not edited_df.equals(df):
            st.info("💡 Você tem alterações não salvas. Clique no botão abaixo para salvar.")

            if st.button("💾 Salvar Alterações no Valor Investido", type="primary"):
                # Find changed rows
                changes_made = 0
                for idx in range(len(df)):
                    original_invested = df.iloc[idx]['Investido (R$)']
                    edited_invested = edited_df.iloc[idx]['Investido (R$)']

                    if original_invested != edited_invested:
                        position_id = position_id_map[idx]
                        db.update_position_invested_value(position_id, edited_invested)
                        changes_made += 1

                if changes_made > 0:
                    st.success(f"✓ {changes_made} posição(ões) atualizada(s) com sucesso!")
                    st.rerun()
                else:
                    st.info("Nenhuma alteração detectada.")

        # Summary
        total_filtered = sum(p.value for p in filtered_positions)
        total_all = sum(p.value for p in positions)
        pct_filtered = (total_filtered / total_all * 100) if total_all > 0 else 0

        st.caption(
            f"Mostrando {len(filtered_positions)} posições | "
            f"Valor: R$ {total_filtered:,.2f} ({pct_filtered:.1f}% do total)"
        )
    else:
        st.info("Nenhuma posição corresponde aos filtros selecionados.")


def _render_asset_classification(db: Database):
    """Render interface to classify unmapped assets"""
    st.subheader("Ativos Não Classificados")

    unmapped_assets = db.get_unmapped_assets()

    if not unmapped_assets:
        st.success("✓ Todos os ativos estão classificados!")
        return

    st.info(f"📋 {len(unmapped_assets)} ativos precisam ser classificados.")

    # Get existing labels for suggestions
    existing_mappings = db.get_all_mappings()
    existing_labels = sorted(set(m.custom_label for m in existing_mappings))

    with st.expander("📦 Classificar múltiplos ativos de uma vez"):
        bulk_label = _select_labels_or_create_new(existing_labels)

        selected_assets = st.multiselect(
            "Selecione os Ativos",
            unmapped_assets,
            key="bulk_assets"
        )

        if st.button("💾 Classificar Selecionados", type="secondary"):
            if bulk_label and selected_assets:
                for asset in selected_assets:
                    db.add_or_update_mapping(asset, bulk_label)
                st.success(f"✓ {len(selected_assets)} ativos classificados!")
                st.rerun()
            else:
                st.error("Selecione ativos e defina uma categoria.")

    # Quick classification form
    with st.form("quick_classify"):
        st.write("**Classificação Rápida**")

        asset = st.selectbox("Selecione o Ativo", unmapped_assets)

        col1, col2 = st.columns([2, 1])

        with col1:
            custom_label = _select_labels_or_create_new(existing_labels)

        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            submitted = st.form_submit_button("💾 Salvar Classificação", type="primary")

        if submitted:
            if asset and custom_label:
                db.add_or_update_mapping(asset, custom_label)
                st.success(f"✓ '{asset}' classificado como '{custom_label}'")
                st.rerun()
            else:
                st.error("Preencha todos os campos.")


def _select_labels_or_create_new(existing_labels=None):
    """Return a fixed category selection (no free-form creation)."""
    return st.selectbox("Categoria", FIXED_CATEGORIES)


def _render_mapping_management(db: Database):
    """Render interface to manage existing mappings"""
    st.subheader("Mapeamentos Existentes")

    mappings = db.get_all_mappings()

    if not mappings:
        st.info("Nenhum mapeamento criado ainda. Classifique seus ativos na aba anterior.")
        return

    # Group by label
    by_label = {}
    for mapping in mappings:
        if mapping.custom_label not in by_label:
            by_label[mapping.custom_label] = []
        by_label[mapping.custom_label].append(mapping)

    # Display by category
    for label, maps in sorted(by_label.items()):
        with st.expander(f"**{label}** ({len(maps)} ativos)"):
            for mapping in maps:
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.write(mapping.asset_name)

                with col2:
                    default_idx = FIXED_CATEGORIES.index(mapping.custom_label) if mapping.custom_label in FIXED_CATEGORIES else 0
                    new_label = st.selectbox(
                        "Categoria",
                        FIXED_CATEGORIES,
                        index=default_idx,
                        key=f"edit_{mapping.id}",
                        label_visibility="collapsed"
                    )

                with col3:
                    if st.button("🗑️", key=f"delete_{mapping.id}", help="Deletar mapeamento"):
                        db.delete_mapping(mapping.asset_name)
                        st.rerun()

                    if new_label != mapping.custom_label:
                        if st.button("💾", key=f"save_{mapping.id}", help="Salvar alteração"):
                            db.add_or_update_mapping(mapping.asset_name, new_label, PORTFOLIO_INVESTIMENTOS)
                            st.rerun()
    
    st.divider()
    _render_asset_classification(db)

    # Statistics
    st.divider()
    st.subheader("Estatísticas")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Categorias", len(by_label))
    with col2:
        st.metric("Total de Mapeamentos", len(mappings))


def _render_target_management(db: Database):
    """Render interface to manage target allocations"""
    st.subheader("Definir Metas — Investimentos")

    st.info(
        "Defina a porcentagem alvo para cada categoria da **Carteira de Investimentos**. "
        "A soma deve ser 100%. Previdência é gerenciada separadamente."
    )

    # Get existing targets for investimentos portfolio (4 fixed categories only)
    existing_targets = db.get_targets_by_portfolio(PORTFOLIO_INVESTIMENTOS)
    targets_dict = {
        t.custom_label: t.target_percentage
        for t in existing_targets
        if t.custom_label != "Segurança"
    }

    with st.form("target_form"):
        st.write("Porcentagem alvo por categoria:")

        targets_input = {}
        total_percentage = 0.0

        for label in FIXED_CATEGORIES:
            current_target = targets_dict.get(label, 0.0)
            targets_input[label] = st.number_input(
                f"{label} (%)",
                min_value=0.0,
                max_value=100.0,
                value=current_target,
                step=1.0,
                key=f"target_{label}"
            )
            total_percentage += targets_input[label]

        if abs(total_percentage - 100.0) < 0.01:
            st.success(f"✓ Total: {total_percentage:.1f}%")
        else:
            st.warning(f"⚠️ Total: {total_percentage:.1f}% (deve somar 100%)")

        submitted = st.form_submit_button("💾 Salvar Metas", type="primary")

        if submitted:
            if abs(total_percentage - 100.0) > 0.1:
                st.error("A soma das porcentagens deve ser 100%!")
            else:
                for label, target_pct in targets_input.items():
                    db.add_or_update_target(label, PORTFOLIO_INVESTIMENTOS, target_pct)
                st.success("✓ Metas salvas com sucesso!")
                st.rerun()

    # Segurança reserve amount
    st.divider()
    st.subheader("Reserva de Segurança")
    st.info("Segurança é gerenciada por um valor mínimo em R$, não por porcentagem.")

    seguranca_target = db.get_target("Segurança", PORTFOLIO_INVESTIMENTOS)
    current_reserve = seguranca_target.reserve_amount if (seguranca_target and seguranca_target.reserve_amount) else 0.0

    new_reserve = currency_input(
        "Valor mínimo da Reserva de Segurança (R$)",
        key="seguranca_reserve_input",
        initial_value=current_reserve
    )

    if st.button("💾 Salvar Reserva de Segurança", type="secondary"):
        db.add_or_update_target("Segurança", PORTFOLIO_INVESTIMENTOS, 0.0, new_reserve)
        st.success(f"✓ Reserva de Segurança definida: R$ {new_reserve:,.2f}")
        st.rerun()

    # Display current targets
    st.divider()
    st.subheader("Metas Atuais")
    active_targets = [t for t in existing_targets if t.custom_label != "Segurança" and t.target_percentage > 0]
    if active_targets:
        for t in sorted(active_targets, key=lambda x: x.target_percentage, reverse=True):
            col1, col2 = st.columns([3, 2])
            with col1:
                st.write(t.custom_label)
            with col2:
                st.write(f"{t.target_percentage:.1f}%")
    else:
        st.info("Nenhuma meta definida ainda.")
