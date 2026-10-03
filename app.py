import datetime
import hashlib
import os
import sqlite3
import pandas as pd
import streamlit as st

import bairro
import lancar_imovel

ARQUIVO_USUARIOS = "usuarios.db"


def verificar_senha_pbkdf2(
    senha_digitada: str, senha_hash_hex: str, salt_hex: str
) -> bool:
    salt = bytes.fromhex(salt_hex)
    hash_calculado = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=senha_digitada.encode("utf-8"),
        salt=salt,
        iterations=100000,
    ).hex()
    return hash_calculado == senha_hash_hex


def validar_login(usuario_input: str, senha_input: str):
    if not os.path.exists(ARQUIVO_USUARIOS):
        return False, f"O arquivo '{ARQUIVO_USUARIOS}' não foi encontrado.", ""

    try:
        conn = sqlite3.connect(ARQUIVO_USUARIOS)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT senha_hash, salt, tipo FROM usuarios WHERE usuario = ?",
            (usuario_input.strip(),),
        )
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            return False, "Usuário ou senha incorretos.", ""

        senha_hash_banco, salt_banco, tipo_usuario = resultado

        if salt_banco and len(salt_banco) > 0:
            if verificar_senha_pbkdf2(
                senha_input.strip(), senha_hash_banco, salt_banco
            ):
                return True, "Login realizado com sucesso!", tipo_usuario

        hash_sha256 = hashlib.sha256(
            senha_input.strip().encode("utf-8")
        ).hexdigest()
        if hash_sha256.lower() == senha_hash_banco.lower():
            return True, "Login realizado com sucesso!", tipo_usuario

        return False, "Usuário ou senha incorretos.", ""

    except Exception as e:
        return False, f"Erro ao acessar banco: {e}", ""


# Configuração da página
st.set_page_config(
    page_title="Combate à Dengue - Acari", page_icon="🦟", layout="wide"
)

# --- Gerenciamento de Estado ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "usuario_atual" not in st.session_state:
    st.session_state["usuario_atual"] = ""
if "tipo_usuario" not in st.session_state:
    st.session_state["tipo_usuario"] = ""
if "precisa_carregar_db" not in st.session_state:
    st.session_state["precisa_carregar_db"] = False


