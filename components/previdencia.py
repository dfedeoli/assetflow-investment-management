"""
Previdencia specialized component with sub-classification
"""

import streamlit as st
import pandas as pd
from database.db import Database
from utils.calculations import PortfolioCalculator


def render_previdencia_component(db: Database):
    """Render Previdencia specialized dashboard"""
    st.header("💼 Previdência Privada")

    # Get Previdencia positions
    positions = db.get_positions_by_custom_label("Previdência")

    if not positions:
        st.info("📭 Nenhuma posição de Previdência encontrada.")
        st.write("Classifique seus ativos de previdência na aba 'Classificação de Ativos' primeiro.")
        return

    # Display summary
    total_value = sum(p.value for p in positions)
    position_date = positions[0].date

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data da Posição", position_date.strftime('%d/%m/%Y'))
    with col2:
        st.metric("Valor Total Previdência", f"R$ {total_value:,.2f}")
    with col3:
        st.metric("Total de Posições", len(positions))

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "Visão Geral",
        "Sub-Classificação",
        "Definir Metas",
        "Rebalanceamento"
    ])

    with tab1:
        _render_overview(positions, db)

    with tab2:
        _render_sub_classification(positions, db)

    with tab3:
        _render_target_management(db)

    with tab4:
        _render_rebalancing(positions, db, total_value)


