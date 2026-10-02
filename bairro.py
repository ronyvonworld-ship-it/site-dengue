import sqlite3
import dropbox
import streamlit as st

ARQUIVO_DIARIO_DB = "diario.db"
CAMINHO_DROPBOX_DIARIO = "/diario.db"


def inicializar_diario_db():
    """Cria a tabela no diario.db se ainda não existir."""
    conn = sqlite3.connect(ARQUIVO_DIARIO_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS diario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imovel_id INTEGER,
            bairro TEXT,
            quarteirao TEXT,
            rua TEXT,
            num_imovel TEXT,
            tipo_imovel TEXT,
            situacao TEXT,
            depositos_eliminados INTEGER DEFAULT 0,
            fez_tratamento TEXT,
            depositos_tratados INTEGER DEFAULT 0,
            gramas_medicamento REAL DEFAULT 0.0,
            data_registro DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()


def salvar_registro_diario(dados_registro):
    """Insere o registro no diario.db e envia o arquivo atualizado para o Dropbox."""
    inicializar_diario_db()

    conn = sqlite3.connect(ARQUIVO_DIARIO_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO diario (
            imovel_id, bairro, quarteirao, rua, num_imovel, tipo_imovel,
            situacao, depositos_eliminados, fez_tratamento, depositos_tratados, gramas_medicamento
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        dados_registro,
    )
    conn.commit()
    conn.close()

    # Envia o banco atualizado para o Dropbox
    enviar_diario_dropbox()


def enviar_diario_dropbox():
    """Envia o arquivo diario.db atualizado para o Dropbox."""
    app_key = st.secrets.get("DROPBOX_APP_KEY")
    app_secret = st.secrets.get("DROPBOX_APP_SECRET")
    refresh_token = st.secrets.get("DROPBOX_REFRESH_TOKEN")

    if not all([app_key, app_secret, refresh_token]):
        st.error("Credenciais do Dropbox não configuradas!")
        return

    try:
        dbx = dropbox.Dropbox(
            app_key=app_key,
            app_secret=app_secret,
            oauth2_refresh_token=refresh_token,
        )
        with open(ARQUIVO_DIARIO_DB, "rb") as f:
            # WriteMode.overwrite substitui a versão anterior no Dropbox
            dbx.files_upload(
                f.read(),
                CAMINHO_DROPBOX_DIARIO,
                mode=dropbox.files.WriteMode.overwrite,
            )
        st.toast("✅ Dados salvos e sincronizados com o Dropbox!", icon="☁️")
    except Exception as e:
        st.error(f"Erro ao sincronizar com o Dropbox: {e}")
