import streamlit as st
import sqlite3
import hashlib
import os

ARQUIVO_BANCO = "usuarios.db"


def gerar_hash(senha: str) -> str:
    """Gera o hash SHA-256 para a senha digitada."""
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def buscar_hash_usuario(usuario: str) -> str | None:
    """
    Busca o hash da senha do usuário no arquivo usuarios.db.
    Funciona tanto se o arquivo for um banco de dados SQLite
    quanto se for um arquivo de texto simples (formato usuario:hash).
    """
    if not os.path.exists(ARQUIVO_BANCO):
        st.error(f"Arquivo '{ARQUIVO_BANCO}' não encontrado!")
        return None

    # Tativa 1: Tratar como banco de dados SQLite
    try:
        conn = sqlite3.connect(ARQUIVO_BANCO)
        cursor = conn.cursor()

        # Busca a hash considerando tabelas comuns (usuarios ou users)
        cursor.execute("SELECT senha_hash FROM usuarios WHERE usuario = ?", (usuario,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            return resultado[0]

    except sqlite3.DatabaseError:
        # Tativa 2: Tratar como arquivo de texto simples em caso de falha do SQLite
        try:
            with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
                for linha in f:
                    linha = linha.strip()
                    if not linha or ":" not in linha:
                        continue

                    partes = linha.split(":", 1)
                    user_arq = partes[0].strip()
                    hash_arq = partes[1].strip()

                    if user_arq == usuario:
                        return hash_arq
        except Exception as e:
            st.error(f"Erro ao ler arquivo texto: {e}")

    return None


def validar_login(usuario_input: str, senha_input: str) -> bool:
    """Valida o usuário comparando o hash digitado com o armazenado no arquivo."""
    usuario_input = usuario_input.strip()
    hash_armazenada = buscar_hash_usuario(usuario_input)

    if hash_armazenada:
        hash_digitada = gerar_hash(senha_input)
        return hash_digitada.lower() == hash_armazenada.lower()

    return False


# --- Configuração do Layout Streamlit ---
st.set_page_config(page_title="Sistema de Login", page_icon="🔒", layout="centered")

# Estado da Sessão
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "usuario_atual" not in st.session_state:
    st.session_state["usuario_atual"] = ""

# --- Tela de Login / Dashboard ---
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
            elif validar_login(usuario_input, senha_input):
                st.session_state["logado"] = True
                st.session_state["usuario_atual"] = usuario_input
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

else:
    # --- Painel Restrito ---
    st.sidebar.markdown(f"**Usuário conectado:** `{st.session_state['usuario_atual']}`")

    if st.sidebar.button("Sair / Logout", use_container_width=True):
        st.session_state["logado"] = False
        st.session_state["usuario_atual"] = ""
        st.rerun()

    st.title("🚀 Painel Principal")
    st.success(f"Bem-vindo(a), **{st.session_state['usuario_atual']}**!")
    st.write("Você está autenticado e tem acesso aos dados protegidos.")