"""
File upload and data import component
"""

import streamlit as st
from datetime import datetime
from parsers.xlsx_parser import XLSXParser, InvestmentPosition
from database.db import Database
from database.models import Position


def render_upload_component(db: Database):
    """Render the file upload interface"""
    st.header("📁 Importar Posições")

    tab1, tab2 = st.tabs(["Entrada Manual", "Upload XLSX"])

    with tab1:
        _render_manual_entry(db)

    with tab2:
        _render_xlsx_upload(db)


def _render_xlsx_upload(db: Database):
    """Render XLSX file upload"""
    st.subheader("Upload de Arquivo XLSX")

    uploaded_file = st.file_uploader(
        "Selecione o arquivo XLSX da sua posição",
        type="xlsx",
        help="Faça upload do arquivo exportado do banco/corretora"
    )

    if uploaded_file is not None:
        try:
            # Save temporarily and parse
            temp_path = f"/tmp/{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("Analisando arquivo..."):
                parser = XLSXParser(temp_path)
                positions, metadata = parser.parse()

            if not positions:
                st.error("Nenhuma posição foi encontrada no arquivo. Verifique o formato.")
                return

            # Show preview
            st.success(f"✓ {len(positions)} posições encontradas!")

            # Display metadata
            if metadata:
                col1, col2, col3 = st.columns(3)
                with col1:
                    if 'position_date' in metadata:
                        st.metric("Data da Posição", metadata['position_date'].strftime('%d/%m/%Y'))
                with col2:
                    if 'account' in metadata:
                        st.metric("Conta", metadata['account'])
                with col3:
                    total_value = sum(p.value for p in positions)
                    st.metric("Valor Total", f"R$ {total_value:,.2f}")

            # Show summary by category
            st.subheader("Resumo por Categoria")
            summary = parser.get_summary()
            if 'categories' in summary:
                for cat, data in summary['categories'].items():
                    pct = (data['value'] / summary['total_value'] * 100) if summary['total_value'] > 0 else 0
                    st.write(f"**{cat}**: {data['count']} posições, R$ {data['value']:,.2f} ({pct:.1f}%)")

            # Show preview table
            st.subheader("Prévia das Posições")
            preview_data = []
            preview_number = 30
            for p in positions[:preview_number]:  # Show first 30
                preview_data.append({
                    'Nome': p.name,
                    'Valor': f"R$ {p.value:,.2f}",
                    'Categoria': p.sub_category,
                    'Tipo': p.main_category
                })

            st.dataframe(preview_data, use_container_width=True)

            if len(positions) > preview_number:
                st.info(f"Mostrando {preview_number} de {len(positions)} posições...")

            # Check if date already exists
            position_date = metadata.get('position_date', datetime.now())
            existing_positions = db.get_positions_by_date(position_date)

            if existing_positions:
                st.warning(
                    f"⚠️ Já existem {len(existing_positions)} posições para a data "
                    f"{position_date.strftime('%d/%m/%Y')}. "
                    f"Importar novamente irá adicionar posições duplicadas."
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Deletar Posições Existentes e Reimportar", type="secondary"):
                        db.delete_positions_by_date(position_date)
                        _import_positions(db, positions)
                        st.rerun()

                with col2:
                    if st.button("➕ Importar Mesmo Assim", type="secondary"):
                        _import_positions(db, positions)
                        st.rerun()
            else:
                if st.button("💾 Importar Posições", type="primary"):
                    _import_positions(db, positions)
                    st.rerun()

        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")
            st.exception(e)


def _import_positions(db: Database, positions: list):
    """Import positions into database"""
    with st.spinner("Importando posições..."):
        count = 0
        for inv_pos in positions:
            # Convert InvestmentPosition to Position model
            pos = Position(
                name=inv_pos.name,
                value=inv_pos.value,
                main_category=inv_pos.main_category,
                sub_category=inv_pos.sub_category,
                date=inv_pos.date,
                invested_value=inv_pos.invested_value,
                percentage=inv_pos.percentage,
                quantity=inv_pos.quantity
            )
            db.add_position(pos)
            count += 1

        st.success(f"✓ {count} posições importadas com sucesso!")


def _render_manual_entry(db: Database):
    """Render manual entry form"""
    st.subheader("Entrada Manual de Posição")

    with st.form("manual_entry"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Nome do Ativo", placeholder="Ex: Tesouro IPCA+ 2035")
            value = st.number_input("Valor Atual (R$)", min_value=0.0, step=100.0)
            main_category = st.selectbox(
                "Categoria Principal",
                ["Renda Fixa", "Fundos de Investimentos", "Fundos Imobiliários", "Previdência Privada", "COE", "Outro"]
            )

        with col2:
            sub_category = st.text_input("Subcategoria", placeholder="Ex: Pós-Fixado, Multimercados")
            date = st.date_input("Data da Posição", value=datetime.now())
            invested_value = st.number_input(
                "Valor Investido (R$) - Opcional",
                min_value=0.0,
                step=100.0,
                value=0.0
            )

        submitted = st.form_submit_button("➕ Adicionar Posição", type="primary")

        if submitted:
            if not name or value <= 0:
                st.error("Por favor, preencha o nome e valor do ativo.")
            else:
                position = Position(
                    name=name,
                    value=value,
                    main_category=main_category,
                    sub_category=sub_category,
                    date=datetime.combine(date, datetime.min.time()),
                    invested_value=invested_value if invested_value > 0 else None
                )

                db.add_position(position)
                st.success(f"✓ Posição '{name}' adicionada com sucesso!")
                st.rerun()
