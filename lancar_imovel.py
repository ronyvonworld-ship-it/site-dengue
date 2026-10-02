# lancar_imovel.py
import pandas as pd
import streamlit as st
import bairro


def colorir_linha_por_situacao(row):
    situacao = row.get("Status Ciclo")
    if situacao == "Normal":
        return [
            "background-color: #d4edda; color: #155724; font-weight: bold;"
        ] * len(row)
    elif situacao == "Fechado":
        return [
            "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        ] * len(row)
    else:
        return [""] * len(row)


def renderizar_tela_consulta():
    st.title("📍 Mapeamento Territorial - Consulta e Lançamento Diário")

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

    dados = bairro.listar_quarteiroes_com_status(
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

    col_leg1, col_leg2, col_leg3 = st.columns(3)
    col_leg1.markdown("🟩 **Verde**: Lançado como *Normal* no ciclo atual")
    col_leg2.markdown("🟥 **Vermelho**: Lançado como *Fechado* no ciclo atual")
    col_leg3.markdown("⬜ **Branco**: Sem lançamento no ciclo atual")

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
                "Status Ciclo",
            ],
        )

        df_estilizado = df.style.apply(colorir_linha_por_situacao, axis=1)

        evento_selecao = st.dataframe(
            df_estilizado,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            column_config={
                "Status Ciclo": st.column_config.TextColumn(
                    "Status no Ciclo Atual",
                    help="Situação do último lançamento feito no ciclo bimestral corrente.",
                )
            },
        )

        linhas_selecionadas = evento_selecao.get("selection", {}).get(
            "rows", []
        )

        if linhas_selecionadas:
            idx_selecionado = linhas_selecionadas[0]
            imovel_sel = df.iloc[idx_selecionado]
            id_imovel = imovel_sel["ID"]

            st.markdown("---")
            st.subheader(f"📝 Lançamento Diário para o Imóvel ID #{id_imovel}")

            # Resumo do imóvel selecionado
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"**Bairro:** {imovel_sel['Bairro']}")
            c2.markdown(f"**Quarteirão:** {imovel_sel['Quarteirão']}")
            c3.markdown(
                f"**Rua e Nº:** {imovel_sel['Rua']}, {imovel_sel['Nº Imóvel']}"
            )
            c4.markdown(f"**Tipo:** {imovel_sel['Tipo']}")

            # Controles dinâmicos com seletores fora do form para atualizar na hora
            situacao = st.radio(
                "Situação do Imóvel:",
                ["Normal", "Fechado"],
                horizontal=True,
                key=f"situacao_{id_imovel}",
            )

            depositos_eliminados = 0
            fez_tratamento = "Não"
            depositos_tratados = 0
            gramas_medicamento = 0.0

            if situacao == "Normal":
                col_dep1, col_dep2 = st.columns(2)

                with col_dep1:
                    depositos_eliminados = st.number_input(
                        "Depósitos Eliminados",
                        min_value=0,
                        step=1,
                        value=0,
                        key=f"dep_elim_{id_imovel}",
                    )

                with col_dep2:
                    fez_tratamento = st.selectbox(
                        "Foi feito tratamento?",
                        ["Não", "Sim"],
                        key=f"fez_trat_{id_imovel}",
                    )

                if fez_tratamento == "Sim":
                    col_trat1, col_trat2 = st.columns(2)
                    with col_trat1:
                        depositos_tratados = st.number_input(
                            f"Depósitos Tratados (Máx: {depositos_eliminados})",
                            min_value=0,
                            max_value=max(depositos_eliminados, 0),
                            step=1,
                            value=min(1, depositos_eliminados)
                            if depositos_eliminados > 0
                            else 0,
                            key=f"dep_trat_{id_imovel}",
                        )

                    with col_trat2:
                        gramas_medicamento = st.number_input(
                            "Quantidade de Medicamento Utilizado (g)",
                            min_value=0.0,
                            step=0.5,
                            format="%.2f",
                            key=f"gramas_{id_imovel}",
                        )

            st.markdown(" ")
            if st.button(
                "💾 Salvar Lançamento no Diário",
                type="primary",
                use_container_width=True,
                key=f"btn_salvar_{id_imovel}",
            ):
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

                    bairro.salvar_registro_diario(dados_registro)
                    st.success(
                        "Lançamento salvo e sincronizado no Dropbox com sucesso!"
                    )
                    st.rerun()

    else:
        st.info("Nenhum imóvel corresponde aos filtros selecionados.")
