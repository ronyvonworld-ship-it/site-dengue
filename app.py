import streamlit as st
import sqlite3
import hashlib
import os
import pandas as pd

import bairro

ARQUIVO_USUARIOS = "usuarios.db"


def verificar_senha_pbkdf2(senha_digitada: str, senha_hash_hex: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    hash_calculado = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=senha_digitada.encode("utf-8"),
        salt=salt,
        iterations=100000
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
            (usuario_input.strip(),)
        )
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            return False, "Usuário ou senha incorretos.", ""

        senha_hash_banco, salt_banco, tipo_usuario = resultado

        if salt_banco and len(salt_banco) > 0:
            if verificar_senha_pbkdf2(senha_input.strip(), senha_hash_banco, salt_banco):
                return True, "Login realizado com sucesso!", tipo_usuario

        hash_sha256 = hashlib.sha256(senha_input.strip().encode("utf-8")).hexdigest()
        if hash_sha256.lower() == senha_hash_banco.lower():
            return True, "Login realizado com sucesso!", tipo_usuario

        return False, "Usuário ou senha incorretos.", ""

    except Exception as e:
        return False, f"Erro ao acessar banco: {e}", ""


# Configuração da página
st.set_page_config(page_title="Sistema de Mapeamento", page_icon="📍", layout="wide")

if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "usuario_atual" not in st.session_state:
    st.session_state["usuario_atual"] = ""
if "tipo_usuario" not in st.session_state:
    st.session_state["tipo_usuario"] = ""


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
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

else:
    # --- Sidebar ---
    st.sidebar.markdown(f"**Usuário:** `{st.session_state['usuario_atual']}`")
    st.sidebar.markdown(f"**Perfil:** `{st.session_state['tipo_usuario']}`")

    if st.sidebar.button("Sair / Logout", use_container_width=True):
        st.session_state["logado"] = False
        st.session_state["usuario_atual"] = ""
        st.session_state["tipo_usuario"] = ""
        st.rerun()

    # --- Conteúdo Principal ---
    st.title("📍 Mapeamento Territorial de Quarteirões")

    if st.session_state["tipo_usuario"] == "Administrador":

        aba_cadastro, aba_registros = st.tabs(["➕ Cadastrar Imóvel", "🔍 Consultar, Editar e Excluir"])

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
                        ["Residência", "Comércio", "Terreno Baldio", "Outro"]
                    )

                btn_salvar = st.form_submit_button("Salvar Registro", use_container_width=True)

                if btn_salvar:
                    if not all([bairro_nome, quarteirao_num, rua_nome, lado_num, imovel_num]):
                        st.warning("Preencha todos os campos do formulário.")
                    else:
                        bairro.salvar_quarteirao(
                            bairro_nome.strip(),
                            quarteirao_num.strip(),
                            rua_nome.strip(),
                            lado_num.strip(),
                            imovel_num.strip(),
                            tipo_imovel
                        )
                        st.success("Registro adicionado com sucesso!")

        # TAB 2: Consultar / Editar / Excluir
        with aba_registros:
            st.subheader("Filtros de Pesquisa")

            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                f_bairro = st.text_input("Filtrar por Bairro", key="f_bairro")
                f_quarteirao = st.text_input("Filtrar por Nº Quarteirão", key="f_quarteirao")
            with col_f2:
                f_rua = st.text_input("Filtrar por Rua", key="f_rua")
                f_imovel = st.text_input("Filtrar por Nº Imóvel", key="f_imovel")
            with col_f3:
                f_tipo = st.selectbox("Filtrar por Tipo", ["Todos", "Residência", "Comércio", "Terreno Baldio", "Outro"], key="f_tipo")

            # Busca filtrada dinâmica em tempo real
            dados = bairro.listar_quarteiroes(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)

            st.markdown("---")
            st.subheader(f"Resultados Encontrados ({len(dados)})")

            if dados:
                df = pd.DataFrame(dados, columns=["ID", "Bairro", "Quarteirão", "Rua", "Lado", "Nº Imóvel", "Tipo"])
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.subheader("⚙️ Gerenciar Registro Selecionado")

                opcoes_imoveis = {
                    f"ID {row[0]} | Bairro: {row[1]} | Quart.: {row[2]} | Rua: {row[3]} | Imóvel: {row[5]}": row
                    for row in dados
                }

                imovel_selecionado_str = st.selectbox(
                    "Selecione um imóvel filtrado para alterar ou excluir:",
                    options=list(opcoes_imoveis.keys())
                )

                reg = opcoes_imoveis[imovel_selecionado_str]
                id_sel = reg[0]

                st.markdown(f"**Modificando Registro ID `{id_sel}`**")
                
                with st.form("form_edicao"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        ebairro = st.text_input("Bairro", value=str(reg[1]))
                        equarteirao = st.text_input("Nº Quarteirão", value=str(reg[2]))
                        erua = st.text_input("Rua", value=str(reg[3]))
                    with col_e2:
                        elado = st.text_input("Nº Lado", value=str(reg[4]))
                        eimovel = st.text_input("Nº Imóvel", value=str(reg[5]))
                        
                        tipos_validos = ["Residência", "Comércio", "Terreno Baldio", "Outro"]
                        idx_tipo = tipos_validos.index(reg[6]) if reg[6] in tipos_validos else 0
                        etipo = st.selectbox("Tipo de Imóvel", tipos_validos, index=idx_tipo)

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        btn_atualizar = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                    with col_btn2:
                        btn_excluir = st.form_submit_button("🗑️ Excluir Imóvel", use_container_width=True)

                    if btn_atualizar:
                        bairro.atualizar_quarteirao(id_sel, ebairro, equarteirao, erua, elado, eimovel, etipo)
                        st.success(f"Registro ID {id_sel} atualizado com sucesso!")
                        st.rerun()

                    if btn_excluir:
                        bairro.excluir_quarteirao(id_sel)
                        st.warning(f"Registro ID {id_sel} excluído do banco de dados!")
                        st.rerun()

            else:
                st.info("Nenhum imóvel corresponde aos filtros selecionados.")

    else:
        st.warning("Seu perfil de usuário não possui permissão de acesso.")
