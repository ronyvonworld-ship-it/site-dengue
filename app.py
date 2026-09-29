import streamlit as st
import sqlite3
import hashlib
import os

# Importa as funções de banco de dados do módulo bairro.py
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

        # Validação via PBKDF2
        if salt_banco and len(salt_banco) > 0:
            if verificar_senha_pbkdf2(senha_input.strip(), senha_hash_banco, salt_banco):
                return True, "Login realizado com sucesso!", tipo_usuario

        # Fallback SHA-256 simples
        hash_sha256 = hashlib.sha256(senha_input.strip().encode("utf-8")).hexdigest()
        if hash_sha256.lower() == senha_hash_banco.lower():
            return True, "Login realizado com sucesso!", tipo_usuario

        return False, "Usuário ou senha incorretos.", ""

    except Exception as e:
        return False, f"Erro ao acessar banco: {e}", ""


# --- Configuração da Interface Streamlit ---
st.set_page_config(page_title="Sistema de Mapeamento", page_icon="🏢", layout="wide")

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
    # --- Menu Lateral ---
    st.sidebar.markdown(f"**Usuário:** `{st.session_state['usuario_atual']}`")
    st.sidebar.markdown(f"**Perfil:** `{st.session_state['tipo_usuario']}`")

    if st.sidebar.button("Sair / Logout", use_container_width=True):
        st.session_state["logado"] = False
        st.session_state["usuario_atual"] = ""
        st.session_state["tipo_usuario"] = ""
        st.rerun()

    # --- Área Logada / Mapeamento ---
    st.title("📍 Mapeamento Territorial de Quarteirões")

    if st.session_state["tipo_usuario"] == "Administrador":
        st.success("Acesso concedido: Módulo Administrador ativo.")

        aba_cadastro, aba_registros = st.tabs(["➕ Cadastrar Quarteirão/Imóvel", "📋 Ver Registros (bairro.db)"])

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

                btn_salvar = st.form_submit_button("Salvar no Banco", use_container_width=True)

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
                        st.success("Registro adicionado com sucesso em `bairro.db`!")

        with aba_registros:
            st.subheader("Registros Cadastrados")
            registros = bairro.listar_quarteiroes()
            if registros:
                st.dataframe(
                    registros,
                    column_config={
                        "0": "ID",
                        "1": "Bairro",
                        "2": "Quarteirão",
                        "3": "Rua",
                        "4": "Lado",
                        "5": "Nº Imóvel",
                        "6": "Tipo"
                    },
                    use_container_width=True
                )
            else:
                st.info("Nenhum registro encontrado no banco `bairro.db`.")

    else:
        st.warning("Seu perfil de usuário não tem permissão para cadastrar ou visualizar quarteirões.")
        st.info("Entre em contato com um Administrador para alterar seu nível de acesso.")
