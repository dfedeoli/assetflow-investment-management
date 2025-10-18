"""
Investment Portfolio Planner - Main Application

A Streamlit app for tracking investment portfolios, analyzing allocations,
and generating rebalancing recommendations.
"""

import streamlit as st
from database.db import Database
from components.upload import render_upload_component
from components.dashboard import render_dashboard_component
from components.history import render_history_component
from components.previdencia import render_previdencia_component
from utils.gdrive_backup import (
    authenticate_google_drive,
    upload_backup_to_drive,
    list_backups_from_drive,
    download_backup_from_drive,
    delete_backup_from_drive,
    format_backup_display_name,
    GoogleDriveBackupError
)


# Page configuration
st.set_page_config(
    page_title="AssetFlow - Investment Management",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize session state variables"""
    if 'db' not in st.session_state:
        st.session_state.db = Database()

    # Initialize Google Drive credentials in session state
    if 'gdrive_credentials' not in st.session_state:
        st.session_state.gdrive_credentials = None

    # Track last backup time
    if 'last_backup_time' not in st.session_state:
        st.session_state.last_backup_time = None

    # Track OAuth flow state
    if 'gdrive_auth_url' not in st.session_state:
        st.session_state.gdrive_auth_url = None


def render_google_drive_section(db: Database):
    """Render Google Drive backup/restore controls in sidebar"""
    st.sidebar.subheader("☁️ Google Drive")

    # Check if authenticated
    is_authenticated = st.session_state.gdrive_credentials is not None

    if not is_authenticated:
        # Check if we're in the middle of OAuth flow
        if st.session_state.gdrive_auth_url:
            # Show the authorization URL and code input
            st.sidebar.markdown("**🔐 Autenticação Google Drive**")
            st.sidebar.markdown("**1️⃣ Clique no link abaixo:**")

            # Make the URL clickable using markdown link
            st.sidebar.markdown(f"[🔗 Autorizar AssetFlow no Google Drive]({st.session_state.gdrive_auth_url})")

            st.sidebar.markdown("**2️⃣ Copie o código da URL**")
            st.sidebar.caption("Após autorizar, copie tudo que vem depois de 'code=' na URL")

            # Input for authorization code
            auth_code = st.sidebar.text_input(
                "**3️⃣ Cole o código aqui:**",
                placeholder="4/0AbC...XyZ",
                key="auth_code_input"
            )

            col1, col2 = st.sidebar.columns(2)

            with col1:
                if st.button("✅ Confirmar", use_container_width=True):
                    if auth_code:
                        try:
                            with st.spinner("Finalizando autenticação..."):
                                creds, _ = authenticate_google_drive(auth_code=auth_code.strip())
                                if creds:
                                    st.session_state.gdrive_credentials = creds
                                    st.session_state.gdrive_auth_url = None
                                    st.success("✅ Conectado ao Google Drive!")
                                    st.rerun()
                                else:
                                    st.error("❌ Falha ao obter credenciais")
                        except GoogleDriveBackupError as e:
                            st.error(f"❌ Erro: {str(e)}")
                            st.sidebar.caption("Tente novamente ou clique em Cancelar")
                        except Exception as e:
                            st.error(f"❌ Erro inesperado: {str(e)}")
                    else:
                        st.sidebar.warning("Por favor, cole o código de autorização")

            with col2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.gdrive_auth_url = None
                    st.rerun()

        else:
            # Show initial connect button
            if st.sidebar.button("🔐 Conectar ao Google Drive", use_container_width=True):
                try:
                    # Try to get existing credentials or start OAuth flow
                    creds, auth_url = authenticate_google_drive()

                    if creds:
                        # Already have valid credentials
                        st.session_state.gdrive_credentials = creds
                        st.success("✅ Conectado ao Google Drive!")
                        st.rerun()
                    elif auth_url:
                        # Need to do OAuth flow
                        st.session_state.gdrive_auth_url = auth_url
                        st.rerun()

                except GoogleDriveBackupError as e:
                    st.error(f"❌ Erro de autenticação: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Erro inesperado: {str(e)}")

            # Show help text
            st.sidebar.caption("Configure primeiro o Google Drive API seguindo GOOGLE_DRIVE_SETUP.md")

    else:
        # Show backup button
        if st.sidebar.button("💾 Backup para Drive", use_container_width=True):
            try:
                with st.spinner("Fazendo upload do backup..."):
                    file_id, filename = upload_backup_to_drive(
                        db.db_path,
                        st.session_state.gdrive_credentials
                    )
                    from datetime import datetime
                    st.session_state.last_backup_time = datetime.now()
                    st.success(f"✅ Backup criado: {filename}")
            except GoogleDriveBackupError as e:
                st.error(f"❌ Erro no backup: {str(e)}")
            except Exception as e:
                st.error(f"❌ Erro inesperado: {str(e)}")

        # Show restore functionality
        st.sidebar.markdown("**📥 Restaurar Backup**")

        try:
            backups = list_backups_from_drive(st.session_state.gdrive_credentials)

            if backups:
                # Create dropdown with backup options
                backup_options = {format_backup_display_name(b): b['id'] for b in backups}
                selected_backup_name = st.sidebar.selectbox(
                    "Escolha um backup:",
                    options=list(backup_options.keys()),
                    label_visibility="collapsed"
                )

                col1, col2 = st.sidebar.columns(2)

                with col1:
                    if st.button("📥 Restaurar", use_container_width=True):
                        selected_id = backup_options[selected_backup_name]

                        # Confirm restoration
                        if 'confirm_restore' not in st.session_state:
                            st.session_state.confirm_restore = False

                        st.session_state.confirm_restore = True

                        if st.session_state.confirm_restore:
                            try:
                                with st.spinner("Restaurando backup..."):
                                    safety_backup = download_backup_from_drive(
                                        selected_id,
                                        db.db_path,
                                        st.session_state.gdrive_credentials
                                    )

                                    # Reinitialize database connection
                                    st.session_state.db = Database(db.db_path)

                                    st.success(f"✅ Backup restaurado com sucesso!")
                                    if safety_backup:
                                        st.info(f"💾 Backup de segurança salvo em: {safety_backup}")

                                    st.session_state.confirm_restore = False
                                    st.rerun()

                            except GoogleDriveBackupError as e:
                                st.error(f"❌ Erro ao restaurar: {str(e)}")
                                st.session_state.confirm_restore = False
                            except Exception as e:
                                st.error(f"❌ Erro inesperado: {str(e)}")
                                st.session_state.confirm_restore = False

                with col2:
                    if st.button("🗑️ Deletar", use_container_width=True):
                        selected_id = backup_options[selected_backup_name]

                        try:
                            with st.spinner("Deletando backup..."):
                                delete_backup_from_drive(
                                    selected_id,
                                    st.session_state.gdrive_credentials
                                )
                                st.success("✅ Backup deletado!")
                                st.rerun()

                        except GoogleDriveBackupError as e:
                            st.error(f"❌ Erro ao deletar: {str(e)}")
                        except Exception as e:
                            st.error(f"❌ Erro inesperado: {str(e)}")

            else:
                st.sidebar.caption("Nenhum backup encontrado no Google Drive")

        except GoogleDriveBackupError as e:
            st.sidebar.error(f"❌ Erro ao listar backups: {str(e)}")
        except Exception as e:
            st.sidebar.error(f"❌ Erro inesperado: {str(e)}")

        # Show last backup time if available
        if st.session_state.last_backup_time:
            from datetime import datetime
            time_str = st.session_state.last_backup_time.strftime('%d/%m/%Y %H:%M:%S')
            st.sidebar.caption(f"Último backup: {time_str}")

        # Disconnect button
        if st.sidebar.button("🔓 Desconectar", use_container_width=True):
            st.session_state.gdrive_credentials = None
            st.session_state.last_backup_time = None
            st.rerun()


def render_sidebar():
    """Render sidebar with navigation and statistics"""
    st.sidebar.title("💰 AssetFlow - Investment Management")
    st.sidebar.markdown("---")

    # Navigation
    page = st.sidebar.radio(
        "Navegação",
        ["📊 Carteira de Investimento", "💼 Previdência", "📈 Histórico", "📁 Importar Dados"],
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")

    # Database statistics
    db = st.session_state.db
    stats = db.get_summary_statistics()

    st.sidebar.subheader("Estatísticas")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Posições", stats['total_positions'])
        st.metric("Categorias", stats['total_targets'])

    with col2:
        st.metric("Snapshots", stats['total_dates'])
        st.metric("Mapeamentos", stats['total_mappings'])

    if stats['unmapped_assets'] > 0:
        st.sidebar.warning(f"⚠️ {stats['unmapped_assets']} ativos não classificados")

    # Latest date info
    dates = db.get_all_dates()
    if dates:
        latest_date = dates[0]
        st.sidebar.info(f"📅 Última atualização:\n{latest_date.strftime('%d/%m/%Y')}")

    st.sidebar.markdown("---")

    # Google Drive Backup/Restore Section
    render_google_drive_section(db)

    return page


def render_home():
    """Render home/welcome page"""
    st.title("💰 Investment Portfolio Planner")

    st.markdown("""
    ## Bem-vindo!

    Este aplicativo ajuda você a gerenciar seu portfólio de investimentos:

    ### 📁 Importar Dados
    - Faça upload de arquivos XLSX da sua corretora
    - Adicione posições manualmente
    - Suporte para formatos complexos com múltiplas categorias

    ### 📊 Carteira de Investimento
    - Visualize sua alocação atual
    - Compare com suas metas
    - Receba sugestões de rebalanceamento
    - Calcule onde investir novo dinheiro
    - Crie categorias personalizadas de investimento
    - Mapeie ativos para suas categorias
    - Defina metas de alocação

    ### 📈 Histórico
    - Acompanhe a evolução do patrimônio
    - Compare diferentes períodos
    - Analise mudanças na alocação

    ---

    **Para começar:**
    1. Importe suas posições na aba "Importar Dados"
    2. Classifique seus ativos na aba "Carteira de Investimentos"
    3. Defina suas metas de alocação
    4. Visualize análises e recomendações no Carteira de Investimento
    """)

    # Quick start guide
    db = st.session_state.db
    stats = db.get_summary_statistics()

    st.divider()
    st.subheader("Status Atual")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if stats['total_positions'] > 0:
            st.success(f"✅ {stats['total_positions']} posições")
        else:
            st.error("❌ Nenhuma posição")

    with col2:
        if stats['total_mappings'] > 0:
            st.success(f"✅ {stats['total_mappings']} mapeamentos")
        else:
            st.warning("⚠️ Sem mapeamentos")

    with col3:
        if stats['total_targets'] > 0:
            st.success(f"✅ {stats['total_targets']} metas")
        else:
            st.warning("⚠️ Sem metas")

    with col4:
        if stats['unmapped_assets'] == 0 and stats['total_positions'] > 0:
            st.success("✅ Tudo classificado")
        elif stats['unmapped_assets'] > 0:
            st.error(f"❌ {stats['unmapped_assets']} não classificados")
        else:
            st.info("ℹ️ Aguardando dados")

    # Next steps
    if stats['total_positions'] == 0:
        st.info("👉 **Próximo passo:** Vá para 'Importar Dados' para adicionar suas posições.")
    elif stats['unmapped_assets'] > 0:
        st.info("👉 **Próximo passo:** Vá para 'Carteira de Investimentos' para classificar seus ativos.")
    elif stats['total_targets'] == 0:
        st.info("👉 **Próximo passo:** Vá para 'Carteira de Investimentos' e defina suas metas de alocação.")
    else:
        st.success("👍 **Tudo pronto!** Explore o Carteira de Investimento e o Histórico.")


def main():
    """Main application entry point"""
    initialize_session_state()

    # Render sidebar and get selected page
    page = render_sidebar()

    # Render selected page
    db = st.session_state.db

    if page == "📊 Carteira de Investimento":
        render_dashboard_component(db)
    elif page == "📁 Importar Dados":
        render_upload_component(db)
    elif page == "💼 Previdência":
        render_previdencia_component(db)
    elif page == "📈 Histórico":
        render_history_component(db)
    else:
        render_home()


if __name__ == "__main__":
    main()
