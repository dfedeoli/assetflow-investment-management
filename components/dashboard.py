"""
Portfolio dashboard component
"""

import streamlit as st
import pandas as pd
from database.db import Database
from utils.calculations import PortfolioCalculator


def render_dashboard_component(db: Database):
    """Render portfolio dashboard"""
    st.header("📊 Dashboard do Portfólio")

    # Get latest positions
    all_positions = db.get_latest_positions()

    if not all_positions:
        st.info("📭 Nenhuma posição encontrada. Importe seus dados primeiro!")
        return

    # Get targets to filter positions (exclude labels with 0% target)
    targets = db.get_all_targets()
    target_labels = set(t.custom_label for t in targets if t.target_percentage > 0) if targets else set()

    # Filter positions: only include those with custom labels that have targets > 0%
    positions = [p for p in all_positions if p.custom_label in target_labels]
    excluded_positions = [p for p in all_positions if p.custom_label not in target_labels]

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
    tab1, tab2, tab3 = st.tabs(["Visão Geral", "Rebalanceamento", "Detalhes por Ativo"])

    with tab1:
        _render_overview(positions, db)

    with tab2:
        _render_rebalancing(positions, db, total_value)

    with tab3:
        # Show all positions in asset details, not just managed ones
        _render_asset_details(all_positions)


def _render_overview(positions, db: Database):
    """Render portfolio overview"""
    st.subheader("Distribuição do Portfólio")

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

        # Display as bar chart
        st.bar_chart(df.set_index('Categoria')['Valor'], use_container_width=True)

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


def _render_rebalancing(positions, db: Database, total_value: float):
    """Render rebalancing analysis"""
    st.subheader("Análise de Rebalanceamento")

    # Check if we have targets and mappings
    targets = db.get_all_targets()

    if not targets:
        st.warning("⚠️ Defina suas metas de alocação primeiro na aba 'Classificação de Ativos'.")
        return

    # Check if assets are mapped
    unmapped_count = len(db.get_unmapped_assets())
    if unmapped_count > 0:
        st.warning(f"⚠️ {unmapped_count} ativos não estão classificados. Classifique-os para uma análise completa.")

    # Calculate current allocation
    calc = PortfolioCalculator()
    current_allocation = calc.calculate_current_allocation(positions, use_custom_labels=True)

    # Get target allocations (exclude 0% targets)
    target_allocations = {t.custom_label: t.target_percentage for t in targets if t.target_percentage > 0}

    # Input for additional investment
    st.write("**Novo Investimento**")
    additional_investment = st.number_input(
        "Valor adicional a investir (R$)",
        min_value=0.0,
        value=0.0,
        step=1000.0,
        help="Deixe em 0 para ver apenas o status atual"
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
    for analysis in plan.analyses:
        status_emoji = {
            'balanced': '✅',
            'overweight': '⚠️',
            'underweight': '🔴'
        }

        comparison_data.append({
            'Status': status_emoji.get(analysis.status, ''),
            'Categoria': analysis.label,
            'Atual': f"{analysis.current_percentage:.1f}%",
            'Meta': f"{analysis.target_percentage:.1f}%",
            'Diferença': f"{analysis.difference_percentage:+.1f}%",
            'Valor Atual': f"R$ {analysis.current_value:,.2f}",
            'Ajuste Necessário': f"R$ {analysis.rebalance_amount:+,.2f}" if abs(analysis.rebalance_amount) > 1 else "✓"
        })

    st.dataframe(comparison_data, use_container_width=True, hide_index=True)

    # Display suggestions
    if plan.suggestions:
        st.divider()
        st.write("**Sugestões de Rebalanceamento**")

        for suggestion in plan.suggestions:
            if suggestion.startswith('\n'):
                st.write(suggestion.strip())
            elif suggestion.startswith('  -'):
                st.write(suggestion)
            else:
                st.info(suggestion)

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

    _render_asset_level_rebalancing(positions, plan, additional_investment)


def _render_asset_level_rebalancing(positions, plan, additional_investment):
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
            f"Ajuste: R$ {analysis.rebalance_amount:+,.2f}",
            expanded=(analysis.status != 'balanced' and abs(analysis.rebalance_amount) > 100)
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Valor Atual", f"R$ {analysis.current_value:,.2f}")
                st.metric("Alocação Atual", f"{analysis.current_percentage:.2f}%")

            with col2:
                target_value = (analysis.target_percentage / 100) * plan.total_portfolio_value
                st.metric("Valor Meta", f"R$ {target_value:,.2f}")
                st.metric("Alocação Meta", f"{analysis.target_percentage:.2f}%")

            st.divider()

            # Show current assets in this category
            st.write("**Ativos nesta categoria:**")

            # Sort assets by value
            sorted_positions = sorted(category_positions, key=lambda p: p.value, reverse=True)

            asset_data = []
            total_category_value = sum(p.value for p in sorted_positions)

            for pos in sorted_positions:
                pct_of_category = (pos.value / total_category_value * 100) if total_category_value > 0 else 0

                asset_row = {
                    'Ativo': pos.name,
                    'Valor Atual': f"R$ {pos.value:,.2f}",
                    '% da Categoria': f"{pct_of_category:.1f}%",
                }

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

                # Suggest distribution strategy
                st.write("**💡 Estratégias de investimento:**")

                # Strategy 1: Proportional to current holdings
                st.write("**Opção 1 - Proporcional aos ativos atuais:**")
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

                # Strategy 2: Equal distribution
                st.write("**Opção 2 - Distribuição igual:**")
                equal_amount = analysis.rebalance_amount / len(sorted_positions)
                equal_data = []
                for pos in sorted_positions:
                    equal_data.append({
                        'Ativo': pos.name,
                        'Valor a Investir': f"R$ {equal_amount:,.2f}",
                        'Novo Total': f"R$ {pos.value + equal_amount:,.2f}"
                    })
                st.dataframe(equal_data, use_container_width=True, hide_index=True)

                # Strategy 3: Focus on specific assets
                if len(sorted_positions) > 1:
                    st.write("**Opção 3 - Escolha manual:**")
                    st.caption("Selecione os ativos e distribua o investimento conforme sua estratégia")

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


def _render_asset_details(positions):
    """Render detailed asset list"""
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

    # Display table
    if filtered_positions:
        details_data = []
        for p in filtered_positions:
            row = {
                'Nome': p.name,
                'Valor': f"R$ {p.value:,.2f}",
                'Categoria': p.main_category,
                'Subcategoria': p.sub_category,
            }

            if p.custom_label:
                row['Classificação'] = p.custom_label

            if p.invested_value:
                gain = p.value - p.invested_value
                gain_pct = (gain / p.invested_value * 100) if p.invested_value > 0 else 0
                row['Investido'] = f"R$ {p.invested_value:,.2f}"
                row['Ganho'] = f"R$ {gain:+,.2f} ({gain_pct:+.1f}%)"

            details_data.append(row)

        st.dataframe(details_data, use_container_width=True, hide_index=True)

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
