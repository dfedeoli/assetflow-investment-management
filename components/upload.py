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

    tab1, tab2, tab3 = st.tabs(["Entrada Manual", "Upload XLSX", "Atualizar Posições"])

    with tab1:
        _render_manual_entry(db)

    with tab2:
        _render_xlsx_upload(db)

    with tab3:
        _render_update_positions(db)


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

            st.dataframe(preview_data, width="stretch")

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


def _render_update_positions(db: Database):
    """Render interface to update positions from a previous date"""
    st.subheader("Atualizar Posições Existentes")
    st.write("Carregue posições de uma data anterior e atualize os valores, ou edite posições na mesma data para corrigir valores incorretos.")

    # Get all available dates
    available_dates = db.get_all_dates()

    if not available_dates:
        st.info("Nenhuma posição encontrada no banco de dados. Adicione posições primeiro.")
        return

    # Initialize session state for edited positions
    if 'editing_positions' not in st.session_state:
        st.session_state.editing_positions = None
        st.session_state.base_date = None
        st.session_state.new_date = None
        st.session_state.positions_to_remove = set()
        st.session_state.new_positions = []
        st.session_state.original_values = {}
        st.session_state.edit_same_date = False

    col1, col2 = st.columns(2)

    with col1:
        base_date = st.selectbox(
            "Selecionar Data Base",
            options=available_dates,
            format_func=lambda d: d.strftime('%d/%m/%Y'),
            help="Escolha a data das posições que deseja editar/atualizar"
        )

    with col2:
        # Checkbox to toggle edit mode
        edit_same_date = st.checkbox(
            "✏️ Editar na mesma data",
            value=False,
            help="Marque para editar valores na mesma data. Desmarque para criar posições em uma nova data."
        )

        # Date input - disabled if editing same date
        if edit_same_date:
            st.date_input(
                "Data de Destino",
                value=base_date,
                disabled=True,
                help="Editando na mesma data da base selecionada"
            )
            new_date = base_date
        else:
            new_date = st.date_input(
                "Data de Destino",
                value=datetime.now(),
                help="Data para salvar as posições atualizadas"
            )

    if st.button("🔄 Carregar Posições", type="primary"):
        positions = db.get_positions_by_date(base_date)
        if positions:
            st.session_state.editing_positions = positions
            st.session_state.base_date = base_date
            st.session_state.new_date = datetime.combine(new_date, datetime.min.time()) if isinstance(new_date, datetime) else datetime.combine(new_date, datetime.min.time())
            st.session_state.edit_same_date = edit_same_date
            st.session_state.positions_to_remove = set()
            st.session_state.new_positions = []
            # Store original values when loading positions
            st.session_state.original_values = {idx: pos.value for idx, pos in enumerate(positions)}
            st.rerun()

    # Show editing interface if positions are loaded
    if st.session_state.editing_positions:
        st.divider()

        # Show summary
        total_value = sum(p.value for p in st.session_state.editing_positions
                         if st.session_state.editing_positions.index(p) not in st.session_state.positions_to_remove)
        kept_count = len(st.session_state.editing_positions) - len(st.session_state.positions_to_remove)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Data Base", st.session_state.base_date.strftime('%d/%m/%Y'))
        with col2:
            st.metric("Nova Data", st.session_state.new_date.strftime('%d/%m/%Y'))
        with col3:
            st.metric("Posições Ativas", f"{kept_count} de {len(st.session_state.editing_positions)}")

        st.subheader("Editar Posições")
        st.write("Atualize os valores, marque para remover ou mantenha como está.")

        # Create editable table
        edited_positions = []
        for idx, pos in enumerate(st.session_state.editing_positions):
            if idx in st.session_state.positions_to_remove:
                continue

            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                with col1:
                    st.write(f"**{pos.name}**")
                    if pos.custom_label:
                        st.caption(f"📊 {pos.custom_label}")

                with col2:
                    # Get original value from session state
                    original_value = st.session_state.original_values.get(idx, pos.value)
                    st.metric("Original", f"R$ {original_value:,.2f}", label_visibility="collapsed")

                with col3:
                    new_value = st.number_input(
                        "Valor (R$)",
                        min_value=0.0,
                        value=float(pos.value),
                        step=100.0,
                        key=f"pos_value_{idx}",
                        label_visibility="collapsed"
                    )
                    pos.value = new_value

                with col4:
                    if st.button("🗑️", key=f"remove_{idx}", help="Remover esta posição"):
                        st.session_state.positions_to_remove.add(idx)
                        st.rerun()

                st.divider()

        # Section to add new positions
        st.subheader("➕ Adicionar Novas Posições")

        with st.form("add_new_position"):
            col1, col2 = st.columns(2)

            with col1:
                new_name = st.text_input("Nome do Ativo")
                new_value = st.number_input("Valor (R$)", min_value=0.0, step=100.0)
                new_main_cat = st.selectbox(
                    "Categoria Principal",
                    ["Renda Fixa", "Fundos de Investimentos", "Fundos Imobiliários",
                     "Previdência Privada", "COE", "Outro"]
                )

            with col2:
                new_sub_cat = st.text_input("Subcategoria")
                new_invested = st.number_input("Valor Investido (R$) - Opcional", min_value=0.0, step=100.0)

            if st.form_submit_button("➕ Adicionar à Lista"):
                if new_name and new_value > 0:
                    new_pos = Position(
                        name=new_name,
                        value=new_value,
                        main_category=new_main_cat,
                        sub_category=new_sub_cat,
                        date=st.session_state.new_date,
                        invested_value=new_invested if new_invested > 0 else None
                    )
                    st.session_state.new_positions.append(new_pos)
                    st.rerun()

        # Show new positions to be added
        if st.session_state.new_positions:
            st.subheader("Novas Posições a Adicionar")
            for idx, pos in enumerate(st.session_state.new_positions):
                col1, col2, col3 = st.columns([4, 2, 1])
                with col1:
                    st.write(f"**{pos.name}**")
                    st.caption(f"{pos.main_category} - {pos.sub_category}")
                with col2:
                    st.write(f"R$ {pos.value:,.2f}")
                with col3:
                    if st.button("🗑️", key=f"remove_new_{idx}"):
                        st.session_state.new_positions.pop(idx)
                        st.rerun()

        # Calculate final summary
        st.divider()
        final_positions = [p for idx, p in enumerate(st.session_state.editing_positions)
                          if idx not in st.session_state.positions_to_remove]
        final_positions.extend(st.session_state.new_positions)
        final_value = sum(p.value for p in final_positions)

        st.subheader("Resumo Final")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Posições", len(final_positions))
        with col2:
            st.metric("Valor Total", f"R$ {final_value:,.2f}")
        with col3:
            original_value = sum(p.value for p in st.session_state.editing_positions)
            change = ((final_value - original_value) / original_value * 100) if original_value > 0 else 0
            st.metric("Variação", f"{change:+.2f}%")

        # Check for duplicate date or handle same-date editing
        if st.session_state.edit_same_date:
            # Editing same date - always delete and replace
            st.info(
                f"ℹ️ As alterações serão salvas na mesma data ({st.session_state.new_date.strftime('%d/%m/%Y')}). "
                f"As {len(st.session_state.editing_positions)} posições originais serão substituídas."
            )
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("💾 Salvar Alterações", type="primary"):
                    # Delete existing positions for this date first
                    db.delete_positions_by_date(st.session_state.new_date)
                    _save_updated_positions(db, final_positions, st.session_state.new_date)
                    _clear_editing_state()
                    st.rerun()
            with col2:
                if st.button("❌ Cancelar", type="secondary"):
                    _clear_editing_state()
                    st.rerun()
        else:
            # Creating new date - check for duplicates
            existing_on_new_date = db.get_positions_by_date(st.session_state.new_date)
            if existing_on_new_date:
                st.warning(
                    f"⚠️ Já existem {len(existing_on_new_date)} posições para "
                    f"{st.session_state.new_date.strftime('%d/%m/%Y')}. "
                    f"Salvar irá adicionar posições duplicadas ou você pode deletar as existentes primeiro."
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Deletar Existentes e Salvar", type="secondary"):
                        db.delete_positions_by_date(st.session_state.new_date)
                        _save_updated_positions(db, final_positions, st.session_state.new_date)
                        _clear_editing_state()
                        st.rerun()
                with col2:
                    if st.button("💾 Salvar Mesmo Assim", type="secondary"):
                        _save_updated_positions(db, final_positions, st.session_state.new_date)
                        _clear_editing_state()
                        st.rerun()
            else:
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("💾 Salvar Posições Atualizadas", type="primary"):
                        _save_updated_positions(db, final_positions, st.session_state.new_date)
                        _clear_editing_state()
                        st.rerun()
                with col2:
                    if st.button("❌ Cancelar", type="secondary"):
                        _clear_editing_state()
                        st.rerun()


def _save_updated_positions(db: Database, positions: list, new_date: datetime):
    """Save updated positions to database"""
    with st.spinner("Salvando posições..."):
        count = 0
        for pos in positions:
            # Update the date to the new date
            pos.date = new_date
            db.add_position(pos)
            count += 1

        st.success(f"✓ {count} posições salvas com sucesso para {new_date.strftime('%d/%m/%Y')}!")


def _clear_editing_state():
    """Clear editing session state"""
    st.session_state.editing_positions = None
    st.session_state.base_date = None
    st.session_state.new_date = None
    st.session_state.positions_to_remove = set()
    st.session_state.new_positions = []
    st.session_state.original_values = {}
