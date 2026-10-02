import datetime
import os
import re
import sqlite3
import dropbox
from dropbox.exceptions import ApiError
import pandas as pd
import streamlit as st

# --- CONFIGURAÇÕES DE BANCO DE DADOS E DROPBOX ---
ARQUIVO_DB_BAIRRO = "bairro.db"
CAMINHO_DROPBOX_BAIRRO = "/bairro.db"

ARQUIVO_DIARIO_DB = "diario.db"
CAMINHO_DROPBOX_DIARIO = "/diario.db"

DROPBOX_APP_KEY = st.secrets.get("DROPBOX_APP_KEY", "q0viamdueua22be")
DROPBOX_APP_SECRET = st.secrets.get("DROPBOX_APP_SECRET", "mz2eaymu9r0jrop")
DROPBOX_REFRESH_TOKEN = st.secrets.get(
    "DROPBOX_REFRESH_TOKEN",
    "VHxefblYYMcAAAAAAAAAAXo_fNemEsw_A-sP0lEh3C2YB2kphW9rTfdB6d_sTe5B",
)


# --- CONEXÃO DROPBOX ---


def obter_cliente_dropbox():
    try:
        dbx = dropbox.Dropbox(
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
        )
        return dbx
    except Exception as e:
        st.error(f"❌ Falha ao conectar à API do Dropbox: {e}")
        return None


def carregar_db_do_dropbox(forcar=False):
    db_cliente = obter_cliente_dropbox()
    if not db_cliente:
        return

    if forcar or not os.path.exists(ARQUIVO_DB_BAIRRO):
        try:
            _, resposta = db_cliente.files_download(CAMINHO_DROPBOX_BAIRRO)
            with open(ARQUIVO_DB_BAIRRO, "wb") as f:
                f.write(resposta.content)
            st.toast("📥 Banco de dados restaurado do Dropbox!", icon="🔄")
        except ApiError:
            st.warning(
                "⚠️ Arquivo 'bairro.db' não encontrado na nuvem. Criando novo local."
            )
        except Exception as e:
            st.error(f"❌ Erro ao restaurar banco do Dropbox: {e}")


def sincronizar_banco():
    carregar_db_do_dropbox()


def enviar_db_para_dropbox():
    db_cliente = obter_cliente_dropbox()
    if not db_cliente:
        return False

    if os.path.exists(ARQUIVO_DB_BAIRRO):
        try:
            with open(ARQUIVO_DB_BAIRRO, "rb") as f:
                db_cliente.files_upload(
                    f.read(),
                    CAMINHO_DROPBOX_BAIRRO,
                    mode=dropbox.files.WriteMode.overwrite,
                )
            st.toast("☁️ Alterações salvas no Dropbox!", icon="✅")
            return True
        except Exception as e:
            st.error(f"❌ Erro ao enviar banco para o Dropbox: {e}")
            return False
    return False


# --- GESTÃO DO DIARIO.DB ---


def inicializar_diario_db():
    conn = sqlite3.connect(ARQUIVO_DIARIO_DB)
    cursor = conn.cursor()
    cursor.execute("""
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
    """)
    conn.commit()
    conn.close()


def enviar_diario_dropbox():
    db_cliente = obter_cliente_dropbox()
    if not db_cliente:
        return False

    if os.path.exists(ARQUIVO_DIARIO_DB):
        try:
            with open(ARQUIVO_DIARIO_DB, "rb") as f:
                db_cliente.files_upload(
                    f.read(),
                    CAMINHO_DROPBOX_DIARIO,
                    mode=dropbox.files.WriteMode.overwrite,
                )
            st.toast("☁️ Diário sincronizado com o Dropbox!", icon="✅")
            return True
        except Exception as e:
            st.error(f"❌ Erro ao enviar diario.db para o Dropbox: {e}")
            return False
    return False


def salvar_registro_diario(dados_registro):
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

    enviar_diario_dropbox()


# --- LÓGICA DE CICLOS ANUAIS (1 A 6) ---


