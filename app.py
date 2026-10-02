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
    page_title="Sistema de Mapeamento", page_icon="📍", layout="wide"
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
    st.title("🔒 Acesso ao Sistema")
    st.markdown("---")

    with st.form("form_login"):
        st.subheader("Autenticação")
        usuario_input = st.text_input("Usuário")
        senha_input = st.text_input("Senha", type="password")
        btn_entrar = st.form_submit_button("Entrar", use_container_width=True)

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
    # Executa a restauração do Dropbox uma única vez logo após o login
    if st.session_state.get("precisa_carregar_db", False):
        with st.spinner("Sincronizando banco de dados com o Dropbox..."):
            try:
                bairro.carregar_db_do_dropbox(forcar=True)
            except Exception as e:
                st.error(f"Erro na sincronização inicial do Dropbox: {e}")
        st.session_state["precisa_carregar_db"] = False

    # --- Sidebar ---
    st.sidebar.markdown(f"**Usuário:** `{st.session_state['usuario_atual']}`")
    st.sidebar.markdown(f"**Perfil:** `{st.session_state['tipo_usuario']}`")

    if st.sidebar.button("🔄 Sincronizar com Dropbox", use_container_width=True):
        with st.spinner("Atualizando arquivo..."):
            if os.path.exists("bairro.db"):
                os.remove("bairro.db")
            bairro.carregar_db_do_dropbox(forcar=True)
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

            dados = bairro.listar_quarteiroes(
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

                st.markdown("---")
                st.subheader("⚙️ Gerenciar Registro Selecionado")

                opcoes_imoveis = {
                    f"ID {row[0]} | Bairro: {row[1]} | Quart.: {row[2]} | Rua: {row[3]} | Imóvel: {row[5]}": row
                    for row in dados
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
            st.subheader("🏁 Verificação de Conclusão de Quarteirão")

            col_q1, col_q2 = st.columns(2)
            with col_q1:
                bairro_chk = st.text_input("Bairro", key="chk_bairro_admin")
            with col_q2:
                quarteirao_chk = st.text_input(
                    "Nº do Quarteirão", key="chk_quart_admin"
                )

            if st.button(
                "🔍 Verificar Status do Quarteirão", use_container_width=True
            ):
                if not bairro_chk or not quarteirao_chk:
                    st.warning(
                        "Preencha o nome do Bairro e o Nº do Quarteirão para verificar."
                    )
                else:
                    concluido, lancados, total = (
                        bairro.verificar_status_quarteirao(
                            bairro_chk, quarteirao_chk
                        )
                    )
                    if total == 0:
                        st.info(
                            f"Nenhum imóvel cadastrado no Bairro '{bairro_chk}', Quarteirão '{quarteirao_chk}'."
                        )
                    elif concluido:
                        st.success(
                            f"✅ **Quarteirão CONCLUÍDO!** Todos os **{total}** imóveis foram visitados e lançados no ciclo atual."
                        )
                    else:
                        pendentes = total - lancados
                        st.error(
                            f"❌ **Quarteirão INCOMPLETO!** Lançados: **{lancados}** de **{total}** imóveis ({pendentes} pendentes)."
                        )

        # TAB 4: Backup
        with aba_backup:
            bairro.gerenciar_backup_db()

    else:
        # Usuário Operador / Agente de Campo
        st.session_state["operador"] = st.session_state["usuario_atual"]
        lancar_imovel.renderizar_tela_consulta()
