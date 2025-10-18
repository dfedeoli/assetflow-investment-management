"""
Previdencia specialized component with sub-classification
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from database.db import Database
from database.models import AnnualIncomeEntry, PGBLYearSettings
from utils.calculations import PortfolioCalculator
from utils import pgbl_tax_calculator as pgbl_calc


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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Visão Geral",
        "Sub-Classificação",
        "Definir Metas",
        "Rebalanceamento",
        "📊 Planejamento PGBL"
    ])

    with tab1:
        _render_overview(positions, db)

    with tab2:
        _render_sub_classification(positions, db)

    with tab3:
        _render_target_management(db)

    with tab4:
        _render_rebalancing(positions, db, total_value)

    with tab5:
        _render_pgbl_planning(db)


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

        # Display as donut chart
        total_value = df['Valor'].sum()

        fig = go.Figure(data=[go.Pie(
            labels=df['Sub-Categoria'],
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


def _render_pgbl_planning(db: Database):
    """Render PGBL tax planning dashboard"""
    st.subheader("📊 Planejamento PGBL - Benefício Fiscal")

    st.markdown("""
    **Como funciona o benefício fiscal do PGBL:**
    - Você pode deduzir até **12% da sua renda bruta tributável anual** investindo em PGBL
    - Isso **reduz o Imposto de Renda** a pagar ou aumenta a restituição
    - **Prazo**: Investimentos até 31 de dezembro contam para a declaração do ano seguinte
    - **Requisito**: Você deve contribuir para o INSS ou regime próprio de previdência

    ℹ️ Use esta ferramenta para acompanhar sua renda ao longo do ano e calcular quanto investir em PGBL.
    """)

    st.divider()

    # Year selector
    current_year = datetime.now().year
    selected_year = st.selectbox(
        "📅 Selecione o Ano",
        options=list(range(current_year - 2, current_year + 2)),
        index=2,  # Current year
        help="Escolha o ano para planejamento do PGBL"
    )

    # Get or create year settings
    year_settings = db.get_year_settings(selected_year)
    if not year_settings:
        year_settings = PGBLYearSettings(
            year=selected_year,
            contributes_to_inss=True
        )
        db.add_or_update_year_settings(year_settings)

    # INSS contribution checkbox
    st.divider()
    contributes_to_inss = st.checkbox(
        "✅ Contribuo para o INSS ou regime próprio de previdência",
        value=year_settings.contributes_to_inss,
        help="Requisito obrigatório para deduzir PGBL no IR"
    )

    if contributes_to_inss != year_settings.contributes_to_inss:
        year_settings.contributes_to_inss = contributes_to_inss
        db.add_or_update_year_settings(year_settings)

    if not contributes_to_inss:
        st.warning("⚠️ **Atenção**: Sem contribuição ao INSS, você NÃO pode deduzir o PGBL no Imposto de Renda!")

    # Get income entries for the year
    income_entries = db.get_income_entries_by_year(selected_year)

    # Calculate metrics
    taxable_income = pgbl_calc.calculate_taxable_income(income_entries)
    pgbl_limit = pgbl_calc.calculate_pgbl_limit(taxable_income)

    # Get PGBL contributions (positions from Previdência in selected year)
    start_of_year = datetime(selected_year, 1, 1)
    end_of_year = datetime(selected_year, 12, 31, 23, 59, 59)
    pgbl_positions = db.get_positions_between_dates(start_of_year, end_of_year)
    pgbl_positions = [p for p in pgbl_positions if p.custom_label == "Previdência"]

    # Sum invested values (or current values if invested_value is not available)
    current_pgbl_contributions = sum(
        p.invested_value if p.invested_value else p.value for p in pgbl_positions
    )

    remaining_investment = pgbl_calc.calculate_remaining_investment(pgbl_limit, current_pgbl_contributions)
    completion_pct = pgbl_calc.calculate_completion_percentage(pgbl_limit, current_pgbl_contributions)
    status, status_emoji, status_color = pgbl_calc.get_status_info(completion_pct)

    # Display summary cards
    st.divider()
    st.subheader("💰 Resumo do Ano")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Renda Bruta Tributável",
            f"R$ {taxable_income:,.2f}",
            help="Soma de salários, férias, aluguéis, etc. (excl. 13º e PLR)"
        )

    with col2:
        st.metric(
            "Limite PGBL (12%)",
            f"R$ {pgbl_limit:,.2f}",
            help="Máximo que pode deduzir investindo em PGBL"
        )

    with col3:
        st.metric(
            "Já Investido em PGBL",
            f"R$ {current_pgbl_contributions:,.2f}",
            help="Total de contribuições em Previdência neste ano"
        )

    with col4:
        delta_color = "normal" if remaining_investment >= 0 else "inverse"
        st.metric(
            "Ainda Pode Investir",
            f"R$ {max(0, remaining_investment):,.2f}",
            delta=f"{completion_pct:.1f}% do limite usado",
            delta_color=delta_color,
            help="Quanto falta para atingir o limite de 12%"
        )

    # Progress bar
    st.progress(min(completion_pct / 100, 1.0))

    # Status message
    if completion_pct >= 100:
        st.success(f"{status_emoji} **Parabéns!** Você já atingiu ou ultrapassou o limite de 12%. Suas contribuições estão otimizadas para o benefício fiscal.")
    elif completion_pct >= 90:
        st.warning(f"{status_emoji} **Quase lá!** Faltam apenas R$ {remaining_investment:,.2f} para atingir o limite de dedução.")
    elif completion_pct > 0:
        st.info(f"{status_emoji} Você ainda tem R$ {remaining_investment:,.2f} disponíveis para investir em PGBL e maximizar seu benefício fiscal.")
    else:
        st.info(f"{status_emoji} Comece a registrar sua renda abaixo para calcular quanto pode investir em PGBL.")

    # Deadline reminder
    if selected_year == current_year:
        days_left = pgbl_calc.calculate_days_until_deadline(current_year)
        if days_left > 0:
            st.warning(f"⏰ **Prazo**: Faltam **{days_left} dias** até 31/12/{current_year} para investir em PGBL e deduzir neste ano!")
        elif days_left == 0:
            st.error("🚨 **ÚLTIMO DIA** para investir em PGBL e deduzir no IR deste ano!")

    # Income tracking section
    st.divider()
    st.subheader("📝 Registro de Renda Mensal")

    # Add new income entry
    with st.expander("➕ Adicionar Nova Entrada de Renda", expanded=len(income_entries) == 0):
        with st.form("add_income_entry"):
            col1, col2 = st.columns(2)

            with col1:
                month = st.selectbox(
                    "Mês",
                    options=list(range(1, 13)),
                    format_func=lambda m: [
                        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
                    ][m - 1]
                )

                entry_type = st.selectbox(
                    "Tipo de Renda",
                    options=list(pgbl_calc.INCOME_TYPES.keys()),
                    format_func=lambda x: pgbl_calc.get_income_type_display_name(x)
                )

            with col2:
                amount = st.number_input(
                    "Valor (R$)",
                    min_value=0.0,
                    step=100.0,
                    format="%.2f"
                )

                description = st.text_input(
                    "Descrição (opcional)",
                    placeholder="Ex: Salário mensal, Aluguel apt 101"
                )

            # Show if this type is taxable
            is_taxable = pgbl_calc.is_taxable_income_type(entry_type)
            if not is_taxable:
                st.info(f"ℹ️ **{pgbl_calc.get_income_type_display_name(entry_type)}** não entra no cálculo do PGBL (tributação exclusiva na fonte)")

            submitted = st.form_submit_button("💾 Adicionar Entrada", type="primary")

            if submitted:
                if amount > 0:
                    new_entry = AnnualIncomeEntry(
                        year=selected_year,
                        month=month,
                        entry_type=entry_type,
                        amount=amount,
                        description=description,
                        date_added=datetime.now()
                    )
                    db.add_income_entry(new_entry)
                    st.success(f"✓ Entrada adicionada: {pgbl_calc.get_income_type_display_name(entry_type)} - R$ {amount:,.2f}")
                    st.rerun()
                else:
                    st.error("O valor deve ser maior que zero!")

    # Display existing entries
    if income_entries:
        st.subheader("📊 Entradas Registradas")

        # Group by month for display
        monthly_totals = pgbl_calc.categorize_income_by_month(income_entries)
        by_type = pgbl_calc.categorize_income_by_type(income_entries)

        # Create display table
        entry_data = []
        for entry in income_entries:
            entry_data.append({
                'ID': entry.id,
                'Mês': ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                        "Jul", "Ago", "Set", "Out", "Nov", "Dez"][entry.month - 1],
                'Tipo': pgbl_calc.get_income_type_display_name(entry.entry_type),
                'Valor': f"R$ {entry.amount:,.2f}",
                'Tributável': "✅" if entry.is_taxable else "❌",
                'Descrição': entry.description or "-"
            })

        df_entries = pd.DataFrame(entry_data)

        # Show table
        st.dataframe(
            df_entries[['Mês', 'Tipo', 'Valor', 'Tributável', 'Descrição']],
            use_container_width=True,
            hide_index=True
        )

        # Delete entries
        st.write("**Deletar Entrada**")
        col1, col2 = st.columns([3, 1])
        with col1:
            entry_to_delete = st.selectbox(
                "Selecione a entrada para deletar",
                options=[e.id for e in income_entries],
                format_func=lambda id: next(
                    f"{e.month:02d} - {pgbl_calc.get_income_type_display_name(e.entry_type)} - R$ {e.amount:,.2f}"
                    for e in income_entries if e.id == id
                )
            )
        with col2:
            if st.button("🗑️ Deletar", type="secondary"):
                db.delete_income_entry(entry_to_delete)
                st.success("Entrada deletada!")
                st.rerun()

        # Monthly breakdown
        st.divider()
        st.subheader("📅 Resumo Mensal")

        month_data = []
        for month_num in range(1, 13):
            month_name = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                          "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][month_num - 1]
            month_total = monthly_totals.get(month_num, 0.0)
            month_entries = [e for e in income_entries if e.month == month_num]
            month_taxable = sum(e.amount for e in month_entries if e.is_taxable)

            month_data.append({
                'Mês': month_name,
                'Total': f"R$ {month_total:,.2f}",
                'Tributável': f"R$ {month_taxable:,.2f}",
                'Entradas': len(month_entries)
            })

        st.dataframe(month_data, use_container_width=True, hide_index=True)

        # Breakdown by type
        st.divider()
        st.subheader("📋 Resumo por Tipo de Renda")

        type_data = []
        for entry_type, total in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            type_name = pgbl_calc.get_income_type_display_name(entry_type)
            is_taxable = pgbl_calc.is_taxable_income_type(entry_type)
            count = sum(1 for e in income_entries if e.entry_type == entry_type)

            type_data.append({
                'Tipo': type_name,
                'Total': f"R$ {total:,.2f}",
                'Tributável': "✅" if is_taxable else "❌ (excluído)",
                'Entradas': count
            })

        st.dataframe(type_data, use_container_width=True, hide_index=True)

    else:
        st.info("📭 Nenhuma entrada de renda registrada ainda. Adicione suas rendas mensais acima para começar o planejamento.")

    # Projection section
    if income_entries:
        st.divider()
        st.subheader("🔮 Projeção Anual")

        months_with_data = len(set(e.month for e in income_entries))
        projected_income = pgbl_calc.project_annual_income(taxable_income, months_with_data)
        projected_limit = pgbl_calc.calculate_pgbl_limit(projected_income)
        projected_remaining = projected_limit - current_pgbl_contributions

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Meses com Dados",
                f"{months_with_data}/12"
            )

        with col2:
            st.metric(
                "Renda Projetada (Anual)",
                f"R$ {projected_income:,.2f}",
                help="Baseado na média mensal dos meses informados"
            )

        with col3:
            st.metric(
                "Limite PGBL Projetado",
                f"R$ {projected_limit:,.2f}",
                delta=f"R$ {max(0, projected_remaining):,.2f} faltando",
                help="12% da renda projetada"
            )

        if months_with_data < 12:
            st.info(f"ℹ️ Projeção baseada em {months_with_data} meses de dados. Continue registrando suas rendas para uma estimativa mais precisa!")
