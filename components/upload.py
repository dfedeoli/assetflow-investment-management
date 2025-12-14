"""
File upload and data import component
"""

import streamlit as st
from datetime import datetime
from parsers.xlsx_parser import XLSXParser, InvestmentPosition
from parsers.pdf_image_parser import PDFImageParser
from database.db import Database
from database.models import Position


def render_upload_component(db: Database):
    """Render the file upload interface"""
    st.header("📁 Gerenciar Posições")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Entrada Manual",
        "Atualizar Posições",
        "Registrar Contribuição",
        "Upload - Histórico Carteira XP",
        "Upload - PDF/Imagem (AI)"
    ])

    with tab1:
        _render_manual_entry(db)

    with tab2:
        _render_update_positions(db)

    with tab3:
        _render_record_contribution(db)

    with tab4:
         _render_xlsx_upload(db)

    with tab5:
        _render_pdf_image_upload(db)


def _render_xlsx_upload(db: Database):
    """Render XLSX file upload"""
    st.subheader("Upload de Histórico de Carteira - XP Investimentos")

    # Initialize session state for XLSX editing
    if 'xlsx_positions' not in st.session_state:
        st.session_state.xlsx_positions = None
        st.session_state.xlsx_metadata = None
        st.session_state.xlsx_positions_to_remove = set()
        st.session_state.xlsx_new_positions = []
        st.session_state.xlsx_original_values = {}

    # Stage 1: Upload and parse (only show if not currently editing)
    if st.session_state.xlsx_positions is None:
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

                # Button to proceed to editing
                st.divider()
                if st.button("✏️ Revisar e Editar Posições", type="primary"):
                    st.session_state.xlsx_positions = positions
                    st.session_state.xlsx_metadata = metadata
                    st.session_state.xlsx_positions_to_remove = set()
                    st.session_state.xlsx_new_positions = []
                    # Store original values
                    st.session_state.xlsx_original_values = {idx: p.value for idx, p in enumerate(positions)}
                    st.rerun()

            except Exception as e:
                st.error(f"Erro ao processar arquivo: {str(e)}")
                st.exception(e)

    # Stage 2: Edit positions
    else:
        _render_xlsx_editing(db)


def _render_xlsx_editing(db: Database):
    """Render editing interface for XLSX positions"""
    positions = st.session_state.xlsx_positions
    metadata = st.session_state.xlsx_metadata
    position_date = metadata.get('position_date', datetime.now())

    st.subheader("✏️ Revisar e Editar Posições")
    st.write("Revise os dados importados, edite valores, remova posições indesejadas ou adicione novas antes de salvar.")

    # Show summary
    total_value = sum(p.value for p in positions
                     if positions.index(p) not in st.session_state.xlsx_positions_to_remove)
    kept_count = len(positions) - len(st.session_state.xlsx_positions_to_remove)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data da Posição", position_date.strftime('%d/%m/%Y'))
    with col2:
        st.metric("Posições Ativas", f"{kept_count} de {len(positions)}")
    with col3:
        final_total = total_value + sum(p.value for p in st.session_state.xlsx_new_positions)
        st.metric("Valor Total", f"R$ {final_total:,.2f}")

    st.divider()

    # Editable positions table
    st.subheader("Posições do Arquivo")
    for idx, pos in enumerate(positions):
        if idx in st.session_state.xlsx_positions_to_remove:
            continue

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1, 1])

            with col1:
                st.write(f"**{pos.name}**")
                st.caption(f"{pos.main_category} - {pos.sub_category}")

            with col2:
                # Show original value
                original_value = st.session_state.xlsx_original_values.get(idx, pos.value)
                st.metric("Original", f"R$ {original_value:,.2f}", label_visibility="collapsed")

            with col3:
                # Editable value
                new_value = st.number_input(
                    "Novo Valor (R$)",
                    min_value=0.0,
                    value=float(pos.value),
                    step=100.0,
                    key=f"xlsx_pos_value_{idx}",
                    label_visibility="collapsed"
                )
                pos.value = new_value

            with col4:
                # Show change indicator
                if abs(new_value - original_value) > 0.01:
                    change_pct = ((new_value - original_value) / original_value * 100) if original_value > 0 else 0
                    st.metric("Δ", f"{change_pct:+.1f}%", label_visibility="collapsed")

            with col5:
                if st.button("🗑️", key=f"xlsx_remove_{idx}", help="Remover esta posição"):
                    st.session_state.xlsx_positions_to_remove.add(idx)
                    st.rerun()

            st.divider()

    # Section to add new positions
    st.subheader("➕ Adicionar Novas Posições")

    with st.form("xlsx_add_new_position"):
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
                # Create InvestmentPosition (to match the type from parser)
                new_pos = InvestmentPosition(
                    name=new_name,
                    value=new_value,
                    main_category=new_main_cat,
                    sub_category=new_sub_cat,
                    date=position_date,
                    invested_value=new_invested if new_invested > 0 else None
                )
                st.session_state.xlsx_new_positions.append(new_pos)
                st.rerun()

    # Show new positions to be added
    if st.session_state.xlsx_new_positions:
        st.subheader("Novas Posições a Adicionar")
        for idx, pos in enumerate(st.session_state.xlsx_new_positions):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.write(f"**{pos.name}**")
                st.caption(f"{pos.main_category} - {pos.sub_category}")
            with col2:
                st.write(f"R$ {pos.value:,.2f}")
            with col3:
                if st.button("🗑️", key=f"xlsx_remove_new_{idx}"):
                    st.session_state.xlsx_new_positions.pop(idx)
                    st.rerun()

    # Final summary and save
    st.divider()
    _render_xlsx_final_summary_and_save(db, positions, position_date)


