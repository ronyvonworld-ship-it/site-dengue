# TAB 3: Resumo & Conclusão de Quarteirão
        with aba_resumo_admin:
            st.subheader("📊 Resumo de Lançamentos e Status por Período")

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                data_inicio = st.date_input(
                    "Data Inicial",
                    value=datetime.date.today(),
                    key="admin_d_inicio",
                )
            with col_d2:
                data_fim = st.date_input(
                    "Data Final",
                    value=datetime.date.today(),
                    key="admin_d_fim",
                )

            if data_inicio > data_fim:
                st.error("⚠️ A data inicial não pode ser posterior à data final.")
            else:
                resumo = bairro.obter_resumo_por_datas(data_inicio, data_fim)

                st.markdown("##### 📍 Imóveis Lançados no Período")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Lançados", resumo["total_lancados"])
                m2.metric("Normal 🟩", resumo["total_normal"])
                m3.metric("Fechado 🟥", resumo["total_fechado"])
                m4.metric("Recuperado 🟩", resumo["total_recuperado"])

                st.markdown("##### 🧪 Depósitos e Medicamentos")
                m5, m6, m7 = st.columns(3)
                m5.metric("Depósitos Eliminados", resumo["total_eliminados"])
                m6.metric("Depósitos Tratados", resumo["total_tratados"])
                m7.metric("Medicamento (g)", f"{resumo['total_gramas']:.2f} g")

            st.markdown("---")
            st.subheader("🏁 Situação de Todos os Quarteirões do Bairro")

            bairro_chk = st.text_input("Filtrar Bairro para verificar Quarteirões", key="chk_bairro_admin")

            if st.button("🔍 Pesquisar Quarteirões do Bairro", use_container_width=True):
                if not bairro_chk:
                    st.warning("Preencha o nome do Bairro para pesquisar.")
                else:
                    resultado_q = bairro.listar_status_quarteiroes_por_bairro(bairro_chk)
                    if not resultado_q:
                        st.info(f"Nenhum quarteirão/imóvel encontrado para o Bairro '{bairro_chk}'.")
                    else:
                        df_q = pd.DataFrame(resultado_q)
                        
                        # Calcula totais gerais do Bairro
                        total_q = len(df_q)
                        q_concluidos = len(df_q[df_q["Status"] == "✅ CONCLUÍDO"])
                        
                        st.markdown(f"**Resultado para o Bairro:** `{bairro_chk}`")
                        col_m1, col_m2 = st.columns(2)
                        col_m1.metric("Total de Quarteirões", total_q)
                        col_m2.metric("Quarteirões Concluídos", f"{q_concluidos} / {total_q}")
                        
                        st.dataframe(df_q, use_container_width=True, hide_index=True)
