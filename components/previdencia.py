"""
Previdência portfolio component — completely separate from the Investimentos portfolio.
Uses the same 4 fixed categories (Estabilidade, Diversificação, Valorização, Antifragilidade)
with independent targets and rebalancing.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from database.db import Database, FIXED_CATEGORIES, PORTFOLIO_PREVIDENCIA
from database.models import AnnualIncomeEntry, PGBLYearSettings
from utils.calculations import PortfolioCalculator
from utils.ui_helpers import currency_input
from utils import pgbl_tax_calculator as pgbl_calc


def render_previdencia_component(db: Database):
    """Render Previdência specialized dashboard"""
    st.header("💼 Previdência Privada")

    positions = db.get_latest_positions(portfolio=PORTFOLIO_PREVIDENCIA)

    if not positions:
        st.info("📭 Nenhuma posição de Previdência encontrada.")
        st.write(
            "Ao importar ou adicionar posições, selecione **Previdência** como carteira. "
            "Se você já tinha ativos classificados como 'Previdência', eles precisam ser reclassificados nas categorias abaixo."
        )
        return

    total_value = sum(p.value for p in positions)
    position_date = positions[0].date

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data da Posição", position_date.strftime('%d/%m/%Y'))
    with col2:
        st.metric("Valor Total Previdência", f"R$ {total_value:,.2f}")
    with col3:
        st.metric("Total de Posições", len(positions))

    # Warn about uncategorized positions
    uncategorized = [p for p in positions if not p.custom_label]
    if uncategorized:
        st.warning(
            f"⚠️ **{len(uncategorized)} posição(ões) sem categoria** — "
            "classifique-as na aba 'Classificação' para incluí-las na análise."
        )

    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Visão Geral",
        "Classificação",
        "Definir Metas",
        "Metas por Ativo",
        "Rebalanceamento",
        "📊 Planejamento PGBL"
    ])

    with tab1:
        _render_overview(positions, total_value)

    with tab2:
        _render_classification(positions, db)

    with tab3:
        _render_target_management(db)

    with tab4:
        _render_asset_targets(db)

    with tab5:
        classified = [p for p in positions if p.custom_label]
        _render_rebalancing(classified, db, total_value)

    with tab6:
        _render_pgbl_planning(db, positions)


def _render_overview(positions, total_value: float):
    """Overview of Previdência distribution by category."""
    st.subheader("Distribuição por Categoria")

    classified = [p for p in positions if p.custom_label]
    if not classified:
        st.warning("⚠️ Classifique seus ativos de previdência na aba 'Classificação'.")
        return

    by_cat = {}
    for p in classified:
        by_cat.setdefault(p.custom_label, 0.0)
        by_cat[p.custom_label] += p.value

    cat_total = sum(by_cat.values())

    fig = go.Figure(data=[go.Pie(
        labels=list(by_cat.keys()),
        values=list(by_cat.values()),
        hole=0.40,
        hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>',
        textinfo='label+percent',
        textposition='outside'
    )])
    fig.update_layout(
        annotations=[dict(
            text=f'<b>Total</b><br>R$ {cat_total:,.0f}',
            x=0.5, y=0.5, font_size=16, showarrow=False, align='center'
        )],
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05),
        height=500,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    alloc_data = []
    for cat, val in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
        pct = val / cat_total * 100 if cat_total > 0 else 0
        alloc_data.append({'Categoria': cat, 'Valor': f"R$ {val:,.2f}", '%': f"{pct:.1f}%"})
    st.dataframe(alloc_data, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Todas as Posições")

    details = []
    for p in sorted(positions, key=lambda x: x.value, reverse=True):
        row = {
            'Nome': p.name,
            'Categoria': p.custom_label or "Não Classificado",
            'Valor': f"R$ {p.value:,.2f}",
        }
        if p.invested_value:
            gain = p.value - p.invested_value
            gain_pct = gain / p.invested_value * 100 if p.invested_value > 0 else 0
            row['Investido'] = f"R$ {p.invested_value:,.2f}"
            row['Ganho'] = f"R$ {gain:+,.2f} ({gain_pct:+.1f}%)"
        details.append(row)
    st.dataframe(details, use_container_width=True, hide_index=True)


def _render_classification(positions, db: Database):
    """Classify Previdência assets into the 4 fixed categories."""
    st.subheader("Classificar Ativos de Previdência")
    st.info(
        "Cada ativo de previdência deve pertencer a uma das 4 categorias. "
        "A classificação aqui é independente da carteira de Investimentos."
    )

    uncategorized = [p for p in positions if not p.custom_label]
    all_assets = sorted(set(p.name for p in positions))

    if uncategorized:
        uncategorized_names = sorted(set(p.name for p in uncategorized))
        st.warning(f"⚠️ {len(uncategorized_names)} ativo(s) sem categoria")

        with st.form("prev_classify_form"):
            asset = st.selectbox("Ativo", uncategorized_names)
            category = st.selectbox("Categoria", FIXED_CATEGORIES)
            submitted = st.form_submit_button("💾 Classificar", type="primary")

            if submitted and asset and category:
                db.add_or_update_mapping(asset, category, portfolio=PORTFOLIO_PREVIDENCIA)
                st.success(f"✓ '{asset}' classificado como '{category}' (Previdência)")
                st.rerun()

        # Bulk
        with st.expander("📦 Classificar múltiplos ativos"):
            bulk_cat = st.selectbox("Categoria", FIXED_CATEGORIES, key="prev_bulk_cat")
            selected = st.multiselect("Ativos", uncategorized_names, key="prev_bulk_assets")
            if st.button("💾 Classificar Selecionados", type="secondary"):
                if bulk_cat and selected:
                    for a in selected:
                        db.add_or_update_mapping(a, bulk_cat, portfolio=PORTFOLIO_PREVIDENCIA)
                    st.success(f"✓ {len(selected)} ativos classificados!")
                    st.rerun()
    else:
        st.success("✓ Todos os ativos de previdência estão classificados!")

    # Show existing classifications
    classified_mappings = [m for m in db.get_all_mappings() if m.portfolio == PORTFOLIO_PREVIDENCIA and m.custom_label]
    if classified_mappings:
        st.divider()
        st.subheader("Classificações Existentes")

        by_cat = {}
        for m in classified_mappings:
            by_cat.setdefault(m.custom_label, []).append(m)

        for cat, maps in sorted(by_cat.items()):
            with st.expander(f"**{cat}** ({len(maps)} ativos)"):
                for mapping in maps:
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.write(mapping.asset_name)
                    with col2:
                        new_cat = st.selectbox(
                            "Categoria",
                            FIXED_CATEGORIES,
                            index=FIXED_CATEGORIES.index(mapping.custom_label) if mapping.custom_label in FIXED_CATEGORIES else 0,
                            key=f"prev_edit_{mapping.id}",
                            label_visibility="collapsed"
                        )
                        if new_cat != mapping.custom_label:
                            if st.button("Salvar", key=f"prev_save_{mapping.id}"):
                                db.add_or_update_mapping(mapping.asset_name, new_cat, portfolio=PORTFOLIO_PREVIDENCIA)
                                st.rerun()
                    with col3:
                        if st.button("🗑️", key=f"prev_del_{mapping.id}", help="Remover classificação"):
                            db.delete_mapping(mapping.asset_name)
                            st.rerun()


def _render_target_management(db: Database):
    """Set allocation targets for the Previdência portfolio."""
    st.subheader("Definir Metas — Previdência")
    st.info(
        "Defina a porcentagem alvo para cada categoria **dentro da Previdência**. "
        "Deve somar 100%. Independente das metas de Investimentos."
    )

    targets = db.get_targets_by_portfolio(PORTFOLIO_PREVIDENCIA)
    targets_dict = {t.custom_label: t.target_percentage for t in targets}

    with st.form("prev_target_form"):
        st.write("Porcentagem alvo por categoria:")

        inputs = {}
        total_pct = 0.0

        for cat in FIXED_CATEGORIES:
            current = targets_dict.get(cat, 0.0)
            inputs[cat] = st.number_input(
                f"{cat} (%)",
                min_value=0.0,
                max_value=100.0,
                value=current,
                step=1.0,
                key=f"prev_target_{cat}"
            )
            total_pct += inputs[cat]

        if abs(total_pct - 100.0) < 0.01:
            st.success(f"✓ Total: {total_pct:.1f}%")
        else:
            st.warning(f"⚠️ Total: {total_pct:.1f}% (deve somar 100%)")

        submitted = st.form_submit_button("💾 Salvar Metas", type="primary")

        if submitted:
            if abs(total_pct - 100.0) > 0.1:
                st.error("A soma deve ser 100%!")
            else:
                for cat, pct in inputs.items():
                    db.add_or_update_target(cat, PORTFOLIO_PREVIDENCIA, pct)
                st.success("✓ Metas salvas!")
                st.rerun()

    # Show current targets
    active_targets = [t for t in targets if t.target_percentage > 0]
    if active_targets:
        st.divider()
        st.subheader("Metas Atuais")
        for t in sorted(active_targets, key=lambda x: x.target_percentage, reverse=True):
            col1, col2 = st.columns([3, 2])
            with col1:
                st.write(t.custom_label)
            with col2:
                st.write(f"{t.target_percentage:.1f}%")


def _render_rebalancing(positions, db: Database, total_value: float):
    """Rebalancing analysis for the Previdência portfolio."""
    st.subheader("Rebalanceamento da Previdência")

    targets = db.get_targets_by_portfolio(PORTFOLIO_PREVIDENCIA)
    target_map = {t.custom_label: t.target_percentage for t in targets if t.target_percentage > 0}

    if not target_map:
        st.warning("⚠️ Defina metas na aba 'Definir Metas' primeiro.")
        return

    if not positions:
        st.warning("⚠️ Nenhuma posição classificada. Classifique seus ativos primeiro.")
        return

    calc = PortfolioCalculator()

    current_allocation = {}
    for p in positions:
        current_allocation.setdefault(p.custom_label, 0.0)
        current_allocation[p.custom_label] += p.value

    additional = currency_input(
        "Valor adicional a investir na Previdência (R$)",
        key="prev_additional_investment",
        initial_value=0.0
    )

    plan = calc.create_rebalancing_plan(current_allocation, target_map, additional)

    st.divider()
    st.write("**Alocação Atual vs Meta**")

    status_emoji = {'balanced': '✅', 'overweight': '⚠️', 'underweight': '🔴'}
    comparison_data = []
    for a in plan.analyses:
        # When there's new money, show the amount actually allocated to this category
        # (capped by the shared pool), not the raw isolated distance-to-target.
        if additional > 0 and a.status == 'underweight':
            display_amount = a.capped_investment_amount
        else:
            display_amount = a.rebalance_amount

        comparison_data.append({
            'Status': status_emoji.get(a.status, ''),
            'Categoria': a.label,
            'Atual': f"{a.current_percentage:.1f}%",
            'Meta': f"{a.target_percentage:.1f}%",
            'Diferença': f"{a.difference_percentage:+.1f}%",
            'Valor Atual': f"R$ {a.current_value:,.2f}",
            'Ajuste Necessário': f"R$ {display_amount:+,.2f}" if abs(display_amount) > 1 else "✓"
        })
    st.dataframe(comparison_data, use_container_width=True, hide_index=True)

    if plan.suggestions:
        st.divider()
        st.write("**Sugestões**")
        for s in plan.suggestions:
            if s.startswith('\n'):
                st.write(s.strip())
            elif s.startswith('  -'):
                st.write(s)
            else:
                st.info(s)

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        balanced = sum(1 for a in plan.analyses if a.status == 'balanced')
        st.metric("Categorias Balanceadas", f"{balanced}/{len(plan.analyses)}")
    with col2:
        st.metric("Total Previdência", f"R$ {total_value:,.2f}")
    with col3:
        max_dev = max((abs(a.difference_percentage) for a in plan.analyses), default=0)
        st.metric("Maior Desvio", f"{max_dev:.1f}%")


def _render_asset_targets(db: Database):
    """Set per-asset targets within each category for the Previdência portfolio."""
    st.subheader("Metas por Ativo — Previdência")
    st.info(
        "Defina a porcentagem máxima que cada ativo pode representar dentro de sua categoria. "
        "Útil para limitar posições concentradas."
    )

    category = st.selectbox("Categoria", FIXED_CATEGORIES, key="prev_act_category")

    positions = db.get_latest_positions(portfolio=PORTFOLIO_PREVIDENCIA)
    cat_positions = [p for p in positions if p.custom_label == category]

    if not cat_positions:
        st.info(f"Nenhuma posição classificada em '{category}' na Previdência.")
        return

    cat_total = sum(p.value for p in cat_positions)
    existing_targets = {t.asset_name: t.target_pct for t in db.get_asset_category_targets(category, PORTFOLIO_PREVIDENCIA)}

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
                key=f"prev_act_{category}_{p.name}",
                label_visibility="collapsed"
            )
        with col3:
            if target_pct > 0:
                diff = current_pct - target_pct
                badge = "✅" if abs(diff) < 2 else ("⚠️ Alto" if diff > 0 else "🔴 Baixo")
                st.write(badge)

    if st.button("💾 Salvar Metas por Ativo", type="primary", key="prev_save_act"):
        for asset_name, pct in updated.items():
            if pct > 0:
                db.add_or_update_asset_category_target(asset_name, category, PORTFOLIO_PREVIDENCIA, pct)
            else:
                db.delete_asset_category_target(asset_name, category, PORTFOLIO_PREVIDENCIA)
        st.success("✓ Metas por ativo salvas!")
        st.rerun()


def _render_pgbl_planning(db: Database, positions):
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

    current_year = datetime.now().year
    selected_year = st.selectbox(
        "📅 Selecione o Ano",
        options=list(range(current_year - 2, current_year + 2)),
        index=2,
        help="Escolha o ano para planejamento do PGBL"
    )

    year_settings = db.get_year_settings(selected_year)
    if not year_settings:
        year_settings = PGBLYearSettings(year=selected_year, contributes_to_inss=True)
        db.add_or_update_year_settings(year_settings)

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

    income_entries = db.get_income_entries_by_year(selected_year)

    taxable_income = pgbl_calc.calculate_taxable_income(income_entries)
    pgbl_limit = pgbl_calc.calculate_pgbl_limit(taxable_income)

    # Sum contributions to Previdência assets this year
    start_of_year = datetime(selected_year, 1, 1)
    end_of_year = datetime(selected_year, 12, 31, 23, 59, 59)
    all_contributions = db.get_contributions_between_dates(start_of_year, end_of_year)

    pgbl_contributions = [
        c for c in all_contributions
        if any(p.name == c.asset_name for p in positions)
    ]
    current_pgbl_contributions = sum(c.contribution_amount for c in pgbl_contributions)

    remaining_investment = pgbl_calc.calculate_remaining_investment(pgbl_limit, current_pgbl_contributions)
    completion_pct = pgbl_calc.calculate_completion_percentage(pgbl_limit, current_pgbl_contributions)
    status, status_emoji, status_color = pgbl_calc.get_status_info(completion_pct)

    st.divider()
    st.subheader("💰 Resumo do Ano")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Renda Bruta Tributável", f"R$ {taxable_income:,.2f}",
                  help="Soma de salários, férias, aluguéis, etc. (excl. 13º e PLR)")
    with col2:
        st.metric("Limite PGBL (12%)", f"R$ {pgbl_limit:,.2f}",
                  help="Máximo que pode deduzir investindo em PGBL")
    with col3:
        st.metric("Já Investido em PGBL", f"R$ {current_pgbl_contributions:,.2f}",
                  help="Total de contribuições em Previdência neste ano")
    with col4:
        st.metric("Ainda Pode Investir", f"R$ {max(0, remaining_investment):,.2f}",
                  delta=f"{completion_pct:.1f}% do limite usado",
                  delta_color="normal" if remaining_investment >= 0 else "inverse",
                  help="Quanto falta para atingir o limite de 12%")

    st.progress(min(completion_pct / 100, 1.0))

    if completion_pct >= 100:
        st.success(f"{status_emoji} **Parabéns!** Você já atingiu ou ultrapassou o limite de 12%. Suas contribuições estão otimizadas para o benefício fiscal.")
    elif completion_pct >= 90:
        st.warning(f"{status_emoji} **Quase lá!** Faltam apenas R$ {remaining_investment:,.2f} para atingir o limite de dedução.")
    elif completion_pct > 0:
        st.info(f"{status_emoji} Você ainda tem R$ {remaining_investment:,.2f} disponíveis para investir em PGBL e maximizar seu benefício fiscal.")
    else:
        st.info(f"{status_emoji} Comece a registrar sua renda abaixo para calcular quanto pode investir em PGBL.")

    if selected_year == current_year:
        days_left = pgbl_calc.calculate_days_until_deadline(current_year)
        if days_left > 0:
            st.warning(f"⏰ **Prazo**: Faltam **{days_left} dias** até 31/12/{current_year} para investir em PGBL e deduzir neste ano!")
        elif days_left == 0:
            st.error("🚨 **ÚLTIMO DIA** para investir em PGBL e deduzir no IR deste ano!")

    st.divider()
    st.subheader("📝 Registro de Renda Mensal")

    with st.expander("➕ Adicionar Nova Entrada de Renda", expanded=len(income_entries) == 0):
        col1, col2 = st.columns(2)

        with col1:
            month = st.selectbox(
                "Mês",
                options=list(range(1, 13)),
                format_func=lambda m: [
                    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
                ][m - 1],
                key="pgbl_month"
            )
            entry_type = st.selectbox(
                "Tipo de Renda",
                options=list(pgbl_calc.INCOME_TYPES.keys()),
                format_func=lambda x: pgbl_calc.get_income_type_display_name(x),
                key="pgbl_entry_type"
            )

        with col2:
            amount = currency_input("Valor (R$)", key="pgbl_amount")
            description = st.text_input("Descrição (opcional)", placeholder="Ex: Salário mensal", key="pgbl_description")

        is_taxable = pgbl_calc.is_taxable_income_type(entry_type)
        if not is_taxable:
            st.info(f"ℹ️ **{pgbl_calc.get_income_type_display_name(entry_type)}** não entra no cálculo do PGBL (tributação exclusiva na fonte)")

        if st.button("💾 Adicionar Entrada", type="primary", key="pgbl_add_btn"):
            if amount > 0:
                db.add_income_entry(AnnualIncomeEntry(
                    year=selected_year, month=month, entry_type=entry_type,
                    amount=amount, description=description, date_added=datetime.now()
                ))
                st.success(f"✓ Entrada adicionada: {pgbl_calc.get_income_type_display_name(entry_type)} - R$ {amount:,.2f}")
                st.rerun()
            else:
                st.error("O valor deve ser maior que zero!")

    if income_entries:
        st.subheader("📊 Entradas Registradas")

        monthly_totals = pgbl_calc.categorize_income_by_month(income_entries)
        by_type = pgbl_calc.categorize_income_by_type(income_entries)

        entry_data = [{
            'ID': e.id,
            'Mês': ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"][e.month - 1],
            'Tipo': pgbl_calc.get_income_type_display_name(e.entry_type),
            'Valor': f"R$ {e.amount:,.2f}",
            'Tributável': "✅" if e.is_taxable else "❌",
            'Descrição': e.description or "-"
        } for e in income_entries]

        st.dataframe(
            pd.DataFrame(entry_data)[['Mês', 'Tipo', 'Valor', 'Tributável', 'Descrição']],
            use_container_width=True, hide_index=True
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            entry_to_delete = st.selectbox(
                "Deletar entrada",
                options=[e.id for e in income_entries],
                format_func=lambda eid: next(
                    f"{e.month:02d} - {pgbl_calc.get_income_type_display_name(e.entry_type)} - R$ {e.amount:,.2f}"
                    for e in income_entries if e.id == eid
                )
            )
        with col2:
            if st.button("🗑️ Deletar", type="secondary"):
                db.delete_income_entry(entry_to_delete)
                st.rerun()

        st.divider()
        st.subheader("📅 Resumo Mensal")

        month_data = []
        for m in range(1, 13):
            month_name = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                          "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"][m - 1]
            month_entries = [e for e in income_entries if e.month == m]
            month_taxable = sum(e.amount for e in month_entries if e.is_taxable)
            month_data.append({
                'Mês': month_name,
                'Total': f"R$ {monthly_totals.get(m, 0.0):,.2f}",
                'Tributável': f"R$ {month_taxable:,.2f}",
                'Entradas': len(month_entries)
            })
        st.dataframe(month_data, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📋 Resumo por Tipo de Renda")

        type_data = [{
            'Tipo': pgbl_calc.get_income_type_display_name(et),
            'Total': f"R$ {tot:,.2f}",
            'Tributável': "✅" if pgbl_calc.is_taxable_income_type(et) else "❌ (excluído)",
            'Entradas': sum(1 for e in income_entries if e.entry_type == et)
        } for et, tot in sorted(by_type.items(), key=lambda x: x[1], reverse=True)]
        st.dataframe(type_data, use_container_width=True, hide_index=True)

    else:
        st.info("📭 Nenhuma entrada de renda registrada ainda.")

    if income_entries:
        st.divider()
        st.subheader("🔮 Projeção Anual")

        months_with_data = len(set(e.month for e in income_entries))
        projected_income = pgbl_calc.project_annual_income(taxable_income, months_with_data)
        projected_limit = pgbl_calc.calculate_pgbl_limit(projected_income)
        projected_remaining = projected_limit - current_pgbl_contributions

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Meses com Dados", f"{months_with_data}/12")
        with col2:
            st.metric("Renda Projetada (Anual)", f"R$ {projected_income:,.2f}",
                      help="Baseado na média mensal dos meses informados")
        with col3:
            st.metric("Limite PGBL Projetado", f"R$ {projected_limit:,.2f}",
                      delta=f"R$ {max(0, projected_remaining):,.2f} faltando",
                      help="12% da renda projetada")

        if months_with_data < 12:
            st.info(f"ℹ️ Projeção baseada em {months_with_data} meses de dados.")
