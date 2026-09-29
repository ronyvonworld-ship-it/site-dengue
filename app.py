import streamlit as st
import sqlite3
import hashlib
import os

ARQUIVO_BANCO = "usuarios.db"


def verificar_senha_pbkdf2(senha_digitada: str, senha_hash_hex: str, salt_hex: str) -> bool:
    """Reconstrói o hash PBKDF2 da senha digitada usando o salt armazenado no banco."""
    salt = bytes.fromhex(salt_hex)
    hash_calculado = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=senha_digitada.encode("utf-8"),
        salt=salt,
        iterations=100000
    ).hex()
    return hash_calculado == senha_hash_hex


def validar_login(usuario_input: str, senha_input: str):
    """Consulta o banco usuarios.db e valida o usuário e a senha."""
    if not os.path.exists(ARQUIVO_BANCO):
        return False, f"O arquivo '{ARQUIVO_BANCO}' não foi encontrado no servidor."

    try:
        conn = sqlite3.connect(ARQUIVO_BANCO)
        cursor = conn.cursor()

        # Busca as credenciais cadastradas
        cursor.execute(
            "SELECT senha_hash, salt, tipo FROM usuarios WHERE usuario = ?", 
            (usuario_input.strip(),)
        )
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            return False, "Usuário ou senha incorretos."

        senha_hash_banco, salt_banco, tipo_usuario = resultado

        # 1. Tenta validar via PBKDF2 (se o banco foi criado via app Tkinter)
        if salt_banco and len(salt_banco) > 0:
            if verificar_senha_pbkdf2(senha_input.strip(), senha_hash_banco, salt_banco):
                return True, tipo_usuario

        # 2. Fallback: Tenta validar via SHA-256 simples (caso o banco tenha senhas antigas)
        hash_sha256 = hashlib.sha256(senha_input.strip().encode("utf-8")).hexdigest()
        if hash_sha256.lower() == senha_hash_banco.lower():
            return True, tipo_usuario

        return False, "Usuário ou senha incorretos."

    except sqlite3.OperationalError as e:
        return False, f"Erro na tabela do banco de dados: {e}"
    except Exception as e:
        return False, f"Erro inesperado: {e}"


# --- Interface Streamlit ---
st.set_page_config(page_title="Sistema de Login", page_icon="🔒", layout="centered")

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
                sucesso, resultado = validar_login(usuario_input, senha_input)
                if sucesso:
                    st.session_state["logado"] = True
                    st.session_state["usuario_atual"] = usuario_input.strip()
                    st.session_state["tipo_usuario"] = resultado
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error(resultado)

else:
    # --- Área Logada ---
    st.sidebar.markdown(f"**Usuário:** `{st.session_state['usuario_atual']}`")
    st.sidebar.markdown(f"**Perfil:** `{st.session_state['tipo_usuario']}`")

    if st.sidebar.button("Sair / Logout", use_container_width=True):
        st.session_state["logado"] = False
        st.session_state["usuario_atual"] = ""
        st.session_state["tipo_usuario"] = ""
        st.rerun()

    st.title("🚀 Painel Principal")
    st.success(f"Bem-vindo(a), **{st.session_state['usuario_atual']}**!")
    st.info(f"Nível de acesso do seu perfil: **{st.session_state['tipo_usuario']}**")
