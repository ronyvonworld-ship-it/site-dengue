from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

import bairro


def colorir_linha_por_situacao(row):
    situacao = row.get("Status Ciclo")

    if situacao in ["Normal", "Recuperado"]:
        return ["background-color: #d4edda; color: #155724; font-weight: bold;"] * len(row)
    elif situacao == "Fechado":
        return ["background-color: #f8d7da; color: #721c24; font-weight: bold;"] * len(row)
    else:
        return [""] * len(row)


def renderizar_tela_consulta():
    usuario_logado = st.session_state.get("usuario_atual", "Operador")
    
    # --- CABEÇALHO PADRÃO ELEGANTE ---
    st.markdown(
        """
        <div style="text-align: center; padding: 5px 0px 15px 0px;">
            <h1 style="color: #d9534f; margin-bottom: 0px; font-size: 2.1rem;">🦟 COMBATE À DENGUE</h1>
            <h3 style="color: #4f4f4f; margin-top: 5px; font-weight: 500; font-size: 1.3rem;">Painel do Agente de Campo • Acari/RN</h3>
            <p style="color: #6c757d; font-size: 0.95rem; margin-top: -5px;">Prefeitura Municipal de Acari | <b>Secretaria de Saúde</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("---")

    # --- EXIBIÇÃO DA DATA E CICLO ATUAL (AGENTE) - HORÁRIO DE BRASÍLIA ---
    num_ciclo, ano_ciclo, dt_inicio_ciclo, dt_fim_ciclo = bairro.obter_info_ciclo_atual()
    hoje_brasilia = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    hoje_formatado = hoje_brasilia.strftime("%d/%m/%Y")
    
    st.info(
        f"👤 **Agente Logado:** `{usuario_logado}` | "
        f"📅 **Data de Hoje:** `{hoje_formatado}` | "
        f"🔄 **Ciclo Atual:** `{num_ciclo}º Ciclo de {ano_ciclo}` "
        f"(Período: `{dt_inicio_ciclo[:10]}` até `{dt_fim_ciclo[:10]}`)"
    )

    with st.spinner("🔄 Carregando dados atualizados do Dropbox..."):
        try:
            bairro.carregar_db_do_dropbox(forcar=True)
        except Exception as e:
            st.warning(f"⚠️ Aviso de conexão com Dropbox: {e}")

    # --- BOTÃO / PAINEL DE RESUMO INDIVIDUAL DO USUÁRIO ---
    with st.expander("📊 Meu Resumo de Produção (Clique para expandir/recolher)", expanded=False):
        st.subheader(f"📊 Resumo de Trabalho do Agente: `{usuario_logado}`")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            dt_inicio_user = st.date_input("Data Inicial", value=hoje_brasilia, key="u_dt_inicio")
        with col_d2:
            dt_fim_user = st.date_input("Data Final", value=hoje_brasilia, key="u_dt_fim")

        if dt_inicio_user > dt_fim_user:
            st.error("⚠️ A data inicial não pode ser maior que a data final.")
        else:
            resumo_u = bairro.obter_resumo_por_usuario_e_datas(usuario_logado, dt_inicio_user, dt_fim_user)

            st.markdown("##### 📍 Imóveis Vistoriados")
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Total Lançados", resumo_u["total_lancados"])
            m2.metric("Normal 🟩", resumo_u["total_normal"])
            m3.metric("Fechado 🟥", resumo_u["total_fechado"])
            m4.metric("Recuperado 🟩", resumo_u["total_recuperado"])
            m5.metric("Casas Trabalhadas", resumo_u["casas_trabalhadas"])
            m6.metric("Casas Informadas", resumo_u["casas_informadas"])

            st.markdown("##### 🏠 Vistorias por Tipo de Imóvel")
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Residências", resumo_u["total_residencia"])
            t2.metric("Comércios", resumo_u["total_comercio"])
            t3.metric("Terrenos Baldios", resumo_u["total_terreno"])
            t4.metric("Outros", resumo_u["total_outro"])

            st.markdown("##### 🧪 Insumos e Depósitos")
            i1, i2, i3 = st.columns(3)
            i1.metric("Depósitos Eliminados", resumo_u["total_eliminados"])
            i2.metric("Depósitos Tratados", resumo_u["total_tratados"])
            i3.metric("Medicamento (g)", f"{resumo_u['total_gramas']:.2f} g")

    st.markdown("---")
    st.subheader("🔍 Filtros de Pesquisa")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        f_bairro = st.text_input("Filtrar por Bairro", key="f_bairro_user")
        f_quarteirao = st.text_input("Filtrar por Nº Quarteirão", key="f_quarteirao_user")
    with col_f2:
        f_rua = st.text_input("Filtrar por Rua", key="f_rua_user")
        f_imovel = st.text_input("Filtrar por Nº Imóvel", key="f_imovel_user")
    with col_f3:
        f_tipo = st.selectbox(
            "Filtrar por Tipo",
            ["Todos", "Residência", "Comércio", "Terreno Baldio", "Outro"],
            key="f_tipo_user",
        )

    # Opção para filtrar apenas imóveis fechados
    apenas_fechados = st.toggle("🔴 Exibir apenas imóveis com status FECHADO neste ciclo", key="f_apenas_fechados")

    dados = bairro.listar_quarteiroes_com_status(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)
    total_imoveis, detalhe_tipos = bairro.obter_resumo_filtros(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)

    st.markdown("---")
    st.subheader("📊 Resumo dos Filtros Aplicados")
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    m_col1.metric("Total de Imóveis", total_imoveis)
    m_col2.metric("Residências", detalhe_tipos.get("Residência", 0))
    m_col3.metric("Comércios", detalhe_tipos.get("Comércio", 0))
    m_col4.metric("Terrenos Baldios", detalhe_tipos.get("Terreno Baldio", 0))
    m_col5.metric("Outros", detalhe_tipos.get("Outro", 0))

    st.markdown("---")

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

        if apenas_fechados:
            df = df[df["Status Ciclo"] == "Fechado"]

        if not df.empty:
            df_estilizado = df.style.apply(colorir_linha_por_situacao, axis=1)

            # Renderizamos a tabela e capturamos a seleção do usuário
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

            linhas_selecionadas = evento_selecao.get("selection", {}).get("rows", [])

            # Se um imóvel foi selecionado, exibimos apenas o formulário de lançamento
            if linhas_selecionadas:
                idx_selecionado = linhas_selecionadas[0]
                imovel_sel = df.iloc[idx_selecionado]
                id_imovel = imovel_sel["ID"]
                status_atual = imovel_sel["Status Ciclo"]

                # Limpamos a área visual abaixo recriando um layout focado apenas no lançamento
                st.empty()

                # Bloqueio estrito se o imóvel já foi Normal ou Recuperado no ciclo
                if status_atual in ["Normal", "Recuperado"]:
                    st.warning(f"🔒 **Imóvel ID #{id_imovel} já possui lançamento de ciclo concluído ({status_atual}) e está bloqueado para novas edições.**")
                else:
                    st.markdown("---")
                    
                    # Botão para voltar à lista caso queira cancelar
                    if st.button("⬅ Voltar para a Lista de Imóveis"):
                        st.rerun()

                    # --- CARTÃO DE DESTAQUE DO IMÓVEL SELECIONADO ---
                    st.markdown(
                        f"""
                        <div style="background-color: #f8f9fa; border-left: 5px solid #d9534f; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                            <h4 style="margin-top: 0px; color: #333;">📝 Lançamento Diário para o Imóvel ID #{id_imovel}</h4>
                            <p style="margin-bottom: 5px;"><b>Bairro:</b> {imovel_sel['Bairro']} | <b>Quarteirão:</b> {imovel_sel['Quarteirão']} | <b>Tipo:</b> {imovel_sel['Tipo']}</p>
                            <p style="margin-bottom: 0px;"><b>Endereço:</b> {imovel_sel['Rua']}, Nº {imovel_sel['Nº Imóvel']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if status_atual == "Fechado":
                        opcoes_situacao = ["Fechado", "Recuperado"]
                        st.info("🔄 **Imóvel marcado como Fechado neste ciclo.** Selecione **Recuperado** para efetuar a vistoria realizada.")
                    else:
                        opcoes_situacao = ["Normal", "Fechado"]

                    situacao = st.radio(
                        "Situação do Imóvel:",
                        opcoes_situacao,
                        horizontal=True,
                        key=f"situacao_{id_imovel}",
                    )

                    depositos_eliminados = 0
                    fez_tratamento = "Não"
                    depositos_tratados = 0
                    gramas_medicamento = 0.0

                    if situacao in ["Normal", "Recuperado"]:
                        col_dep1, col_dep2 = st.columns(2)

                        with col_dep1:
                            val_elim = st.number_input(
                                "Depósitos Eliminados",
                                min_value=0,
                                step=1,
                                value=None,
                                placeholder="Digite a quantidade...",
                                key=f"dep_elim_{id_imovel}",
                            )
                            depositos_eliminados = int(val_elim) if val_elim is not None else 0

                        with col_dep2:
                            fez_tratamento = st.selectbox(
                                "Foi feito tratamento?",
                                ["Não", "Sim"],
                                key=f"fez_trat_{id_imovel}",
                            )

                        if fez_tratamento == "Sim":
                            col_trat1, col_trat2 = st.columns(2)
                            with col_trat1:
                                max_v = max(depositos_eliminados, 0)
                                val_trat = st.number_input(
                                    f"Depósitos Tratados (Máx: {depositos_eliminados})",
                                    min_value=0,
                                    max_value=max_v if max_v > 0 else None,
                                    step=1,
                                    value=None,
                                    placeholder="Digite...",
                                    key=f"dep_trat_{id_imovel}",
                                )
                                depositos_tratados = int(val_trat) if val_trat is not None else 0

                            with col_trat2:
                                val_gramas = st.number_input(
                                    "Quantidade de Medicamento Utilizado (g)",
                                    min_value=0.0,
                                    step=0.5,
                                    format="%.2f",
                                    value=None,
                                    placeholder="Ex: 5.5",
                                    key=f"gramas_{id_imovel}",
                                )
                                gramas_medicamento = float(val_gramas) if val_gramas is not None else 0.0

                    st.markdown(" ")
                    
                    # Botão posicionado do lado esquerdo da tela
                    col_botao, col_espaco = st.columns([1, 2])
                    with col_botao:
                        if st.button(
                            "💾 Salvar Lançamento",
                            type="primary",
                            key=f"btn_salvar_{id_imovel}",
                        ):
                            if (
                                situacao in ["Normal", "Recuperado"]
                                and fez_tratamento == "Sim"
                                and depositos_tratados > depositos_eliminados
                            ):
                                st.error("❌ Erro: Depósitos tratados não podem ser maiores que os eliminados!")
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
                                    usuario_logado,
                                )

                                bairro.salvar_registro_diario(dados_registro)
                                st.success(f"Lançamento ({situacao}) salvo e sincronizado no Dropbox com sucesso!")
                                st.rerun()

            else:
                # Caso nenhum imóvel esteja selecionado, exibe o cabeçalho e a lista normalmente
                st.subheader(f"Lista de Registros ({len(df)})")

                col_leg1, col_leg2, col_leg3 = st.columns(3)
                col_leg1.markdown("🟩 **Verde**: Lançado como *Normal* ou *Recuperado* (Bloqueado)")
                col_leg2.markdown("🟥 **Vermelho**: Lançado como *Fechado* (Requer Recuperação)")
                col_leg3.markdown("⬜ **Branco**: Sem lançamento (Disponível)")

                st.info("💡 Clique em uma linha da tabela para realizar o lançamento (Imóveis com status **Normal** ou **Recuperado** já concluídos não podem ser alterados).")

        else:
            st.info("Nenhum imóvel com status FECHADO encontrado.")
    else:
        st.info("Nenhum imóvel corresponde aos filtros selecionados.")