def _render_xlsx_final_summary_and_save(db: Database, positions: list, position_date: datetime):
    """Render final summary and save options for XLSX import"""
    # Calculate final positions
    final_positions = [p for idx, p in enumerate(positions)
                      if idx not in st.session_state.xlsx_positions_to_remove]
    final_positions.extend(st.session_state.xlsx_new_positions)
    final_value = sum(p.value for p in final_positions)

    st.subheader("Resumo Final")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Posições", len(final_positions))
    with col2:
        st.metric("Valor Total", f"R$ {final_value:,.2f}")
    with col3:
        original_value = sum(p.value for p in positions)
        change = ((final_value - original_value) / original_value * 100) if original_value > 0 else 0
        st.metric("Variação", f"{change:+.2f}%")

    # Check for duplicate date
    existing_positions = db.get_positions_by_date(position_date)

    if existing_positions:
        st.warning(
            f"⚠️ Já existem {len(existing_positions)} posições para a data "
            f"{position_date.strftime('%d/%m/%Y')}. "
            f"Importar novamente irá adicionar posições duplicadas."
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🗑️ Deletar Existentes e Salvar", type="secondary"):
                db.delete_positions_by_date(position_date)
                _import_positions(db, final_positions)
                _clear_xlsx_editing_state()
                st.rerun()

        with col2:
            if st.button("➕ Salvar Mesmo Assim", type="secondary"):
                _import_positions(db, final_positions)
                _clear_xlsx_editing_state()
                st.rerun()

        with col3:
            if st.button("❌ Cancelar", type="secondary"):
                _clear_xlsx_editing_state()
                st.rerun()
    else:
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Salvar Posições", type="primary"):
                _import_positions(db, final_positions)
                _clear_xlsx_editing_state()
                st.rerun()
        with col2:
            if st.button("❌ Cancelar", type="secondary"):
                _clear_xlsx_editing_state()
                st.rerun()


def _clear_xlsx_editing_state():
    """Clear XLSX editing session state"""
    st.session_state.xlsx_positions = None
    st.session_state.xlsx_metadata = None
    st.session_state.xlsx_positions_to_remove = set()
    st.session_state.xlsx_new_positions = []
    st.session_state.xlsx_original_values = {}


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
                percentage=inv_pos.percentage if hasattr(inv_pos, 'percentage') else None,
                quantity=inv_pos.quantity if hasattr(inv_pos, 'quantity') else None
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


def _render_record_contribution(db: Database):
    """Render interface to record contributions to existing assets"""
    st.subheader("💰 Registrar Contribuição")
    st.write("Registre novas contribuições para ativos existentes. Adicione múltiplas contribuições à lista antes de salvar.")

    # Get all positions from the latest date (complete snapshot)
    latest_positions = db.get_latest_positions()

    if not latest_positions:
        st.info("Nenhuma posição encontrada no banco de dados. Adicione posições primeiro usando 'Entrada Manual' ou 'Upload - Histórico Carteira XP'.")
        return

    # Get unique custom labels (excluding None)
    custom_labels = sorted(list(set(
        pos.custom_label for pos in latest_positions
        if pos.custom_label is not None
    )))

    # Initialize session state for contribution recording
    if 'contribution_preview' not in st.session_state:
        st.session_state.contribution_preview = None
    if 'contribution_batch' not in st.session_state:
        st.session_state.contribution_batch = []
    if 'contribution_form_key' not in st.session_state:
        st.session_state.contribution_form_key = 0

    st.subheader("Dados da Contribuição")

    # Custom label filter - OUTSIDE form so it triggers reruns
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_label = st.selectbox(
            "Filtrar por Categoria",
            options=["Todas as Categorias"] + custom_labels,
            help="Filtre os ativos por categoria para facilitar a seleção",
            key="contrib_category_filter"
        )
    with col2:
        st.write("")  # Spacer
        if st.button("🔄 Resetar", help="Mostrar todas as categorias"):
            if "contrib_category_filter" in st.session_state:
                del st.session_state.contrib_category_filter
            st.rerun()

    # Filter positions based on selected custom_label
    if selected_label == "Todas as Categorias":
        filtered_positions = latest_positions
    else:
        filtered_positions = [pos for pos in latest_positions if pos.custom_label == selected_label]

    # Get unique asset names from filtered positions, sorted alphabetically
    asset_names = sorted(list(set(pos.name for pos in filtered_positions)))

    if not asset_names:
        st.warning(f"Nenhum ativo encontrado na categoria '{selected_label}'.")
        return

    # Now start the form with the already-filtered asset list (dynamic key for reset)
    with st.form(f"record_contribution_form_{st.session_state.contribution_form_key}"):
        col1, col2 = st.columns(2)

        with col1:
            # Asset selection
            selected_asset = st.selectbox(
                "Selecione o Ativo",
                options=asset_names,
                help="Escolha o ativo ao qual você deseja contribuir"
            )

            # Contribution amount
            contribution_amount = st.number_input(
                "Valor da Contribuição (R$)",
                min_value=0.0,
                step=100.0,
                help="Digite apenas o valor que você está contribuindo agora (não o total)"
            )

        with col2:
            # Contribution date
            contribution_date = st.date_input(
                "Data da Contribuição",
                value=datetime.now(),
                help="Data em que a contribuição foi feita"
            )

            # Notes
            notes = st.text_area(
                "Observações (opcional)",
                placeholder="Ex: Contribuição anual PGBL para IR 2025",
                help="Adicione qualquer informação relevante sobre esta contribuição"
            )

        # Preview section
        if selected_asset and contribution_amount > 0:
            st.divider()
            st.subheader("Prévia da Operação")

            # Find the current position for this asset
            current_position = next((pos for pos in filtered_positions if pos.name == selected_asset), None)

            if current_position:
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Valor Atual", f"R$ {current_position.value:,.2f}")
                    if current_position.custom_label:
                        st.caption(f"📊 {current_position.custom_label}")

                with col2:
                    st.metric("Contribuição", f"+ R$ {contribution_amount:,.2f}")
                    st.caption(f"📅 {contribution_date.strftime('%d/%m/%Y')}")

                with col3:
                    new_total = current_position.value + contribution_amount
                    change_pct = (contribution_amount / current_position.value * 100) if current_position.value > 0 else 0
                    st.metric("Novo Total", f"R$ {new_total:,.2f}", f"+{change_pct:.1f}%")

                # Show invested value calculation if available
                if current_position.invested_value:
                    st.info(
                        f"💡 **Valor Investido:** R$ {current_position.invested_value:,.2f} → "
                        f"R$ {current_position.invested_value + contribution_amount:,.2f}"
                    )

        # Submit button - changed to "Add to Batch"
        submitted = st.form_submit_button("➕ Adicionar à Lista", type="primary")

        if submitted:
            if not selected_asset:
                st.error("Por favor, selecione um ativo.")
            elif contribution_amount <= 0:
                st.error("Por favor, digite um valor de contribuição maior que zero.")
            else:
                # Validate date is not before last position
                contribution_datetime = datetime.combine(contribution_date, datetime.min.time())
                current_position = next((pos for pos in filtered_positions if pos.name == selected_asset), None)

                if current_position and contribution_datetime < current_position.date:
                    st.error(
                        f"A data da contribuição ({contribution_date.strftime('%d/%m/%Y')}) não pode ser "
                        f"anterior à última posição registrada ({current_position.date.strftime('%d/%m/%Y')})."
                    )
                else:
                    # Add to batch instead of immediate registration
                    batch_item = {
                        'asset_name': selected_asset,
                        'contribution_amount': contribution_amount,
                        'contribution_date': contribution_datetime,
                        'notes': notes if notes else None,
                        'current_value': current_position.value if current_position else 0,
                        'custom_label': current_position.custom_label if current_position else None
                    }
                    st.session_state.contribution_batch.append(batch_item)
                    # Increment form key to reset the form
                    st.session_state.contribution_form_key += 1
                    st.rerun()

    # Show batch preview and register all button
    if st.session_state.contribution_batch:
        st.divider()
        st.subheader("📋 Contribuições a Registrar")

        # Summary metrics
        total_contributions = len(st.session_state.contribution_batch)
        total_amount = sum(item['contribution_amount'] for item in st.session_state.contribution_batch)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Contribuições", total_contributions)
        with col2:
            st.metric("Valor Total", f"R$ {total_amount:,.2f}")
        with col3:
            unique_assets = len(set(item['asset_name'] for item in st.session_state.contribution_batch))
            st.metric("Ativos Distintos", unique_assets)

        # Batch table
        st.write("**Lista de Contribuições:**")
        for idx, item in enumerate(st.session_state.contribution_batch):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1.5, 0.8])

                with col1:
                    st.write(f"**{item['asset_name']}**")
                    if item['custom_label']:
                        st.caption(f"📊 {item['custom_label']}")

                with col2:
                    st.metric("Atual", f"R$ {item['current_value']:,.2f}", label_visibility="collapsed")

                with col3:
                    st.metric("Contribuição", f"+ R$ {item['contribution_amount']:,.2f}", label_visibility="collapsed")

                with col4:
                    new_total = item['current_value'] + item['contribution_amount']
                    st.metric("Novo Total", f"R$ {new_total:,.2f}", label_visibility="collapsed")

                with col5:
                    if st.button("🗑️", key=f"remove_batch_{idx}", help="Remover da lista"):
                        st.session_state.contribution_batch.pop(idx)
                        st.rerun()

                # Show date and notes if available
                caption_parts = [f"📅 {item['contribution_date'].strftime('%d/%m/%Y')}"]
                if item['notes']:
                    caption_parts.append(f"📝 {item['notes']}")
                st.caption(" | ".join(caption_parts))

                st.divider()

        # Register all button
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("💾 Registrar Todas", type="primary", use_container_width=True):
                try:
                    success_count = 0
                    errors = []

                    with st.spinner(f"Registrando {total_contributions} contribuições..."):
                        # Group contributions by date to create complete snapshots
                        from collections import defaultdict
                        contributions_by_date = defaultdict(list)

                        for item in st.session_state.contribution_batch:
                            contributions_by_date[item['contribution_date']].append(item)

                        # Process each date separately to create complete snapshots
                        for contribution_date, date_contributions in sorted(contributions_by_date.items()):
                            try:
                                # Get all positions from the latest date (complete snapshot)
                                base_positions = db.get_latest_positions()

                                if not base_positions:
                                    errors.append(f"Erro: Nenhuma posição base encontrada para {contribution_date.strftime('%d/%m/%Y')}")
                                    continue

                                # Create a dictionary of positions by asset name for easy lookup
                                positions_dict = {pos.name: pos for pos in base_positions}

                                # Track which assets received contributions
                                assets_with_contributions = set()

                                # Update positions for assets that received contributions
                                for item in date_contributions:
                                    asset_name = item['asset_name']

                                    if asset_name not in positions_dict:
                                        errors.append(f"Erro em '{asset_name}': Ativo não encontrado nas posições base")
                                        continue

                                    assets_with_contributions.add(asset_name)

                                    # Get the base position
                                    base_pos = positions_dict[asset_name]

                                    # Calculate new values
                                    new_value = base_pos.value + item['contribution_amount']
                                    previous_invested = base_pos.invested_value or base_pos.value
                                    new_invested = previous_invested + item['contribution_amount']

                                    # Update the position in the dictionary
                                    positions_dict[asset_name] = Position(
                                        name=asset_name,
                                        value=new_value,
                                        main_category=base_pos.main_category,
                                        sub_category=base_pos.sub_category,
                                        custom_label=base_pos.custom_label,
                                        sub_label=base_pos.sub_label,
                                        date=contribution_date,
                                        invested_value=new_invested,
                                        percentage=base_pos.percentage,
                                        quantity=base_pos.quantity,
                                        additional_info=base_pos.additional_info
                                    )

                                # Now save ALL positions (complete snapshot) for this date
                                for asset_name, pos in positions_dict.items():
                                    # Update date to contribution_date if it wasn't already updated
                                    if pos.date != contribution_date:
                                        pos.date = contribution_date

                                    # Save the position
                                    position_id = db.add_position(pos)

                                    # If this asset received a contribution, record it in contributions table
                                    if asset_name in assets_with_contributions:
                                        # Find the contribution item for this asset
                                        contrib_item = next(
                                            (item for item in date_contributions if item['asset_name'] == asset_name),
                                            None
                                        )
                                        if contrib_item:
                                            # Record in contributions table (manually, since add_contribution already created the position)
                                            cursor = db.conn.cursor()
                                            cursor.execute("""
                                                INSERT INTO contributions (
                                                    asset_name, contribution_amount, contribution_date,
                                                    position_id, previous_value, new_total_value, notes
                                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                            """, (
                                                asset_name,
                                                contrib_item['contribution_amount'],
                                                contribution_date.isoformat(),
                                                position_id,
                                                contrib_item['current_value'],
                                                pos.value,
                                                contrib_item['notes']
                                            ))
                                            db.conn.commit()
                                            success_count += 1

                            except Exception as e:
                                errors.append(f"Erro ao processar contribuições de {contribution_date.strftime('%d/%m/%Y')}: {str(e)}")

                    # Clear batch after processing
                    st.session_state.contribution_batch = []

                    # Show results
                    if success_count > 0:
                        st.success(f"✓ {success_count} contribuições registradas com sucesso!")

                    if errors:
                        st.error(f"❌ {len(errors)} erro(s) encontrado(s):")
                        for error in errors:
                            st.error(error)

                    st.rerun()

                except Exception as e:
                    st.error(f"Erro ao processar contribuições: {str(e)}")
                    st.exception(e)

        with col2:
            if st.button("🗑️ Limpar Lista", type="secondary", use_container_width=True):
                st.session_state.contribution_batch = []
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
    # Checkbox to toggle edit mode
    edit_same_date = st.checkbox(
        "✏️ Editar na mesma data",
        value=False,
        help="Marque para editar valores na mesma data. Desmarque para criar posições em uma nova data."
    )

    with col1:
        base_date = st.selectbox(
            "Selecionar Data Base",
            options=available_dates,
            format_func=lambda d: d.strftime('%d/%m/%Y'),
            help="Escolha a data das posições que deseja editar/atualizar"
        )

    with col2:
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


