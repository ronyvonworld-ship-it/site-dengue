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

DROPBOX_APP_KEY = st.secrets.get("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET = st.secrets.get("DROPBOX_APP_SECRET", "")
DROPBOX_REFRESH_TOKEN = st.secrets.get("DROPBOX_REFRESH_TOKEN", "")


# --- FUNÇÃO DE ESTILIZAÇÃO VISUAL ---

def colorir_linha_por_situacao(row):
    situacao = row.get("Status Ciclo") if "Status Ciclo" in row else row.get("status_ciclo")

    if situacao in ["Normal", "Recuperado"]:
        return ["background-color: #d4edda; color: #155724; font-weight: bold;"] * len(row)
    elif situacao == "Fechado":
        return ["background-color: #f8d7da; color: #721c24; font-weight: bold;"] * len(row)
    else:
        return [""] * len(row)


# --- CONEXÃO DROPBOX ---

def obter_cliente_dropbox():
    if not all([DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN]):
        return None
    try:
        dbx = dropbox.Dropbox(
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN
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
            pass
        except Exception as e:
            st.error(f"❌ Erro ao restaurar banco do Dropbox: {e}")


def sincronizar_banco():
    carregar_db_do_dropbox(forcar=True)


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
                    mode=dropbox.files.WriteMode.overwrite
                )
            st.toast("☁️ Alterações salvas no Dropbox!", icon="✅")
            return True
        except Exception as e:
            st.error(f"❌ Erro ao enviar banco para o Dropbox: {e}")
            return False
    return False


# --- BANCO DIÁRIO ---

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
            usuario TEXT DEFAULT '',
            data_registro DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Garante que a coluna usuario exista caso o banco tenha sido criado anteriormente sem ela
    try:
        cursor.execute("ALTER TABLE diario ADD COLUMN usuario TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

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
                    mode=dropbox.files.WriteMode.overwrite
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
    cursor.execute("""
        INSERT INTO diario (
            imovel_id, bairro, quarteirao, rua, num_imovel, tipo_imovel,
            situacao, depositos_eliminados, fez_tratamento, depositos_tratados, gramas_medicamento, usuario
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, dados_registro)
    conn.commit()
    conn.close()

    enviar_diario_dropbox()


# --- LÓGICA DE CICLOS ANUAIS (6 CICLOS/ANO) ---

def obter_info_ciclo_atual():
    hoje = datetime.date.today()
    ano = hoje.year
    mes = hoje.month

    num_ciclo = (mes - 1) // 2 + 1
    mes_inicio = (num_ciclo - 1) * 2 + 1
    mes_fim = mes_inicio + 1

    data_inicio = datetime.date(ano, mes_inicio, 1).strftime("%Y-%m-%d 00:00:00")

    if mes_fim in [4, 6, 9, 11]:
        ultimo_dia = 30
    elif mes_fim == 2:
        ultimo_dia = 29 if (ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)) else 28
    else:
        ultimo_dia = 31

    data_fim = datetime.date(ano, mes_fim, ultimo_dia).strftime("%Y-%m-%d 23:59:59")

    return num_ciclo, ano, data_inicio, data_fim


# --- BANCO BAIRRO & CONSULTAS ---

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


def salvar_quarteirao(bairro, quarteirao, rua, lado, imovel, tipo):
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quarteiroes (nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (bairro, quarteirao, rua, lado, imovel, tipo))
    conn.commit()
    conn.close()
    enviar_db_para_dropbox()


def atualizar_quarteirao(id_reg, bairro, quarteirao, rua, lado, imovel, tipo):
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE quarteiroes
        SET nome_bairro = ?, num_quarteirao = ?, nome_rua = ?, num_lado = ?, num_imovel = ?, tipo_imovel = ?
        WHERE id = ?
    """, (bairro, quarteirao, rua, lado, imovel, tipo, id_reg))
    conn.commit()
    conn.close()
    enviar_db_para_dropbox()


def excluir_quarteirao(id_reg):
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quarteiroes WHERE id = ?", (id_reg,))
    conn.commit()
    conn.close()
    enviar_db_para_dropbox()


def montar_clausula_where(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    sql_where = " WHERE 1=1"
    params = []

    if f_bairro and f_bairro.strip():
        sql_where += " AND q.nome_bairro LIKE ?"
        params.append(f"%{f_bairro.strip()}%")

    if f_quarteirao and f_quarteirao.strip():
        lista_q = [q.strip() for q in re.split(r'[\s,]+', f_quarteirao.strip()) if q.strip()]
        if lista_q:
            placeholders = ",".join(["?"] * len(lista_q))
            sql_where += f" AND q.num_quarteirao IN ({placeholders})"
            params.extend(lista_q)

    if f_rua and f_rua.strip():
        sql_where += " AND q.nome_rua LIKE ?"
        params.append(f"%{f_rua.strip()}%")

    if f_imovel and f_imovel.strip():
        sql_where += " AND q.num_imovel LIKE ?"
        params.append(f"%{f_imovel.strip()}%")

    if f_tipo and f_tipo != "Todos":
        sql_where += " AND q.tipo_imovel = ?"
        params.append(f_tipo.strip())

    return sql_where, params


def listar_quarteiroes(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    sql_where, params = montar_clausula_where(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)
    sql = "SELECT id, nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel FROM quarteiroes q" + sql_where + " ORDER BY CAST(q.num_quarteirao AS INTEGER) ASC, q.num_lado ASC, q.id ASC"
    cursor.execute(sql, params)
    dados = cursor.fetchall()
    conn.close()
    return dados


def listar_quarteiroes_com_status(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    init_db_bairro()
    inicializar_diario_db()

    num_ciclo, ano, data_inicio, data_fim = obter_info_ciclo_atual()

    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    cursor.execute(f"ATTACH DATABASE '{ARQUIVO_DIARIO_DB}' AS db_diario")

    sql_where, params = montar_clausula_where(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)

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
        ORDER BY CAST(q.num_quarteirao AS INTEGER) ASC, q.num_lado ASC, q.id ASC
    """

    cursor.execute(sql, params)
    dados = cursor.fetchall()
    conn.close()
    return dados


def obter_resumo_filtros(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    sql_where, params = montar_clausula_where(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)

    sql_total = "SELECT COUNT(*) FROM quarteiroes q" + sql_where
    cursor.execute(sql_total, params)
    total_imoveis = cursor.fetchone()[0]

    sql_por_tipo = "SELECT q.tipo_imovel, COUNT(*) FROM quarteiroes q" + sql_where + " GROUP BY q.tipo_imovel"
    cursor.execute(sql_por_tipo, params)
    por_tipo = dict(cursor.fetchall())

    conn.close()
    return total_imoveis, por_tipo


# --- RESUMO POR USUARIO E POR DATAS ---

def obter_resumo_por_usuario_e_datas(usuario, data_inicio, data_fim):
    """
    Retorna o resumo dos lançamentos diários EXCLUSIVAMENTE do usuário informado no período selecionado.
    """
    inicializar_diario_db()
    conn = sqlite3.connect(ARQUIVO_DIARIO_DB)
    cursor = conn.cursor()

    query = """
        SELECT 
            COUNT(id) AS total_lancados,
            SUM(CASE WHEN situacao = 'Normal' THEN 1 ELSE 0 END) AS total_normal,
            SUM(CASE WHEN situacao = 'Fechado' THEN 1 ELSE 0 END) AS total_fechado,
            SUM(CASE WHEN situacao = 'Recuperado' THEN 1 ELSE 0 END) AS total_recuperado,
            SUM(CASE WHEN tipo_imovel = 'Residência' THEN 1 ELSE 0 END) AS total_residencia,
            SUM(CASE WHEN tipo_imovel = 'Comércio' THEN 1 ELSE 0 END) AS total_comercio,
            SUM(CASE WHEN tipo_imovel = 'Terreno Baldio' THEN 1 ELSE 0 END) AS total_terreno,
            SUM(CASE WHEN tipo_imovel NOT IN ('Residência', 'Comércio', 'Terreno Baldio') THEN 1 ELSE 0 END) AS total_outro,
            COALESCE(SUM(depositos_eliminados), 0) AS total_eliminados,
            COALESCE(SUM(depositos_tratados), 0) AS total_tratados,
            COALESCE(SUM(gramas_medicamento), 0.0) AS total_gramas
        FROM diario
        WHERE LOWER(usuario) = LOWER(?)
          AND DATE(data_registro) BETWEEN DATE(?) AND DATE(?)
    """

    cursor.execute(query, (str(usuario).strip(), str(data_inicio), str(data_fim)))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "total_lancados": row[0] or 0,
            "total_normal": row[1] or 0,
            "total_fechado": row[2] or 0,
            "total_recuperado": row[3] or 0,
            "total_residencia": row[4] or 0,
            "total_comercio": row[5] or 0,
            "total_terreno": row[6] or 0,
            "total_outro": row[7] or 0,
            "total_eliminados": row[8] or 0,
            "total_tratados": row[9] or 0,
            "total_gramas": row[10] or 0.0,
        }
    return {
        "total_lancados": 0,
        "total_normal": 0,
        "total_fechado": 0,
        "total_recuperado": 0,
        "total_residencia": 0,
        "total_comercio": 0,
        "total_terreno": 0,
        "total_outro": 0,
        "total_eliminados": 0,
        "total_tratados": 0,
        "total_gramas": 0.0,
    }


def obter_resumo_por_datas(data_inicio, data_fim):
    inicializar_diario_db()
    conn = sqlite3.connect(ARQUIVO_DIARIO_DB)
    cursor = conn.cursor()

    query = """
        SELECT 
            COUNT(id) AS total_lancados,
            SUM(CASE WHEN situacao = 'Normal' THEN 1 ELSE 0 END) AS total_normal,
            SUM(CASE WHEN situacao = 'Fechado' THEN 1 ELSE 0 END) AS total_fechado,
            SUM(CASE WHEN situacao = 'Recuperado' THEN 1 ELSE 0 END) AS total_recuperado,
            SUM(CASE WHEN tipo_imovel = 'Residência' THEN 1 ELSE 0 END) AS total_residencia,
            SUM(CASE WHEN tipo_imovel = 'Comércio' THEN 1 ELSE 0 END) AS total_comercio,
            SUM(CASE WHEN tipo_imovel = 'Terreno Baldio' THEN 1 ELSE 0 END) AS total_terreno,
            SUM(CASE WHEN tipo_imovel NOT IN ('Residência', 'Comércio', 'Terreno Baldio') THEN 1 ELSE 0 END) AS total_outro,
            COALESCE(SUM(depositos_eliminados), 0) AS total_eliminados,
            COALESCE(SUM(depositos_tratados), 0) AS total_tratados,
            COALESCE(SUM(gramas_medicamento), 0.0) AS total_gramas
        FROM diario
        WHERE DATE(data_registro) BETWEEN DATE(?) AND DATE(?)
    """

    cursor.execute(query, (str(data_inicio), str(data_fim)))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "total_lancados": row[0] or 0,
            "total_normal": row[1] or 0,
            "total_fechado": row[2] or 0,
            "total_recuperado": row[3] or 0,
            "total_residencia": row[4] or 0,
            "total_comercio": row[5] or 0,
            "total_terreno": row[6] or 0,
            "total_outro": row[7] or 0,
            "total_eliminados": row[8] or 0,
            "total_tratados": row[9] or 0,
            "total_gramas": row[10] or 0.0,
        }
    return {
        "total_lancados": 0,
        "total_normal": 0,
        "total_fechado": 0,
        "total_recuperado": 0,
        "total_residencia": 0,
        "total_comercio": 0,
        "total_terreno": 0,
        "total_outro": 0,
        "total_eliminados": 0,
        "total_tratados": 0,
        "total_gramas": 0.0,
    }


def listar_status_quarteiroes_por_bairro(bairro_nome):
    init_db_bairro()
    inicializar_diario_db()

    num_ciclo, ano, data_inicio, data_fim = obter_info_ciclo_atual()

    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    cursor.execute(f"ATTACH DATABASE '{ARQUIVO_DIARIO_DB}' AS db_diario")

    query = f"""
        SELECT 
            q.num_quarteirao,
            COUNT(q.id) AS total_imoveis,
            COUNT(DISTINCT d.imovel_id) AS total_lancados
        FROM quarteiroes q
        LEFT JOIN db_diario.diario d 
            ON q.id = d.imovel_id 
           AND d.data_registro BETWEEN '{data_inicio}' AND '{data_fim}'
        WHERE LOWER(q.nome_bairro) LIKE LOWER(?)
        GROUP BY q.num_quarteirao
        ORDER BY CAST(q.num_quarteirao AS INTEGER) ASC
    """

    cursor.execute(query, (f"%{bairro_nome.strip()}%",))
    registros = cursor.fetchall()
    conn.close()

    resultado = []
    for q_num, total, lancados in registros:
        concluido = (lancados >= total) and (total > 0)
        status_txt = "✅ CONCLUÍDO" if concluido else "❌ INCOMPLETO"
        resultado.append({
            "Quarteirão": q_num,
            "Total Imóveis": total,
            "Imóveis Visitados": lancados,
            "Pendentes": max(0, total - lancados),
            "Status": status_txt
        })

    return resultado


# --- RECURSOS AUXILIARES ---

def confirmar_e_atualizar(id_sel, bairro_val, quarteirao_val, rua_val, lado_val, imovel_val, tipo_val):
    chave_edicao = f"confirmar_edicao_{id_sel}"
    if st.button("💾 Salvar Alterações", use_container_width=True, key=f"btn_salvar_{id_sel}"):
        st.session_state[chave_edicao] = True
        st.session_state[f"confirmar_exclusao_{id_sel}"] = False

    if st.session_state.get(chave_edicao, False):
        st.info(f"❓ Tem certeza de que deseja atualizar o **Registro ID {id_sel}**?")
        col_sim, col_nao = st.columns(2)
        with col_sim:
            if st.button("✅ Confirmar Atualização", key=f"sim_edit_{id_sel}", use_container_width=True):
                atualizar_quarteirao(id_sel, bairro_val, quarteirao_val, rua_val, lado_val, imovel_val, tipo_val)
                st.session_state[chave_edicao] = False
                st.success(f"Registro ID {id_sel} atualizado com sucesso!")
                st.rerun()
        with col_nao:
            if st.button("❌ Cancelar", key=f"cancela_edit_{id_sel}", use_container_width=True):
                st.session_state[chave_edicao] = False
                st.rerun()


def confirmar_e_excluir(id_sel):
    chave_exclusao = f"confirmar_exclusao_{id_sel}"
    if st.button("🗑️ Excluir Imóvel", use_container_width=True, key=f"btn_excluir_{id_sel}"):
        st.session_state[chave_exclusao] = True
        st.session_state[f"confirmar_edicao_{id_sel}"] = False

    if st.session_state.get(chave_exclusao, False):
        st.warning(f"⚠️ **ATENÇÃO:** Tem certeza de que deseja excluir o **Registro ID {id_sel}**?")
        col_sim, col_nao = st.columns(2)
        with col_sim:
            if st.button("🔴 Sim, Excluir Registro", key=f"sim_exc_{id_sel}", use_container_width=True):
                excluir_quarteirao(id_sel)
                st.session_state[chave_exclusao] = False
                st.success(f"Registro ID {id_sel} excluído com sucesso!")
                st.rerun()
        with col_nao:
            if st.button("❌ Cancelar", key=f"cancela_exc_{id_sel}", use_container_width=True):
                st.session_state[chave_exclusao] = False
                st.rerun()


def obter_bytes_db():
    init_db_bairro()
    if os.path.exists(ARQUIVO_DB_BAIRRO):
        with open(ARQUIVO_DB_BAIRRO, "rb") as f:
            return f.read()
    return b""


def gerenciar_backup_db():
    st.subheader("💾 Backup e Sincronização (`bairro.db`)")
    col_down, col_up, col_sync = st.columns(3)

    with col_down:
        st.markdown("**1. Baixar banco local**")
        bytes_db = obter_bytes_db()
        st.download_button(
            label="⬇️ Baixar bairro.db",
            data=bytes_db,
            file_name="bairro.db",
            mime="application/x-sqlite3",
            use_container_width=True
        )

    with col_up:
        st.markdown("**2. Enviar arquivo do computador**")
        arquivo_enviado = st.file_uploader(
            "Selecione um arquivo .db local",
            type=["db", "sqlite", "sqlite3"],
            key="uploader_db_bairro",
            label_visibility="collapsed"
        )
        if arquivo_enviado is not None:
            if st.button("⬆ Restaurar/Substituir via Upload", use_container_width=True):
                try:
                    with open(ARQUIVO_DB_BAIRRO, "wb") as f:
                        f.write(arquivo_enviado.getbuffer())
                    enviar_db_para_dropbox()
                    st.success("✅ Banco de dados atualizado e enviado para o Dropbox com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar o arquivo enviado: {e}")

    with col_sync:
        st.markdown("**3. Sincronizar via Dropbox**")
        if st.button("🔄 Restaurar da Nuvem", use_container_width=True):
            carregar_db_do_dropbox(forcar=True)
            st.rerun()
