"""
Asset classification and mapping component
"""

import streamlit as st
from database.db import Database


def render_classification_component(db: Database):
    """Render asset classification interface"""
    st.header("🏷️ Classificação de Ativos")

    st.markdown("""
    Classifique seus ativos em categorias personalizadas para melhor análise.
    Isso permite agrupar diferentes ativos por estratégia ou objetivo de investimento.
    """)

    tab1, tab2, tab3 = st.tabs(["Classificar Ativos", "Gerenciar Mapeamentos", "Definir Metas"])

    with tab1:
        _render_asset_classification(db)

    with tab2:
        _render_mapping_management(db)

    with tab3:
        _render_target_management(db)


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


def _select_labels_or_create_new(existing_labels):
    # Allow selecting existing label or creating new
    label_option = st.radio(
        "Opção",
        ["Usar Categoria Existente", "Criar Nova Categoria"],
        horizontal=True
    )

    if label_option == "Usar Categoria Existente":
        if existing_labels:
            custom_label = st.selectbox("Categoria", existing_labels)
        else:
            st.warning("Nenhuma categoria existente. Crie uma nova.")
            custom_label = st.text_input("Nova Categoria")
    else:
        custom_label = st.text_input("Nome da Nova Categoria", placeholder="Ex: Renda Fixa Conservadora")
    return custom_label


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
                    # Allow inline editing
                    new_label = st.text_input(
                        "Nova categoria",
                        value=mapping.custom_label,
                        key=f"edit_{mapping.id}",
                        label_visibility="collapsed"
                    )

                with col3:
                    if st.button("🗑️", key=f"delete_{mapping.id}", help="Deletar mapeamento"):
                        db.delete_mapping(mapping.asset_name)
                        st.rerun()

                    if new_label != mapping.custom_label:
                        if st.button("💾", key=f"save_{mapping.id}", help="Salvar alteração"):
                            db.add_or_update_mapping(mapping.asset_name, new_label)
                            st.rerun()

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
    st.subheader("Metas de Alocação")

    # Emergency Reserve Section (Separate from targets)
    st.markdown("### 🔒 Reserva de Emergência")
    st.info(
        "A categoria **Segurança** é sua reserva de emergência. Defina um valor mínimo "
        "e qualquer excesso será automaticamente disponibilizado para rebalanceamento."
    )

    seguranca_target = db.get_target("Segurança")
    current_reserve = seguranca_target.reserve_amount if seguranca_target and seguranca_target.reserve_amount else 0.0

    with st.form("reserve_form"):
        reserve_amount = st.number_input(
            "Valor Mínimo de Reserva de Segurança (R$)",
            min_value=0.0,
            value=current_reserve,
            step=1000.0,
            help="Valor mínimo a manter sempre na categoria Segurança. O excesso será disponibilizado para rebalanceamento nas outras categorias."
        )

        reserve_submitted = st.form_submit_button("💾 Salvar Reserva de Emergência", type="primary")

        if reserve_submitted:
            # Save with 0% target so it doesn't appear in dashboard
            reserve_amt = reserve_amount if reserve_amount > 0 else None
            db.add_or_update_target("Segurança", 0.0, reserve_amt)
            st.success("✓ Reserva de emergência salva com sucesso!")
            st.rerun()

    # Show current reserve
    if current_reserve > 0:
        st.success(f"✅ Reserva atual configurada: **R$ {current_reserve:,.2f}**")
    else:
        st.info("ℹ️ Nenhuma reserva de emergência configurada.")

    st.divider()

    # Target Allocations Section
    st.markdown("### 📊 Alocação das Demais Categorias")

    st.info(
        "⚠️ **Importante:** Apenas categorias com metas definidas aparecerão no Dashboard. "
        "A categoria Segurança não deve ter meta percentual."
    )

    st.markdown("""
    Defina a porcentagem ideal que cada categoria deve representar no seu portfólio.
    O sistema irá comparar sua posição atual com as metas e sugerir rebalanceamentos.
    """)

    # Get all custom labels from mappings (excluding Segurança)
    mappings = db.get_all_mappings()
    all_labels = sorted(set(m.custom_label for m in mappings if m.custom_label != "Segurança"))

    if not all_labels:
        st.warning("⚠️ Classifique seus ativos primeiro antes de definir metas.")
        return

    # Get existing targets (excluding Segurança)
    existing_targets = db.get_all_targets()
    targets_dict = {t.custom_label: t.target_percentage for t in existing_targets if t.custom_label != "Segurança"}

    # Form to add/edit targets
    st.subheader("Definir Metas")

    with st.form("target_form"):
        st.write("Defina a porcentagem alvo para cada categoria:")

        targets_input = {}
        total_percentage = 0

        # Create input for each label (Segurança already excluded from all_labels)
        for label in all_labels:
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
                for label, target_pct in targets_input.items():
                    if target_pct > 0:  # Only save non-zero targets
                        db.add_or_update_target(label, target_pct, None)

                st.success("✓ Metas salvas com sucesso!")
                st.rerun()

    # Display current targets (excluding Segurança)
    st.divider()
    st.subheader("Metas Atuais")

    # Filter out Segurança from display
    display_targets = [t for t in existing_targets if t.custom_label != "Segurança"]

    if display_targets:
        for target in display_targets:
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.write(target.custom_label)

            with col2:
                st.write(f"{target.target_percentage:.1f}%")

            with col3:
                if st.button("🗑️", key=f"del_target_{target.id}", help="Deletar meta"):
                    db.delete_target(target.custom_label)
                    st.rerun()
    else:
        st.info("Nenhuma meta definida ainda.")

    # Quick preset options
    st.divider()
    st.subheader("Presets de Alocação")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 Conservador (80/20)", help="80% Renda Fixa, 20% Variável"):
            st.info("Implemente presets conforme necessário")

    with col2:
        if st.button("⚖️ Moderado (60/40)", help="60% Renda Fixa, 40% Variável"):
            st.info("Implemente presets conforme necessário")

    with col3:
        if st.button("🚀 Agressivo (30/70)", help="30% Renda Fixa, 70% Variável"):
            st.info("Implemente presets conforme necessário")