def _render_pdf_image_upload(db: Database):
    """Render PDF/Image file upload with AI extraction"""
    st.subheader("Upload de PDF/Imagem - Extração com IA")

    st.info(
        "📸 **Nova funcionalidade com IA!** Faça upload de extratos em PDF ou imagem e deixe a IA extrair automaticamente as posições.\n\n"
        "✨ Suporta: PDF, PNG, JPG, JPEG\n\n"
        "⚠️ **Importante:** Configure sua chave da API OpenAI no arquivo `.env` antes de usar."
    )

    # Initialize session state for PDF/Image editing
    if 'pdf_image_positions' not in st.session_state:
        st.session_state.pdf_image_positions = None
        st.session_state.pdf_image_metadata = None
        st.session_state.pdf_image_positions_to_remove = set()
        st.session_state.pdf_image_new_positions = []
        st.session_state.pdf_image_original_values = {}
        st.session_state.pdf_page_selection_mode = False
        st.session_state.pdf_selected_pages = []
        st.session_state.pdf_page_thumbnails = {}
        st.session_state.pdf_temp_path = None
        st.session_state.pdf_page_count = 0
        st.session_state.pdf_duplicate_warnings = {}

    # Stage 1: Upload and parse (only show if not currently editing)
    if st.session_state.pdf_image_positions is None:
        # Model selection
        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Selecione o arquivo PDF ou imagem do seu extrato",
                type=["pdf", "png", "jpg", "jpeg"],
                help="Faça upload de um extrato de investimentos em PDF ou imagem"
            )

        with col2:
            model = st.selectbox(
                "Modelo OpenAI",
                options=["gpt-4o", "gpt-4o-mini"],
                index=0,
                help="gpt-4o: Mais preciso, maior custo\ngpt-4o-mini: Mais econômico, boa precisão"
            )

            # Show estimated cost
            if uploaded_file:
                from utils.openai_client import OpenAIExtractor
                file_size_kb = len(uploaded_file.getvalue()) / 1024
                estimated_cost = OpenAIExtractor.estimate_cost(model, file_size_kb)
                st.metric("Custo Estimado", f"${estimated_cost:.4f} USD")

        if uploaded_file is not None:
            try:
                # Validate API key first
                from utils.openai_client import OpenAIExtractor

                try:
                    extractor = OpenAIExtractor()
                except ValueError as e:
                    st.error(str(e))
                    st.stop()

                # Save temporarily
                temp_path = f"/tmp/{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                parser = PDFImageParser(temp_path, model=model)

                # Check if PDF with multiple pages
                page_count = parser.get_page_count()
                is_pdf = uploaded_file.name.lower().endswith('.pdf')

                # Stage 1A: PDF Page Selection (only for multi-page PDFs)
                if is_pdf and page_count > 1 and not st.session_state.pdf_page_selection_mode:
                    _render_page_selection(parser, page_count, model, temp_path)

                # Stage 1B: Process file (single page image, single page PDF, or after page selection)
                elif st.session_state.pdf_page_selection_mode or page_count == 1:
                    _render_pdf_image_processing(parser, model, temp_path, is_pdf, page_count)

            except Exception as e:
                st.error(f"Erro ao processar arquivo: {str(e)}")
                st.exception(e)

    # Stage 2: Edit positions (reuse logic from XLSX)
    else:
        _render_pdf_image_editing(db)


