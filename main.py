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
