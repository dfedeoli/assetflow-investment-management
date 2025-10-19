"""
Contribution History Component
View and analyze contribution history over time
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.db import Database


def render_contribution_history(db: Database):
    """Render the contribution history interface"""
    st.header("📊 Histórico de Contribuições")

    # Get all contributions
    all_contributions = db.get_all_contributions()

    if not all_contributions:
        st.info("Nenhuma contribuição registrada ainda. Use a aba 'Registrar Contribuição' para começar.")
        return

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Todas as Contribuições", "📈 Por Ativo", "📅 Por Período"])

    with tab1:
        _render_all_contributions(db, all_contributions)

    with tab2:
        _render_by_asset(db, all_contributions)

    with tab3:
        _render_by_period(db, all_contributions)


def _render_all_contributions(db: Database, contributions: list):
    """Render all contributions in a table"""
    st.subheader("Todas as Contribuições")

    if not contributions:
        st.info("Nenhuma contribuição encontrada.")
        return

    # Summary metrics
    total_contributed = sum(c.contribution_amount for c in contributions)
    unique_assets = len(set(c.asset_name for c in contributions))
    total_contributions = len(contributions)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Contribuído", f"R$ {total_contributed:,.2f}")
    with col2:
        st.metric("Ativos com Contribuições", unique_assets)
    with col3:
        st.metric("Número de Contribuições", total_contributions)

    st.divider()

    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        # Get unique asset names
        asset_names = sorted(list(set(c.asset_name for c in contributions)))
        selected_assets = st.multiselect(
            "Filtrar por Ativo",
            options=asset_names,
            default=None,
            help="Selecione um ou mais ativos para filtrar"
        )

    with col2:
        # Date range filter
        min_date = min(c.contribution_date for c in contributions).date()
        max_date = max(c.contribution_date for c in contributions).date()

        date_range = st.date_input(
            "Filtrar por Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Selecione o período para filtrar contribuições"
        )

    # Apply filters
    filtered_contributions = contributions

    if selected_assets:
        filtered_contributions = [c for c in filtered_contributions if c.asset_name in selected_assets]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_contributions = [
            c for c in filtered_contributions
            if start_date <= c.contribution_date.date() <= end_date
        ]

    # Show filtered results
    if filtered_contributions:
        st.write(f"Mostrando {len(filtered_contributions)} de {len(contributions)} contribuições")

        # Create DataFrame for display
        data = []
        for c in filtered_contributions:
            data.append({
                'Data': c.contribution_date.strftime('%d/%m/%Y'),
                'Ativo': c.asset_name,
                'Contribuição': f"R$ {c.contribution_amount:,.2f}",
                'Valor Anterior': f"R$ {c.previous_value:,.2f}",
                'Novo Total': f"R$ {c.new_total_value:,.2f}",
                'Observações': c.notes if c.notes else '-'
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Show filtered totals
        filtered_total = sum(c.contribution_amount for c in filtered_contributions)
        st.metric("Total das Contribuições Filtradas", f"R$ {filtered_total:,.2f}")
    else:
        st.info("Nenhuma contribuição encontrada com os filtros aplicados.")


def _render_by_asset(db: Database, contributions: list):
    """Render contributions grouped by asset"""
    st.subheader("Contribuições por Ativo")

    if not contributions:
        st.info("Nenhuma contribuição encontrada.")
        return

    # Group by asset
    assets_contrib = {}
    for c in contributions:
        if c.asset_name not in assets_contrib:
            assets_contrib[c.asset_name] = []
        assets_contrib[c.asset_name].append(c)

    # Sort by total contribution amount
    sorted_assets = sorted(
        assets_contrib.items(),
        key=lambda x: sum(c.contribution_amount for c in x[1]),
        reverse=True
    )

    # Display each asset's contributions
    for asset_name, asset_contributions in sorted_assets:
        with st.expander(f"🔹 {asset_name}", expanded=False):
            total_contributed = sum(c.contribution_amount for c in asset_contributions)
            num_contributions = len(asset_contributions)

            # Show metrics for this asset
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Contribuído", f"R$ {total_contributed:,.2f}")
            with col2:
                st.metric("Número de Contribuições", num_contributions)
            with col3:
                avg_contribution = total_contributed / num_contributions if num_contributions > 0 else 0
                st.metric("Média por Contribuição", f"R$ {avg_contribution:,.2f}")

            # Show contribution timeline
            st.subheader("Timeline de Contribuições")
            timeline_data = []
            for c in sorted(asset_contributions, key=lambda x: x.contribution_date):
                timeline_data.append({
                    'Data': c.contribution_date.strftime('%d/%m/%Y'),
                    'Contribuição': f"R$ {c.contribution_amount:,.2f}",
                    'Novo Total': f"R$ {c.new_total_value:,.2f}",
                    'Observações': c.notes if c.notes else '-'
                })

            df = pd.DataFrame(timeline_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Get latest position to show current value
            latest_positions = db.get_latest_positions()
            current_position = next((pos for pos in latest_positions if pos.name == asset_name), None)

            if current_position:
                current_value = current_position.value
                total_gain = current_value - total_contributed
                gain_pct = (total_gain / total_contributed * 100) if total_contributed > 0 else 0

                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Valor Atual", f"R$ {current_value:,.2f}")
                with col2:
                    st.metric("Ganho/Perda", f"R$ {total_gain:,.2f}", f"{gain_pct:+.2f}%")
                with col3:
                    if current_position.custom_label:
                        st.info(f"📊 **Categoria:** {current_position.custom_label}")


def _render_by_period(db: Database, contributions: list):
    """Render contributions grouped by period"""
    st.subheader("Contribuições por Período")

    if not contributions:
        st.info("Nenhuma contribuição encontrada.")
        return

    # Period selection
    period_type = st.radio(
        "Agrupar por:",
        options=["Mês", "Trimestre", "Ano"],
        horizontal=True
    )

    # Group contributions by period
    periods = {}

    for c in contributions:
        if period_type == "Mês":
            period_key = c.contribution_date.strftime("%Y-%m")
            period_label = c.contribution_date.strftime("%B/%Y")
        elif period_type == "Trimestre":
            quarter = (c.contribution_date.month - 1) // 3 + 1
            period_key = f"{c.contribution_date.year}-Q{quarter}"
            period_label = f"Q{quarter}/{c.contribution_date.year}"
        else:  # Ano
            period_key = str(c.contribution_date.year)
            period_label = str(c.contribution_date.year)

        if period_key not in periods:
            periods[period_key] = {
                'label': period_label,
                'contributions': [],
                'total': 0.0
            }

        periods[period_key]['contributions'].append(c)
        periods[period_key]['total'] += c.contribution_amount

    # Sort periods (most recent first)
    sorted_periods = sorted(periods.items(), key=lambda x: x[0], reverse=True)

    # Display summary chart
    st.subheader("Resumo por Período")

    # Create data for bar chart
    chart_data = []
    for period_key, period_data in sorted_periods:
        chart_data.append({
            'Período': period_data['label'],
            'Total Contribuído (R$)': period_data['total']
        })

    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        st.bar_chart(df_chart.set_index('Período'))

    st.divider()

    # Display detailed breakdown
    st.subheader("Detalhamento por Período")

    for period_key, period_data in sorted_periods:
        with st.expander(f"📅 {period_data['label']} - R$ {period_data['total']:,.2f}", expanded=False):
            period_contributions = period_data['contributions']

            # Count by asset
            asset_totals = {}
            for c in period_contributions:
                if c.asset_name not in asset_totals:
                    asset_totals[c.asset_name] = 0
                asset_totals[c.asset_name] += c.contribution_amount

            # Display asset breakdown
            st.write(f"**{len(period_contributions)} contribuições neste período:**")

            for asset, total in sorted(asset_totals.items(), key=lambda x: x[1], reverse=True):
                st.write(f"- **{asset}:** R$ {total:,.2f}")

            # Show detailed list
            st.divider()
            detail_data = []
            for c in sorted(period_contributions, key=lambda x: x.contribution_date):
                detail_data.append({
                    'Data': c.contribution_date.strftime('%d/%m/%Y'),
                    'Ativo': c.asset_name,
                    'Valor': f"R$ {c.contribution_amount:,.2f}",
                    'Observações': c.notes if c.notes else '-'
                })

            df_detail = pd.DataFrame(detail_data)
            st.dataframe(df_detail, use_container_width=True, hide_index=True)