def _render_overview(positions, db: Database):
    """Render overview of Previdencia positions"""
    st.subheader("Distribuição da Previdência")

    # Check if we have sub-labels
    has_sub_labels = any(p.sub_label for p in positions)

    if has_sub_labels:
        # Group by sub-label
        sub_allocation = {}
        for p in positions:
            key = p.sub_label if p.sub_label else "Não Classificado"
            if key not in sub_allocation:
                sub_allocation[key] = 0.0
            sub_allocation[key] += p.value

        total = sum(sub_allocation.values())

        # Create DataFrame
        alloc_data = []
        for sub_label, value in sorted(sub_allocation.items(), key=lambda x: x[1], reverse=True):
            pct = (value / total * 100) if total > 0 else 0
            alloc_data.append({
                'Sub-Categoria': sub_label,
                'Valor': value,
                'Valor (Formatado)': f"R$ {value:,.2f}",
                'Porcentagem': pct,
                'Porcentagem (Formatada)': f"{pct:.1f}%"
            })

        df = pd.DataFrame(alloc_data)

        # Display as bar chart
        st.bar_chart(df.set_index('Sub-Categoria')['Valor'], use_container_width=True)

        # Display as table
        st.dataframe(
            df[['Sub-Categoria', 'Valor (Formatado)', 'Porcentagem (Formatada)']].rename(columns={
                'Valor (Formatado)': 'Valor',
                'Porcentagem (Formatada)': '%'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("⚠️ Sub-classifique seus ativos de previdência na aba 'Sub-Classificação'.")

    # Show all positions
    st.divider()
    st.subheader("Todas as Posições de Previdência")

    details_data = []
    for p in sorted(positions, key=lambda x: x.value, reverse=True):
        row = {
            'Nome': p.name,
            'Valor': f"R$ {p.value:,.2f}",
            'Sub-Categoria': p.sub_label if p.sub_label else "Não Classificado"
        }

        if p.invested_value:
            gain = p.value - p.invested_value
            gain_pct = (gain / p.invested_value * 100) if p.invested_value > 0 else 0
            row['Investido'] = f"R$ {p.invested_value:,.2f}"
            row['Ganho'] = f"R$ {gain:+,.2f} ({gain_pct:+.1f}%)"

        details_data.append(row)

    st.dataframe(details_data, use_container_width=True, hide_index=True)


def _render_sub_classification(positions, db: Database):
    """Render sub-classification management"""
    st.subheader("Sub-Classificação de Previdência")

    st.markdown("""
    Classifique seus ativos de previdência em subcategorias para melhor análise.
    Por exemplo: Conservadora, Moderada, Agressiva, etc.
    """)

    # Get unmapped sub-assets
    unmapped_assets = db.get_unmapped_sub_assets("Previdência")

    # Get existing sub-label mappings
    existing_mappings = db.get_all_sub_label_mappings("Previdência")
    existing_sub_labels = sorted(set(m.sub_label for m in existing_mappings))

    if unmapped_assets:
        st.write(f"**{len(unmapped_assets)} ativos precisam de sub-classificação**")

        # Quick classification form
        with st.form("quick_sub_classify"):
            st.write("**Classificação Rápida**")

            asset = st.selectbox("Selecione o Ativo", unmapped_assets)

            col1, col2 = st.columns([2, 1])

            with col1:
                # Allow selecting existing or creating new
                label_option = st.radio(
                    "Opção",
                    ["Usar Sub-Categoria Existente", "Criar Nova Sub-Categoria"],
                    horizontal=True
                )

                if label_option == "Usar Sub-Categoria Existente":
                    if existing_sub_labels:
                        sub_label = st.selectbox("Sub-Categoria", existing_sub_labels)
                    else:
                        st.warning("Nenhuma sub-categoria existente. Crie uma nova.")
                        sub_label = st.text_input("Nova Sub-Categoria")
                else:
                    sub_label = st.text_input(
                        "Nome da Nova Sub-Categoria",
                        placeholder="Ex: Conservadora, Moderada, Agressiva"
                    )

            with col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                submitted = st.form_submit_button("💾 Salvar Sub-Classificação", type="primary")

            if submitted:
                if asset and sub_label:
                    db.add_or_update_sub_label_mapping(asset, "Previdência", sub_label)
                    st.success(f"✓ '{asset}' sub-classificado como '{sub_label}'")
                    st.rerun()
                else:
                    st.error("Preencha todos os campos.")

        # Bulk classification
        st.divider()
        with st.expander("📦 Sub-classificar múltiplos ativos de uma vez"):
            bulk_sub_label = st.text_input(
                "Sub-Categoria para Aplicar",
                placeholder="Ex: Conservadora",
                key="bulk_sub_label"
            )

            selected_assets = st.multiselect(
                "Selecione os Ativos",
                unmapped_assets,
                key="bulk_sub_assets"
            )

            if st.button("💾 Sub-classificar Selecionados", type="secondary"):
                if bulk_sub_label and selected_assets:
                    for asset in selected_assets:
                        db.add_or_update_sub_label_mapping(asset, "Previdência", bulk_sub_label)
                    st.success(f"✓ {len(selected_assets)} ativos sub-classificados!")
                    st.rerun()
                else:
                    st.error("Selecione ativos e defina uma sub-categoria.")
    else:
        st.success("✓ Todos os ativos de previdência estão sub-classificados!")

    # Show existing mappings
    if existing_mappings:
        st.divider()
        st.subheader("Sub-Classificações Existentes")

        # Group by sub-label
        by_sub_label = {}
        for mapping in existing_mappings:
            if mapping.sub_label not in by_sub_label:
                by_sub_label[mapping.sub_label] = []
            by_sub_label[mapping.sub_label].append(mapping)

        for sub_label, maps in sorted(by_sub_label.items()):
            with st.expander(f"**{sub_label}** ({len(maps)} ativos)"):
                for mapping in maps:
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        st.write(mapping.asset_name)

                    with col2:
                        if st.button("🗑️", key=f"del_sub_{mapping.id}", help="Remover sub-classificação"):
                            db.delete_sub_label_mapping(mapping.asset_name, "Previdência")
                            st.rerun()


def _render_target_management(db: Database):
    """Render sub-label target management"""
    st.subheader("Metas de Sub-Alocação")

    st.info(
        "⚠️ **Importante:** Defina as porcentagens ideais dentro da sua Previdência. "
        "A soma deve ser 100% (referente ao total de Previdência, não ao portfólio total)."
    )

    # Get all sub-labels from mappings
    mappings = db.get_all_sub_label_mappings("Previdência")
    all_sub_labels = sorted(set(m.sub_label for m in mappings))

    if not all_sub_labels:
        st.warning("⚠️ Sub-classifique seus ativos primeiro antes de definir metas.")
        return

    # Get existing targets
    existing_targets = db.get_all_sub_label_targets("Previdência")
    targets_dict = {t.sub_label: t.target_percentage for t in existing_targets}

    # Form to add/edit targets
    st.subheader("Definir Metas")

    with st.form("sub_target_form"):
        st.write("Defina a porcentagem alvo para cada sub-categoria:")

        targets_input = {}
        total_percentage = 0

        # Create input for each sub-label
        for sub_label in all_sub_labels:
            current_target = targets_dict.get(sub_label, 0.0)
            targets_input[sub_label] = st.number_input(
                f"{sub_label} (%)",
                min_value=0.0,
                max_value=100.0,
                value=current_target,
                step=1.0,
                key=f"sub_target_{sub_label}"
            )
            total_percentage += targets_input[sub_label]

        # Show total
        if total_percentage != 100:
            st.warning(f"⚠️ Total: {total_percentage:.1f}% (deve somar 100%)")
        else:
            st.success(f"✓ Total: {total_percentage:.1f}%")

        submitted = st.form_submit_button("💾 Salvar Metas", type="primary")

        if submitted:
            if abs(total_percentage - 100.0) > 0.1:
                st.error("A soma das porcentagens deve ser 100%!")
            else:
                for sub_label, target_pct in targets_input.items():
                    if target_pct > 0:  # Only save non-zero targets
                        db.add_or_update_sub_label_target("Previdência", sub_label, target_pct)

                st.success("✓ Metas salvas com sucesso!")
                st.rerun()

    # Display current targets
    if existing_targets:
        st.divider()
        st.subheader("Metas Atuais")

        for target in sorted(existing_targets, key=lambda x: x.target_percentage, reverse=True):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.write(target.sub_label)

            with col2:
                st.write(f"{target.target_percentage:.1f}%")

            with col3:
                if st.button("🗑️", key=f"del_sub_target_{target.id}", help="Deletar meta"):
                    db.delete_sub_label_target("Previdência", target.sub_label)
                    st.rerun()


def _render_rebalancing(positions, db: Database, total_value: float):
    """Render rebalancing analysis for Previdencia"""
    st.subheader("Rebalanceamento da Previdência")

    # Check if we have targets
    targets = db.get_all_sub_label_targets("Previdência")

    if not targets:
        st.warning("⚠️ Defina suas metas de sub-alocação primeiro na aba 'Definir Metas'.")
        return

    # Calculate current allocation by sub-label
    calc = PortfolioCalculator()

    # Use sub_label for grouping
    current_allocation = {}
    for p in positions:
        key = p.sub_label if p.sub_label else "Não Classificado"
        if key not in current_allocation:
            current_allocation[key] = 0.0
        current_allocation[key] += p.value

    # Get target allocations
    target_allocations = {t.sub_label: t.target_percentage for t in targets}

    # Input for additional investment
    st.write("**Novo Investimento em Previdência**")
    additional_investment = st.number_input(
        "Valor adicional a investir na Previdência (R$)",
        min_value=0.0,
        value=0.0,
        step=500.0,
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
    st.write("**Sub-Alocação Atual vs Meta**")

    comparison_data = []
    for analysis in plan.analyses:
        status_emoji = {
            'balanced': '✅',
            'overweight': '⚠️',
            'underweight': '🔴'
        }

        comparison_data.append({
            'Status': status_emoji.get(analysis.status, ''),
            'Sub-Categoria': analysis.label,
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
        st.metric("Sub-Categorias Balanceadas", f"{balanced_count}/{len(plan.analyses)}")

    with col2:
        if additional_investment > 0:
            st.metric("Novo Total Previdência", f"R$ {plan.total_portfolio_value:,.2f}")
        else:
            st.metric("Total Previdência", f"R$ {total_value:,.2f}")

    with col3:
        max_deviation = max((abs(a.difference_percentage) for a in plan.analyses), default=0)
        st.metric("Maior Desvio", f"{max_deviation:.1f}%")