def obter_info_ciclo_atual():
    """
    Retorna o número do ciclo (1 a 6), o ano, e as datas de início e fim.
    Reinicia no Ciclo 1 todo dia 1º de Janeiro.
    
    1º Ciclo: Jan/Fev
    2º Ciclo: Mar/Abr
    3º Ciclo: Mai/Jun
    4º Ciclo: Jul/Ago
    5º Ciclo: Set/Out
    6º Ciclo: Nov/Dez
    """
    hoje = datetime.date.today()
    ano = hoje.year
    mes = hoje.month

    # Número do ciclo de 1 a 6
    num_ciclo = (mes - 1) // 2 + 1

    # Mês de início (1, 3, 5, 7, 9 ou 11) e fim do ciclo
    mes_inicio = (num_ciclo - 1) * 2 + 1
    mes_fim = mes_inicio + 1

    # Data de início do ciclo
    data_inicio = datetime.date(ano, mes_inicio, 1).strftime("%Y-%m-%d 00:00:00")

    # Data de fim do ciclo
    if mes_fim in [4, 6, 9, 11]:
        ultimo_dia = 30
    elif mes_fim == 2:
        ultimo_dia = 29 if (ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)) else 28
    else:
        ultimo_dia = 31

    data_fim = datetime.date(ano, mes_fim, ultimo_dia).strftime("%Y-%m-%d 23:59:59")

    return num_ciclo, ano, data_inicio, data_fim


# --- INICIALIZAÇÃO E CONSULTAS ---


def init_db_bairro():
    if "db_sincronizado_inicio" not in st.session_state:
        carregar_db_do_dropbox()
        st.session_state["db_sincronizado_inicio"] = True

    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarteiroes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_bairro TEXT NOT NULL,
            num_quarteirao TEXT NOT NULL,
            nome_rua TEXT NOT NULL,
            num_lado TEXT NOT NULL,
            num_imovel TEXT NOT NULL,
            tipo_imovel TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def montar_clausula_where(
    f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""
):
    sql_where = " WHERE 1=1"
    params = []

    if f_bairro and f_bairro.strip():
        sql_where += " AND nome_bairro LIKE ?"
        params.append(f"%{f_bairro.strip()}%")

    if f_quarteirao and f_quarteirao.strip():
        lista_q = [
            q.strip()
            for q in re.split(r"[\s,]+", f_quarteirao.strip())
            if q.strip()
        ]
        if lista_q:
            placeholders = ",".join(["?"] * len(lista_q))
            sql_where += f" AND num_quarteirao IN ({placeholders})"
            params.extend(lista_q)

    if f_rua and f_rua.strip():
        sql_where += " AND nome_rua LIKE ?"
        params.append(f"%{f_rua.strip()}%")

    if f_imovel and f_imovel.strip():
        sql_where += " AND num_imovel LIKE ?"
        params.append(f"%{f_imovel.strip()}%")

    if f_tipo and f_tipo != "Todos":
        sql_where += " AND tipo_imovel = ?"
        params.append(f_tipo.strip())

    return sql_where, params


def listar_quarteiroes_com_status(
    f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""
):
    init_db_bairro()
    inicializar_diario_db()

    num_ciclo, ano, data_inicio, data_fim = obter_info_ciclo_atual()

    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    # Anexa diario.db para consulta unificada
    cursor.execute(f"ATTACH DATABASE '{ARQUIVO_DIARIO_DB}' AS db_diario")

    sql_where, params = montar_clausula_where(
        f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo
    )

    sql = f"""
        SELECT 
            q.id, 
            q.nome_bairro, 
            q.num_quarteirao, 
            q.nome_rua, 
            q.num_lado, 
            q.num_imovel, 
            q.tipo_imovel,
            d.situacao AS status_ciclo
        FROM quarteiroes q
        LEFT JOIN (
            SELECT imovel_id, situacao, MAX(data_registro)
            FROM db_diario.diario
            WHERE data_registro BETWEEN '{data_inicio}' AND '{data_fim}'
            GROUP BY imovel_id
        ) d ON q.id = d.imovel_id
        {sql_where}
        ORDER BY q.num_quarteirao ASC, q.num_lado ASC, q.id ASC
    """

    cursor.execute(sql, params)
    dados = cursor.fetchall()
    conn.close()
    return dados


def obter_resumo_filtros(
    f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""
):
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    sql_where, params = montar_clausula_where(
        f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo
    )

    sql_total = "SELECT COUNT(*) FROM quarteiroes" + sql_where
    cursor.execute(sql_total, params)
    total_imoveis = cursor.fetchone()[0]

    sql_por_tipo = (
        "SELECT tipo_imovel, COUNT(*) FROM quarteiroes"
        + sql_where
        + " GROUP BY tipo_imovel"
    )
    cursor.execute(sql_por_tipo, params)
    por_tipo = dict(cursor.fetchall())

    conn.close()
    return total_imoveis, por_tipo