def _render_pdf_image_editing(db: Database):
    """Render editing interface for PDF/Image positions (mirrors XLSX editing)"""
    positions = st.session_state.pdf_image_positions
    metadata = st.session_state.pdf_image_metadata
    position_date = metadata.get('position_date', datetime.now())

    st.subheader("✏️ Revisar e Editar Posições Extraídas")
    st.write("Revise os dados extraídos pela IA, edite valores, remova posições incorretas ou adicione novas antes de salvar.")

    # Show summary
    total_value = sum(p.value for p in positions
                     if positions.index(p) not in st.session_state.pdf_image_positions_to_remove)
    kept_count = len(positions) - len(st.session_state.pdf_image_positions_to_remove)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data da Posição", position_date.strftime('%d/%m/%Y'))
    with col2:
        st.metric("Posições Ativas", f"{kept_count} de {len(positions)}")
    with col3:
        final_total = total_value + sum(p.value for p in st.session_state.pdf_image_new_positions)
        st.metric("Valor Total", f"R$ {final_total:,.2f}")

    st.divider()

    # Show duplicate warnings if any
    duplicate_warnings = st.session_state.pdf_duplicate_warnings
    if duplicate_warnings:
        st.warning(f"⚠️ **{len(duplicate_warnings)} ativos duplicados detectados!** Revise os itens marcados abaixo.")

    # Editable positions table
    st.subheader("Posições Extraídas")
    for idx, pos in enumerate(positions):
        if idx in st.session_state.pdf_image_positions_to_remove:
            continue

        # Check if this position is a duplicate
        is_duplicate = pos.name in duplicate_warnings
        duplicate_pages = duplicate_warnings.get(pos.name, [])

        # Apply styling for duplicates
        if is_duplicate:
            st.markdown(f"""
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                <strong>⚠️ DUPLICADO</strong> - Aparece nas páginas: {', '.join(map(str, duplicate_pages))}
            </div>
            """, unsafe_allow_html=True)

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1, 1])

            with col1:
                # Add warning badge for duplicates
                if is_duplicate:
                    st.write(f"**{pos.name}** ⚠️")
                else:
                    st.write(f"**{pos.name}**")
                st.caption(f"{pos.main_category} - {pos.sub_category}")

            with col2:
                # Show original value
                original_value = st.session_state.pdf_image_original_values.get(idx, pos.value)
                st.metric("Original", f"R$ {original_value:,.2f}", label_visibility="collapsed")

            with col3:
                # Editable value
                new_value = st.number_input(
                    "Novo Valor (R$)",
                    min_value=0.0,
                    value=float(pos.value),
                    step=100.0,
                    key=f"pdf_image_pos_value_{idx}",
                    label_visibility="collapsed"
                )
                pos.value = new_value

            with col4:
                # Show change indicator
                if abs(new_value - original_value) > 0.01:
                    change_pct = ((new_value - original_value) / original_value * 100) if original_value > 0 else 0
                    st.metric("Δ", f"{change_pct:+.1f}%", label_visibility="collapsed")

            with col5:
                if st.button("🗑️", key=f"pdf_image_remove_{idx}", help="Remover esta posição"):
                    st.session_state.pdf_image_positions_to_remove.add(idx)
                    st.rerun()

            st.divider()

    # Section to add new positions
    st.subheader("➕ Adicionar Novas Posições")

    with st.form("pdf_image_add_new_position"):
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
                # Create InvestmentPosition
                new_pos = InvestmentPosition(
                    name=new_name,
                    value=new_value,
                    main_category=new_main_cat,
                    sub_category=new_sub_cat,
                    date=position_date,
                    invested_value=new_invested if new_invested > 0 else None
                )
                st.session_state.pdf_image_new_positions.append(new_pos)
                st.rerun()

    # Show new positions to be added
    if st.session_state.pdf_image_new_positions:
        st.subheader("Novas Posições a Adicionar")
        for idx, pos in enumerate(st.session_state.pdf_image_new_positions):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.write(f"**{pos.name}**")
                st.caption(f"{pos.main_category} - {pos.sub_category}")
            with col2:
                st.write(f"R$ {pos.value:,.2f}")
            with col3:
                if st.button("🗑️", key=f"pdf_image_remove_new_{idx}"):
                    st.session_state.pdf_image_new_positions.pop(idx)
                    st.rerun()

    # Final summary and save
    st.divider()
    _render_pdf_image_final_summary_and_save(db, positions, position_date)


