# lancar_imovel.py
import streamlit as st
import pandas as pd
import bairro


def renderizar_tela_consulta():
    st.title("📍 Mapeamento Territorial - Consulta de Quarteirões")
    st.markdown("---")

    st.subheader("🔍 Filtros de Pesquisa")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        f_bairro = st.text_input("Filtrar por Bairro", key="f_bairro_user")
        f_quarteirao = st.text_input(
            "Filtrar por Nº Quarteirão", key="f_quarteirao_user"
        )
    with col_f2:
        f_rua = st.text_input("Filtrar por Rua", key="f_rua_user")
        f_imovel = st.text_input("Filtrar por Nº Imóvel", key="f_imovel_user")
    with col_f3:
        f_tipo = st.selectbox(
            "Filtrar por Tipo",
            ["Todos", "Residência", "Comércio", "Terreno Baldio", "Outro"],
            key="f_tipo_user",
        )

    # Busca de dados e resumo dos filtros
    dados = bairro.listar_quarteiroes(
        f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo
    )
    total_imoveis, detalhe_tipos = bairro.obter_resumo_filtros(
        f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo
    )

    st.markdown("---")

    # Painel de Resumo
    st.subheader("📊 Resumo dos Filtros Aplicados")
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

    m_col1.metric("Total de Imóveis", total_imoveis)
    m_col2.metric("Residências", detalhe_tipos.get("Residência", 0))
    m_col3.metric("Comércios", detalhe_tipos.get("Comércio", 0))
    m_col4.metric("Terrenos Baldios", detalhe_tipos.get("Terreno Baldio", 0))
    m_col5.metric("Outros", detalhe_tipos.get("Outro", 0))

    st.markdown("---")
    st.subheader(f"Lista de Registros ({len(dados)})")

    if dados:
        df = pd.DataFrame(
            dados,
            columns=[
                "ID",
                "Bairro",
                "Quarteirão",
                "Rua",
                "Lado",
                "Nº Imóvel",
                "Tipo",
            ],
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum imóvel corresponde aos filtros selecionados.")
