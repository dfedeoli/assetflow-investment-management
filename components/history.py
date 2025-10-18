"""
Historical evolution and comparison component
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.db import Database
from utils.calculations import PortfolioCalculator


def render_history_component(db: Database):
    """Render historical evolution view"""
    st.header("📈 Evolução Histórica")

    # Get all available dates
    dates = db.get_all_dates()

    if len(dates) < 1:
        st.info("📭 Nenhum histórico disponível. Importe mais posições para ver a evolução.")
        return

    if len(dates) == 1:
        st.warning("⚠️ Apenas uma data disponível. Importe mais posições para comparar a evolução.")
        _render_single_snapshot(db, dates[0])
        return

    # Multiple dates available
    st.write(f"**{len(dates)} snapshots disponíveis**")

    tab1, tab2, tab3 = st.tabs(["Timeline", "Comparar Períodos", "Evolução por Categoria"])

    with tab1:
        _render_timeline(db, dates)

    with tab2:
        _render_comparison(db, dates)

    with tab3:
        _render_category_evolution(db, dates)


def _render_single_snapshot(db: Database, date: datetime):
    """Render view for single snapshot"""
    st.subheader(f"Snapshot: {date.strftime('%d/%m/%Y')}")

    positions = db.get_positions_by_date(date)
    total_value = sum(p.value for p in positions)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Valor Total", f"R$ {total_value:,.2f}")
    with col2:
        st.metric("Total de Posições", len(positions))


def _render_timeline(db: Database, dates: list):
    """Render timeline of portfolio value"""
    st.subheader("Evolução do Patrimônio")

    # Build timeline data
    timeline_data = []

    for date in sorted(dates):
        positions = db.get_positions_by_date(date)
        total_value = sum(p.value for p in positions)
        count = len(positions)

        timeline_data.append({
            'Data': date,
            'Valor Total': total_value,
            'Número de Posições': count
        })

    df = pd.DataFrame(timeline_data)

    # Plot value over time
    st.line_chart(df.set_index('Data')['Valor Total'], width="stretch")

    # Calculate growth
    if len(timeline_data) >= 2:
        first_value = timeline_data[0]['Valor Total']
        last_value = timeline_data[-1]['Valor Total']
        growth = last_value - first_value
        growth_pct = (growth / first_value * 100) if first_value > 0 else 0

        days_diff = (timeline_data[-1]['Data'] - timeline_data[0]['Data']).days

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Valor Inicial", f"R$ {first_value:,.2f}")

        with col2:
            st.metric("Valor Atual", f"R$ {last_value:,.2f}")

        with col3:
            st.metric("Crescimento", f"R$ {growth:+,.2f}", delta=f"{growth_pct:+.1f}%")

        with col4:
            st.metric("Período", f"{days_diff} dias")

    # Display table
    st.divider()
    st.subheader("Histórico Detalhado")

    display_data = []
    for i, row in enumerate(timeline_data):
        item = {
            'Data': row['Data'].strftime('%d/%m/%Y'),
            'Valor': f"R$ {row['Valor Total']:,.2f}",
            'Posições': row['Número de Posições']
        }

        # Calculate change from previous
        if i > 0:
            prev_value = timeline_data[i-1]['Valor Total']
            change = row['Valor Total'] - prev_value
            change_pct = (change / prev_value * 100) if prev_value > 0 else 0
            item['Variação'] = f"R$ {change:+,.2f} ({change_pct:+.1f}%)"
        else:
            item['Variação'] = "-"

        display_data.append(item)

    st.dataframe(display_data, width="stretch", hide_index=True)


def _render_comparison(db: Database, dates: list):
    """Render comparison between two periods"""
    st.subheader("Comparar Dois Períodos")

    col1, col2 = st.columns(2)

    with col1:
        date1 = st.selectbox(
            "Período 1 (Inicial)",
            dates,
            format_func=lambda x: x.strftime('%d/%m/%Y'),
            index=0 if len(dates) > 1 else 0
        )

    with col2:
        date2 = st.selectbox(
            "Período 2 (Final)",
            dates,
            format_func=lambda x: x.strftime('%d/%m/%Y'),
            index=len(dates)-1 if len(dates) > 1 else 0
        )

    if date1 == date2:
        st.warning("Selecione duas datas diferentes para comparar.")
        return

    # Get positions for both dates
    positions1 = db.get_positions_by_date(date1)
    positions2 = db.get_positions_by_date(date2)

    total1 = sum(p.value for p in positions1)
    total2 = sum(p.value for p in positions2)
    change = total2 - total1
    change_pct = (change / total1 * 100) if total1 > 0 else 0

    # Display summary
    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            date1.strftime('%d/%m/%Y'),
            f"R$ {total1:,.2f}",
            f"{len(positions1)} posições"
        )

    with col2:
        st.metric(
            date2.strftime('%d/%m/%Y'),
            f"R$ {total2:,.2f}",
            f"{len(positions2)} posições"
        )

    with col3:
        st.metric(
            "Variação",
            f"R$ {change:+,.2f}",
            f"{change_pct:+.1f}%"
        )

    # Compare by category
    st.divider()
    st.subheader("Comparação por Categoria")

    calc = PortfolioCalculator()

    # Use custom labels if available
    alloc1 = calc.calculate_current_allocation(positions1, use_custom_labels=True)
    alloc2 = calc.calculate_current_allocation(positions2, use_custom_labels=True)

    growth_data = calc.calculate_historical_growth(alloc1, alloc2)

    comparison_data = []
    for label, data in sorted(growth_data.items(), key=lambda x: abs(x[1]['growth']), reverse=True):
        comparison_data.append({
            'Categoria': label,
            f'{date1.strftime("%d/%m")}': f"R$ {data['old_value']:,.2f}",
            f'{date2.strftime("%d/%m")}': f"R$ {data['new_value']:,.2f}",
            'Variação': f"R$ {data['growth']:+,.2f}",
            'Variação %': f"{data['growth_pct']:+.1f}%"
        })

    st.dataframe(comparison_data, width="stretch", hide_index=True)

    # Identify new and removed positions
    st.divider()
    st.subheader("Mudanças nas Posições")

    names1 = set(p.name for p in positions1)
    names2 = set(p.name for p in positions2)

    new_positions = names2 - names1
    removed_positions = names1 - names2

    col1, col2 = st.columns(2)

    with col1:
        if new_positions:
            st.write(f"**Novas Posições ({len(new_positions)})**")
            for name in sorted(new_positions):
                pos = next(p for p in positions2 if p.name == name)
                st.write(f"- {name}: R$ {pos.value:,.2f}")
        else:
            st.write("**Nenhuma posição nova**")

    with col2:
        if removed_positions:
            st.write(f"**Posições Removidas ({len(removed_positions)})**")
            for name in sorted(removed_positions):
                pos = next(p for p in positions1 if p.name == name)
                st.write(f"- {name}: R$ {pos.value:,.2f}")
        else:
            st.write("**Nenhuma posição removida**")


def _render_category_evolution(db: Database, dates: list):
    """Render evolution of categories over time"""
    st.subheader("Evolução por Categoria")

    # Allow user to select date range
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.selectbox(
            "Data Inicial",
            dates,
            format_func=lambda x: x.strftime('%d/%m/%Y'),
            index=0
        )

    with col2:
        end_date = st.selectbox(
            "Data Final",
            dates,
            format_func=lambda x: x.strftime('%d/%m/%Y'),
            index=len(dates)-1
        )

    # Get positions in range
    filtered_dates = [d for d in dates if start_date <= d <= end_date]

    if len(filtered_dates) < 2:
        st.warning("Selecione um intervalo com pelo menos 2 datas.")
        return

    # Build evolution data
    calc = PortfolioCalculator()
    all_labels = set()
    evolution_by_date = {}

    for date in sorted(filtered_dates):
        positions = db.get_positions_by_date(date)
        allocation = calc.calculate_current_allocation(positions, use_custom_labels=True)

        evolution_by_date[date] = allocation
        all_labels.update(allocation.keys())

    # Create DataFrame for chart
    chart_data = []
    for date in sorted(filtered_dates):
        row = {'Data': date}
        for label in all_labels:
            row[label] = evolution_by_date[date].get(label, 0)
        chart_data.append(row)

    df = pd.DataFrame(chart_data)

    # Display line chart
    st.line_chart(df.set_index('Data'), width="stretch")

    # Display percentage evolution
    st.divider()
    st.subheader("Evolução da Alocação (%)")

    pct_data = []
    for date in sorted(filtered_dates):
        positions = db.get_positions_by_date(date)
        allocation = calc.calculate_current_allocation(positions, use_custom_labels=True)
        percentages = calc.calculate_allocation_percentages(allocation)

        row = {'Data': date.strftime('%d/%m/%Y')}
        for label in sorted(all_labels):
            row[label] = f"{percentages.get(label, 0):.1f}%"

        pct_data.append(row)

    st.dataframe(pct_data, width="stretch", hide_index=True)
