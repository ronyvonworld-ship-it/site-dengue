# lancar_imovel.py
import pandas as pd
import streamlit as st

import bairro


def renderizar_tela_consulta():
    st.title("📍 Mapeamento Territorial - Consulta e Lançamento Diário")

    # Garante que o arquivo bairro.db é baixado do Dropbox antes de carregar
    with st.spinner("🔄 Carregando dados atualizados do Dropbox..."):
        try:
            bairro.carregar_db_do_dropbox(forcar=True)
        except Exception as e:
            st.warning(f"⚠️ Aviso de conexão com Dropbox: {e}")

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

    # Busca de dados e resumo dos filtros após o download do Dropbox
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
    st.info("💡 Clique em uma linha da tabela para realizar o lançamento.")

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

        # Habilita seleção de 1 linha na tabela
        evento_selecao = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
        )

        # Verifica se alguma linha foi selecionada pelo usuário
        linhas_selecionadas = evento_selecao.get("selection", {}).get(
            "rows", []
        )

        if linhas_selecionadas:
            idx_selecionado = linhas_selecionadas[0]
            imovel_sel = df.iloc[idx_selecionado]

            st.markdown("---")
            st.subheader(
                f"📝 Lançamento Diário para o Imóvel ID #{imovel_sel['ID']}"
            )

            # Exibe resumo do imóvel selecionado
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"**Bairro:** {imovel_sel['Bairro']}")
            c2.markdown(f"**Quarteirão:** {imovel_sel['Quarteirão']}")
            c3.markdown(
                f"**Rua e Nº:** {imovel_sel['Rua']}, {imovel_sel['Nº Imóvel']}"
            )
            c4.markdown(f"**Tipo:** {imovel_sel['Tipo']}")

            # Formulário de lançamento
            with st.form(key=f"form_lancamento_{imovel_sel['ID']}"):
                situacao = st.radio(
                    "Situação do Imóvel:",
                    ["Normal", "Fechado"],
                    horizontal=True,
                )

                depositos_eliminados = 0
                fez_tratamento = "Não"
                depositos_tratados = 0
                gramas_medicamento = 0.0

                if situacao == "Normal":
                    col_dep1, col_dep2 = st.columns(2)

                    with col_dep1:
                        depositos_eliminados = st.number_input(
                            "Depósitos Eliminados", min_value=0, step=1, value=0
                        )

                    with col_dep2:
                        fez_tratamento = st.selectbox(
                            "Foi feito tratamento?", ["Não", "Sim"]
                        )

                    if fez_tratamento == "Sim":
                        col_trat1, col_trat2 = st.columns(2)
                        with col_trat1:
                            depositos_tratados = st.number_input(
                                f"Depósitos Tratados (Máx: {depositos_eliminados})",
                                min_value=0,
                                max_value=depositos_eliminados,
                                step=1,
                                value=min(1, depositos_eliminados)
                                if depositos_eliminados > 0
                                else 0,
                                help="O número de depósitos tratados não pode ser maior que o número de depósitos eliminados.",
                            )

                        with col_trat2:
                            gramas_medicamento = st.number_input(
                                "Quantidade de Medicamento Utilizado (g)",
                                min_value=0.0,
                                step=0.5,
                                format="%.2f",
                            )

                btn_salvar = st.form_submit_button(
                    "💾 Salvar Lançamento no Diário"
                )

                if btn_salvar:
                    if (
                        situacao == "Normal"
                        and fez_tratamento == "Sim"
                        and depositos_tratados > depositos_eliminados
                    ):
                        st.error(
                            "❌ Erro: Depósitos tratados não podem ser maiores que os eliminados!"
                        )
                    else:
                        dados_registro = (
                            int(imovel_sel["ID"]),
                            str(imovel_sel["Bairro"]),
                            str(imovel_sel["Quarteirão"]),
                            str(imovel_sel["Rua"]),
                            str(imovel_sel["Nº Imóvel"]),
                            str(imovel_sel["Tipo"]),
                            situacao,
                            depositos_eliminados,
                            fez_tratamento,
                            depositos_tratados,
                            gramas_medicamento,
                        )

                        # Salva no banco SQLite local (diario.db) e envia para o Dropbox
                        bairro.salvar_registro_diario(dados_registro)
                        st.success(
                            "Lançamento salvo e sincronizado no Dropbox com sucesso!"
                        )

    else:
        st.info("Nenhum imóvel corresponde aos filtros selecionados.")