def _render_pdf_image_final_summary_and_save(db: Database, positions: list, position_date: datetime):
    """Render final summary and save options for PDF/Image import"""
    # Calculate final positions
    final_positions = [p for idx, p in enumerate(positions)
                      if idx not in st.session_state.pdf_image_positions_to_remove]
    final_positions.extend(st.session_state.pdf_image_new_positions)
    final_value = sum(p.value for p in final_positions)

    st.subheader("Resumo Final")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Posições", len(final_positions))
    with col2:
        st.metric("Valor Total", f"R$ {final_value:,.2f}")
    with col3:
        original_value = sum(p.value for p in positions)
        change = ((final_value - original_value) / original_value * 100) if original_value > 0 else 0
        st.metric("Variação", f"{change:+.2f}%")

    # Check for duplicate date
    existing_positions = db.get_positions_by_date(position_date)

    if existing_positions:
        st.warning(
            f"⚠️ Já existem {len(existing_positions)} posições para a data "
            f"{position_date.strftime('%d/%m/%Y')}. "
            f"Importar novamente irá adicionar posições duplicadas."
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🗑️ Deletar Existentes e Salvar", type="secondary"):
                db.delete_positions_by_date(position_date)
                _import_positions(db, final_positions)
                _clear_pdf_image_editing_state()
                st.rerun()

        with col2:
            if st.button("➕ Salvar Mesmo Assim", type="secondary"):
                _import_positions(db, final_positions)
                _clear_pdf_image_editing_state()
                st.rerun()

        with col3:
            if st.button("❌ Cancelar", type="secondary"):
                _clear_pdf_image_editing_state()
                st.rerun()
    else:
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Salvar Posições", type="primary"):
                _import_positions(db, final_positions)
                _clear_pdf_image_editing_state()
                st.rerun()
        with col2:
            if st.button("❌ Cancelar", type="secondary"):
                _clear_pdf_image_editing_state()
                st.rerun()


def _render_page_selection(parser, page_count: int, model: str, temp_path: str):
    """Render page selection UI for multi-page PDFs"""
    from utils.openai_client import OpenAIExtractor

    st.subheader(f"📄 Selecionar Páginas ({page_count} páginas encontradas)")
    st.write("Escolha quais páginas você deseja processar para economizar custos. Apenas as páginas selecionadas serão enviadas para a IA.")

    # Cost estimation
    col1, col2, col3 = st.columns(3)
    with col1:
        estimated_cost_per_page = OpenAIExtractor.estimate_cost(model, 200)  # Rough estimate
        st.metric("Custo por Página", f"~${estimated_cost_per_page:.4f} USD")
    with col2:
        selected_count = len([p for p in range(1, page_count + 1) if st.session_state.get(f"page_checkbox_{p}", False)])
        st.metric("Páginas Selecionadas", selected_count)
    with col3:
        total_estimated = estimated_cost_per_page * selected_count
        st.metric("Custo Total Estimado", f"${total_estimated:.4f} USD")

    st.divider()

    # Select All / Deselect All buttons
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("✅ Selecionar Todas", use_container_width=True):
            for page_num in range(1, page_count + 1):
                st.session_state[f"page_checkbox_{page_num}"] = True
            st.rerun()
    with col2:
        if st.button("❌ Limpar Seleção", use_container_width=True):
            for page_num in range(1, page_count + 1):
                st.session_state[f"page_checkbox_{page_num}"] = False
            st.rerun()

    st.divider()

    # Generate and show thumbnails with checkboxes
    with st.spinner("Gerando miniaturas das páginas..."):
        for page_num in range(1, page_count + 1):
            # Generate thumbnail if not cached
            if page_num not in st.session_state.pdf_page_thumbnails:
                try:
                    thumb_base64 = parser.generate_page_thumbnail(page_num, width=200)
                    st.session_state.pdf_page_thumbnails[page_num] = thumb_base64
                except Exception as e:
                    st.session_state.pdf_page_thumbnails[page_num] = None
                    st.warning(f"Erro ao gerar miniatura da página {page_num}: {str(e)}")

    # Display pages with checkboxes
    num_cols = 3  # 3 pages per row
    for row_start in range(1, page_count + 1, num_cols):
        cols = st.columns(num_cols)
        for col_idx, page_num in enumerate(range(row_start, min(row_start + num_cols, page_count + 1))):
            with cols[col_idx]:
                # Show thumbnail if available
                thumb = st.session_state.pdf_page_thumbnails.get(page_num)
                if thumb:
                    st.image(f"data:image/jpeg;base64,{thumb}", caption=f"Página {page_num}", use_container_width=True)
                else:
                    st.info(f"Página {page_num}\n(Miniatura indisponível)")

                # Checkbox for selection
                st.checkbox(
                    f"Processar página {page_num}",
                    key=f"page_checkbox_{page_num}",
                    value=st.session_state.get(f"page_checkbox_{page_num}", page_num == 1)  # Default: select first page
                )

    st.divider()

    # Process selected pages button
    selected_pages = [p for p in range(1, page_count + 1) if st.session_state.get(f"page_checkbox_{p}", False)]

    if not selected_pages:
        st.warning("⚠️ Nenhuma página selecionada. Selecione pelo menos uma página para processar.")
    else:
        if st.button(f"🚀 Processar {len(selected_pages)} Página(s) Selecionada(s)", type="primary", use_container_width=True):
            st.session_state.pdf_selected_pages = selected_pages
            st.session_state.pdf_page_selection_mode = True
            st.session_state.pdf_temp_path = temp_path
            st.session_state.pdf_page_count = page_count
            st.rerun()


def _render_pdf_image_processing(parser, model: str, temp_path: str, is_pdf: bool, page_count: int):
    """Render processing UI with progress for single or multiple pages"""

    # Determine which pages to process
    if is_pdf and st.session_state.pdf_page_selection_mode:
        pages_to_process = st.session_state.pdf_selected_pages
    else:
        pages_to_process = [1]  # Single page (image or single-page PDF)

    # Multi-page processing with progress
    if len(pages_to_process) > 1:
        st.subheader(f"🤖 Processando {len(pages_to_process)} Páginas")

        # Progress container
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()

        all_positions = []
        combined_metadata = {}
        duplicate_warnings = {}

        try:
            # Process pages sequentially
            page_generator = parser.parse_multiple_pages(pages_to_process)

            for progress_update in page_generator:
                status = progress_update.get('status')

                if status == 'processing':
                    progress_pct = (progress_update['current_page'] - 1) / progress_update['total_pages']
                    progress_bar.progress(progress_pct)
                    status_text.info(f"⏳ Processando página {progress_update['page_number']} ({progress_update['current_page']} de {progress_update['total_pages']})...")

                elif status == 'completed':
                    progress_pct = progress_update['current_page'] / progress_update['total_pages']
                    progress_bar.progress(progress_pct)

                    with results_container:
                        st.success(f"✅ Página {progress_update['page_number']}: {progress_update['positions_found']} posições encontradas (Custo: ${progress_update['page_cost']:.4f})")

                elif status == 'error':
                    with results_container:
                        st.error(f"❌ Erro na página {progress_update['page_number']}: {progress_update.get('error', 'Erro desconhecido')}")

            # Get final results (generator returns this after yielding all progress updates)
            all_positions, combined_metadata, duplicate_warnings = page_generator.send(None) if hasattr(page_generator, 'send') else ([], {}, {})

            # Extract the actual values from the generator return
            try:
                all_positions, combined_metadata, duplicate_warnings = next(page_generator)
            except StopIteration as e:
                all_positions, combined_metadata, duplicate_warnings = e.value

            progress_bar.progress(1.0)
            status_text.success("✅ Processamento concluído!")

        except Exception as e:
            st.error(f"Erro durante processamento: {str(e)}")
            st.exception(e)
            return

        positions = all_positions
        metadata = combined_metadata

    else:
        # Single page processing (original flow)
        with st.spinner(f"🤖 Analisando documento com {model}... Isso pode levar alguns segundos..."):
            try:
                positions, metadata = parser.parse()
                duplicate_warnings = {}
            except NotImplementedError as e:
                st.error(str(e))
                return
            except Exception as e:
                st.error(f"Erro ao processar arquivo: {str(e)}")
                st.exception(e)
                return

    if not positions:
        st.error("❌ Nenhuma posição foi encontrada no arquivo. Tente outro arquivo ou verifique a qualidade da imagem.")
        return

    # Show success
    st.success(f"✅ {len(positions)} posições extraídas com sucesso!")

    # Display metadata
    if metadata:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if 'position_date' in metadata:
                st.metric("Data da Posição", metadata['position_date'].strftime('%d/%m/%Y'))
        with col2:
            st.metric("Modelo Usado", metadata.get('model_used', model))
        with col3:
            if 'total_tokens' in metadata:
                st.metric("Tokens Usados", f"{metadata['total_tokens']:,}")
        with col4:
            if 'total_cost' in metadata:
                st.metric("Custo Total", f"${metadata['total_cost']:.4f}")
            elif 'estimated_cost' in metadata:
                st.metric("Custo (est.)", f"${metadata['estimated_cost']:.4f}")

    # Show duplicate warnings if any
    if duplicate_warnings:
        st.warning(f"⚠️ **Avisos de Duplicados:** {len(duplicate_warnings)} ativos aparecem em múltiplas páginas. Revise na próxima etapa.")
        with st.expander("Ver detalhes dos duplicados"):
            for asset_name, pages in duplicate_warnings.items():
                st.write(f"- **{asset_name}**: páginas {', '.join(map(str, pages))}")

    # Show summary by category
    st.subheader("Resumo por Categoria")
    summary = parser.get_summary(positions)
    if 'categories' in summary:
        for cat, data in summary['categories'].items():
            pct = (data['value'] / summary['total_value'] * 100) if summary['total_value'] > 0 else 0
            st.write(f"**{cat}**: {data['count']} posições, R$ {data['value']:,.2f} ({pct:.1f}%)")

    # Show preview table
    st.subheader("Prévia das Posições Extraídas")
    preview_data = []
    preview_number = 30
    for p in positions[:preview_number]:
        preview_data.append({
            'Nome': p.name,
            'Valor': f"R$ {p.value:,.2f}",
            'Categoria': p.main_category,
            'Subcategoria': p.sub_category,
            'Investido': f"R$ {p.invested_value:,.2f}" if p.invested_value else "-"
        })

    st.dataframe(preview_data, use_container_width=True)

    if len(positions) > preview_number:
        st.info(f"Mostrando {preview_number} de {len(positions)} posições...")

    # Button to proceed to editing
    st.divider()
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("✏️ Revisar e Editar Posições", type="primary", use_container_width=True):
            st.session_state.pdf_image_positions = positions
            st.session_state.pdf_image_metadata = metadata
            st.session_state.pdf_duplicate_warnings = duplicate_warnings
            st.session_state.pdf_image_positions_to_remove = set()
            st.session_state.pdf_image_new_positions = []
            # Store original values
            st.session_state.pdf_image_original_values = {idx: p.value for idx, p in enumerate(positions)}
            st.rerun()

    with col2:
        st.caption("💡 **Dica:** Sempre revise os valores extraídos pela IA antes de salvar!")


def _clear_pdf_image_editing_state():
    """Clear PDF/Image editing session state"""
    st.session_state.pdf_image_positions = None
    st.session_state.pdf_image_metadata = None
    st.session_state.pdf_image_positions_to_remove = set()
    st.session_state.pdf_image_new_positions = []
    st.session_state.pdf_image_original_values = {}
    st.session_state.pdf_page_selection_mode = False
    st.session_state.pdf_selected_pages = []
    st.session_state.pdf_page_thumbnails = {}
    st.session_state.pdf_temp_path = None
    st.session_state.pdf_page_count = 0
    st.session_state.pdf_duplicate_warnings = {}