# --- TELA DE LOGIN ---
if not st.session_state["logado"]:
    # Layout centralizado e estilizado para a tela de login
    col_vazia1, col_centro, col_vazia2 = st.columns([1, 1.2, 1])

    with col_centro:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Cabeçalho customizado e elegante
        st.markdown(
            """
            <div style="text-align: center; padding: 10px;">
                <h1 style="color: #d9534f; margin-bottom: 0px; font-size: 2.3rem;">🦟 COMBATE À DENGUE</h1>
                <h3 style="color: #4f4f4f; margin-top: 5px; font-weight: 500;">Boletim Diário da Cidade de Acari</h3>
                <h4 style="color: #6c757d; font-weight: 400; font-size: 1.1rem; margin-top: -5px;">Prefeitura Municipal de Acari<br><b>Secretaria de Saúde</b></h4>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        st.markdown("---")

        with st.form("form_login"):
            st.markdown("#### 🔐 Acesso ao Sistema")
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            btn_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)

            if btn_entrar:
                if not usuario_input or not senha_input:
                    st.warning("Por favor, preencha todos os campos.")
                else:
                    sucesso, msg, tipo = validar_login(usuario_input, senha_input)
                    if sucesso:
                        st.session_state["logado"] = True
                        st.session_state["usuario_atual"] = usuario_input.strip()
                        st.session_state["tipo_usuario"] = tipo
                        st.session_state["precisa_carregar_db"] = True
                        st.rerun()
                    else:
                        st.error(msg)

# --- ÁREA LOGADA ---
else:
    if st.session_state.get("precisa_carregar_db", False):
        with st.spinner("Sincronizando bancos de dados com o Dropbox..."):
            try:
                # Sincroniza o banco de bairros
                bairro.carregar_db_do_dropbox(forcar=True)
                
                # Sincroniza automaticamente o diario.db do Dropbox
                db_cliente = bairro.obter_cliente_dropbox()
                if db_cliente:
                    try:
                        _, resposta = db_cliente.files_download("/diario.db")
                        with open("diario.db", "wb") as f:
                            f.write(resposta.content)
                    except Exception:
                        pass # Se não existir no Dropbox ainda, será gerado localmente
                
                # Inicializa as tabelas do diário localmente
                bairro.inicializar_diario_db()

            except Exception as e:
                st.error(f"Erro na sincronização inicial do Dropbox: {e}")
        st.session_state["precisa_carregar_db"] = False

    # --- Sidebar ---
    st.sidebar.markdown(f"**Usuário:** `{st.session_state['usuario_atual']}`")
    st.sidebar.markdown(f"**Perfil:** `{st.session_state['tipo_usuario']}`")

    if st.sidebar.button("🔄 Sincronizar com Dropbox", use_container_width=True):
        with st.spinner("Atualizando arquivos..."):
            if os.path.exists("bairro.db"):
                os.remove("bairro.db")
            if os.path.exists("diario.db"):
                os.remove("diario.db")

            # Sincroniza o banco de bairros
            bairro.carregar_db_do_dropbox(forcar=True)

            # Sincroniza o diario.db da nuvem
            db_cliente = bairro.obter_cliente_dropbox()
            if db_cliente:
                try:
                    _, resposta = db_cliente.files_download("/diario.db")
                    with open("diario.db", "wb") as f:
                        f.write(resposta.content)
                except Exception:
                    pass

            bairro.inicializar_diario_db()
            st.sidebar.success("Sincronização concluída!")
            st.rerun()

    if st.sidebar.button("Sair / Logout", use_container_width=True):
        st.session_state["logado"] = False
        st.session_state["usuario_atual"] = ""
        st.session_state["tipo_usuario"] = ""
        st.session_state["precisa_carregar_db"] = False
        st.rerun()

    # --- Controle de Acesso por Tipo de Usuário ---
    if st.session_state["tipo_usuario"] == "Administrador":
        st.title("📍 Mapeamento Territorial de Quarteirões")

        # --- EXIBIÇÃO DA DATA E CICLO ATUAL (ADMIN) ---
        num_ciclo, ano_ciclo, dt_inicio_ciclo, dt_fim_ciclo = bairro.obter_info_ciclo_atual()
        hoje_formatado = datetime.date.today().strftime("%d/%m/%Y")
        
        st.info(
            f"📅 **Data de Hoje:** `{hoje_formatado}` | "
            f"🔄 **Ciclo Atual:** `{num_ciclo}º Ciclo de {ano_ciclo}` "
            f"(Período: `{dt_inicio_ciclo[:10]}` até `{dt_fim_ciclo[:10]}`)"
        )
        st.markdown("---")

        aba_cadastro, aba_registros, aba_resumo_admin, aba_backup = st.tabs(
            [
                "➕ Cadastrar Imóvel",
                "🔍 Consultar, Editar e Excluir",
                "📊 Resumo & Quarteirões",
                "💾 Backup / Restaurar DB",
            ]
        )

        # TAB 1: Cadastrar
        with aba_cadastro:
            st.subheader("Adicionar Novo Registro no `bairro.db`")
            with st.form("form_quarteirao"):
                col1, col2 = st.columns(2)

                with col1:
                    bairro_nome = st.text_input("Nome do Bairro")
                    quarteirao_num = st.text_input("Número do Quarteirão")
                    rua_nome = st.text_input("Nome da Rua")

                with col2:
                    lado_num = st.text_input("Número do Lado do Quarteirão")
                    imovel_num = st.text_input("Número do Imóvel")
                    tipo_imovel = st.selectbox(
                        "Tipo do Imóvel",
                        [
                            "Residência",
                            "Comércio",
                            "Terreno Baldio",
                            "Outro",
                        ],
                    )

                btn_salvar = st.form_submit_button(
                    "Salvar Registro", use_container_width=True
                )

                if btn_salvar:
                    if not all(
                        [
                            bairro_nome,
                            quarteirao_num,
                            rua_nome,
                            lado_num,
                            imovel_num,
                        ]
                    ):
                        st.warning("Preencha todos os campos do formulário.")
                    else:
                        bairro.salvar_quarteirao(
                            bairro_nome.strip(),
                            quarteirao_num.strip(),
                            rua_nome.strip(),
                            lado_num.strip(),
                            imovel_num.strip(),
                            tipo_imovel,
                        )
                        st.success("Registro adicionado com sucesso!")

        # TAB 2: Consultar / Editar / Excluir
        with aba_registros:
            st.subheader("Filtros de Pesquisa")

            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                f_bairro = st.text_input("Filtrar por Bairro", key="f_bairro")
                f_quarteirao = st.text_input(
                    "Filtrar por Nº Quarteirão", key="f_quarteirao"
                )
            with col_f2:
                f_rua = st.text_input("Filtrar por Rua", key="f_rua")
                f_imovel = st.text_input("Filtrar por Nº Imóvel", key="f_imovel")
            with col_f3:
                f_tipo = st.selectbox(
                    "Filtrar por Tipo",
                    [
                        "Todos",
                        "Residência",
                        "Comércio",
                        "Terreno Baldio",
                        "Outro",
                    ],
                    key="f_tipo",
                )

            dados_detalhados = bairro.listar_quarteiroes_com_status_detalhado(
                f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo
            )
            total_imoveis, detalhe_tipos = bairro.obter_resumo_filtros(
                f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo
            )

            st.markdown("---")
            st.subheader("📊 Resumo dos Filtros Aplicados")
            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

            m_col1.metric("Total de Imóveis", total_imoveis)
            m_col2.metric("Residências", detalhe_tipos.get("Residência", 0))
            m_col3.metric("Comércios", detalhe_tipos.get("Comércio", 0))
            m_col4.metric(
                "Terrenos Baldios", detalhe_tipos.get("Terreno Baldio", 0)
            )
            m_col5.metric("Outros", detalhe_tipos.get("Outro", 0))

            st.markdown("---")
            st.subheader(f"Lista de Registros ({len(dados_detalhados)})")

            if dados_detalhados:
                df = pd.DataFrame(
                    dados_detalhados,
                    columns=[
                        "ID",
                        "Bairro",
                        "Quarteirão",
                        "Rua",
                        "Lado",
                        "Nº Imóvel",
                        "Tipo",
                        "Status Ciclo",
                        "Agente",
                        "Data do Lançamento",
                    ],
                )

                df_estilizado = df.style.apply(
                    bairro.colorir_linha_por_situacao, axis=1
                )
                st.dataframe(df_estilizado, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.subheader("⚙ Gerenciar Registro Selecionado")

                opcoes_imoveis = {
                    f"ID {row[0]} | Bairro: {row[1]} | Quart.: {row[2]} | Rua: {row[3]} | Imóvel: {row[5]}": row
                    for row in dados_detalhados
                }

                imovel_selecionado_str = st.selectbox(
                    "Selecione um imóvel filtrado para alterar ou excluir:",
                    options=list(opcoes_imoveis.keys()),
                )

                reg = opcoes_imoveis[imovel_selecionado_str]
                id_sel = reg[0]

                st.markdown(f"**Modificando Registro ID `{id_sel}`**")

                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    ebairro = st.text_input(
                        "Bairro", value=str(reg[1]), key=f"eb_{id_sel}"
                    )
                    equarteirao = st.text_input(
                        "Nº Quarteirão", value=str(reg[2]), key=f"eq_{id_sel}"
                    )
                    erua = st.text_input(
                        "Rua", value=str(reg[3]), key=f"er_{id_sel}"
                    )
                with col_e2:
                    elado = st.text_input(
                        "Nº Lado", value=str(reg[4]), key=f"el_{id_sel}"
                    )
                    eimovel = st.text_input(
                        "Nº Imóvel", value=str(reg[5]), key=f"ei_{id_sel}"
                    )

                    tipos_validos = [
                        "Residência",
                        "Comércio",
                        "Terreno Baldio",
                        "Outro",
                    ]
                    idx_tipo = (
                        tipos_validos.index(reg[6])
                        if reg[6] in tipos_validos
                        else 0
                    )
                    etipo = st.selectbox(
                        "Tipo de Imóvel",
                        tipos_validos,
                        index=idx_tipo,
                        key=f"et_{id_sel}",
                    )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    bairro.confirmar_e_atualizar(
                        id_sel, ebairro, equarteirao, erua, elado, eimovel, etipo
                    )
                with col_btn2:
                    bairro.confirmar_e_excluir(id_sel)

            else:
                st.info("Nenhum imóvel corresponde aos filtros selecionados.")

        # TAB 3: Resumo & Conclusão de Quarteirão
        with aba_resumo_admin:
            st.subheader("📊 Resumo de Lançamentos por Período e Agente")

            col_d1, col_d2, col_d3 = st.columns(3)
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
            with col_d3:
                lista_agentes = ["Todos (Total Geral)"] + bairro.obter_lista_agentes()
                agente_selecionado = st.selectbox(
                    "Filtrar por Agente / Usuário",
                    options=lista_agentes,
                    key="admin_agente_sel",
                )

            if data_inicio > data_fim:
                st.error("⚠️ A data inicial não pode ser posterior à data final.")
            else:
                resumo = bairro.obter_resumo_por_datas(data_inicio, data_fim, usuario=agente_selecionado)

                # --- CÁLCULO DOS INDICADORES ---
                total_trabalhados = resumo["total_normal"] + resumo["total_recuperado"]
                total_informados = resumo["total_normal"] + resumo["total_fechado"]

                st.markdown(f"##### 📍 Situação dos Imóveis Lançados ({agente_selecionado})")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Lançados", resumo["total_lancados"])
                m2.metric("Normal 🟩", resumo["total_normal"])
                m3.metric("Fechado 🟥", resumo["total_fechado"])
                m4.metric("Recuperado 🟩", resumo["total_recuperado"])

                # --- EXIBIÇÃO DOS INDICADORES ---
                mi1, mi2 = st.columns(2)
                mi1.metric("Imóveis Trabalhados", total_trabalhados)
                mi2.metric("Imóveis Informados", total_informados)

                st.markdown("##### 🏠 Detalhamento por Tipo de Imóvel")
                t1, t2, t3, t4 = st.columns(4)
                t1.metric("Residências", resumo["total_residencia"])
                t2.metric("Comércios", resumo["total_comercio"])
                t3.metric("Terrenos Baldios", resumo["total_terreno"])
                t4.metric("Outros", resumo["total_outro"])

                st.markdown("##### 🧪 Depósitos e Medicamentos")
                m5, m6, m7 = st.columns(3)
                m5.metric("Depósitos Eliminados", resumo["total_eliminados"])
                m6.metric("Depósitos Tratados", resumo["total_tratados"])
                m7.metric("Medicamento (g)", f"{resumo['total_gramas']:.2f} g")

            st.markdown("---")
            st.subheader("🏁 Situação de Todos os Quarteirões do Bairro")

            bairro_chk = st.text_input(
                "Filtrar Bairro para verificar Quarteirões", key="chk_bairro_admin"
            )

            if st.button("🔍 Pesquisar Quarteirões do Bairro", use_container_width=True):
                if not bairro_chk:
                    st.warning("Preencha o nome do Bairro para pesquisar.")
                else:
                    resultado_q = bairro.listar_status_quarteiroes_por_bairro(bairro_chk)
                    if not resultado_q:
                        st.info(f"Nenhum quarteirão/imóvel encontrado para o Bairro '{bairro_chk}'.")
                    else:
                        df_q = pd.DataFrame(resultado_q)
                        
                        total_q = len(df_q)
                        q_concluidos = len(df_q[df_q["Status"] == "✅ CONCLUÍDO"])
                        
                        st.markdown(f"**Resultado para o Bairro:** `{bairro_chk}`")
                        col_m1, col_m2 = st.columns(2)
                        col_m1.metric("Total de Quarteirões", total_q)
                        col_m2.metric("Quarteirões Concluídos", f"{q_concluidos} / {total_q}")
                        
                        st.dataframe(df_q, use_container_width=True, hide_index=True)

        # TAB 4: Backup
        with aba_backup:
            bairro.gerenciar_backup_db()

    else:
        # Usuário Operador / Agente de Campo
        st.session_state["operador"] = st.session_state["usuario_atual"]
        lancar_imovel.renderizar_tela_consulta()
