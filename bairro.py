import sqlite3
import os
import re
import streamlit as st
import dropbox
from dropbox.exceptions import ApiError

# --- CONFIGURAÇÕES DE BANCO DE DADOS E DROPBOX ---
ARQUIVO_DB_BAIRRO = "bairro.db"
CAMINHO_DROPBOX = "/bairro.db"

# Busca credenciais puramente do st.secrets (sem expor dados sensíveis no código)
DROPBOX_APP_KEY = st.secrets.get("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET = st.secrets.get("DROPBOX_APP_SECRET", "")
DROPBOX_REFRESH_TOKEN = st.secrets.get("DROPBOX_REFRESH_TOKEN", "")


# --- FUNÇÕES DE CONEXÃO E SINCRONIZAÇÃO COM REFRESH TOKEN ---

def obter_cliente_dropbox():
    """
    Retorna uma instância autenticada da API do Dropbox utilizando
    Refresh Token para renovação automática do token de acesso.
    """
    if not all([DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN]):
        st.error("❌ Credenciais do Dropbox não foram configuradas no st.secrets!")
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


def carregar_db_do_dropbox(forcar_download=False):
    """
    Baixa o banco de dados do Dropbox.
    Se forcar_download=True, ele substitui o banco local pelo da nuvem.
    """
    db_cliente = obter_cliente_dropbox()
    if not db_cliente:
        return

    try:
        # Faz o download do banco de dados mais recente do Dropbox
        _, resposta = db_cliente.files_download(CAMINHO_DROPBOX)
        with open(ARQUIVO_DB_BAIRRO, "wb") as f:
            f.write(resposta.content)
        st.toast("📥 Banco de dados sincronizado do Dropbox com sucesso!", icon="🔄")
    except ApiError as err:
        st.warning("⚠️ Arquivo 'bairro.db' não foi encontrado na nuvem. Um novo banco local será mantido/criado.")
    except Exception as e:
        st.error(f"❌ Erro ao baixar banco do Dropbox: {e}")


def enviar_db_para_dropbox():
    """Sobe a versão atualizada do banco de dados local para o Dropbox."""
    db_cliente = obter_cliente_dropbox()
    if not db_cliente:
        return False

    if os.path.exists(ARQUIVO_DB_BAIRRO):
        try:
            with open(ARQUIVO_DB_BAIRRO, "rb") as f:
                # Mode overwrite garante que a versão antiga na nuvem seja substituída
                db_cliente.files_upload(
                    f.read(),
                    CAMINHO_DROPBOX,
                    mode=dropbox.files.WriteMode.overwrite
                )
            st.toast("☁️ Alterações salvas no Dropbox!", icon="✅")
            return True
        except Exception as e:
            st.error(f"❌ Erro ao enviar banco de dados para o Dropbox: {e}")
            return False
    return False


# --- INICIALIZAÇÃO DO BANCO ---

def init_db_bairro():
    """
    Executado na inicialização da aplicação:
    1. Baixa/sincroniza o banco de dados do Dropbox automaticamente no primeiro acesso da sessão.
    2. Garante a criação da tabela local caso ela ainda não exista.
    """
    if "db_sincronizado_inicio" not in st.session_state:
        carregar_db_do_dropbox(forcar_download=True)
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


# --- OPERAÇÕES CRUD COM AUTOSAVE NO DROPBOX ---

def salvar_quarteirao(bairro, quarteirao, rua, lado, imovel, tipo):
    """Insere um novo imóvel no banco de dados e sincroniza no Dropbox."""
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
    """Atualiza as informações de um imóvel e sincroniza no Dropbox."""
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
    """Remove um registro pelo ID e sincroniza no Dropbox."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quarteiroes WHERE id = ?", (id_reg,))
    conn.commit()
    conn.close()

    enviar_db_para_dropbox()


# --- CONSULTAS SQL ---

def montar_clausula_where(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    """Função auxiliar para construir a instrução WHERE com suporte a múltiplos quarteirões."""
    sql_where = " WHERE 1=1"
    params = []

    if f_bairro and f_bairro.strip():
        sql_where += " AND nome_bairro LIKE ?"
        params.append(f"%{f_bairro.strip()}%")

    if f_quarteirao and f_quarteirao.strip():
        lista_q = [q.strip() for q in re.split(r'[\s,]+', f_quarteirao.strip()) if q.strip()]
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


def listar_quarteiroes(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    """Retorna os registros ordenados por quarteirão, lado e ID."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    sql_where, params = montar_clausula_where(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)
    
    sql = """
        SELECT id, nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel 
        FROM quarteiroes 
    """ + sql_where + " ORDER BY num_quarteirao ASC, num_lado ASC, id ASC"

    cursor.execute(sql, params)
    dados = cursor.fetchall()
    conn.close()
    return dados


def obter_resumo_filtros(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    """Retorna o total geral e a contagem agrupada por tipo de imóvel conforme os filtros."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    sql_where, params = montar_clausula_where(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)

    sql_total = "SELECT COUNT(*) FROM quarteiroes" + sql_where
    cursor.execute(sql_total, params)
    total_imoveis = cursor.fetchone()[0]

    sql_por_tipo = "SELECT tipo_imovel, COUNT(*) FROM quarteiroes" + sql_where + " GROUP BY tipo_imovel"
    cursor.execute(sql_por_tipo, params)
    por_tipo = dict(cursor.fetchall())

    conn.close()
    return total_imoveis, por_tipo


# --- INTERFACE COM CONFIRMAÇÃO ---

def confirmar_e_atualizar(id_sel, bairro_val, quarteirao_val, rua_val, lado_val, imovel_val, tipo_val):
    """Exibe a caixa de confirmação para edição dentro do módulo bairro."""
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
    """Exibe a caixa de confirmação para exclusão dentro do módulo bairro."""
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


# --- BACKUP LOCAL & RESTAURAÇÃO MANUAL / UPLOAD ---

def obter_bytes_db():
    """Garante que o banco existe e retorna os bytes do arquivo para download."""
    init_db_bairro()
    if os.path.exists(ARQUIVO_DB_BAIRRO):
        with open(ARQUIVO_DB_BAIRRO, "rb") as f:
            return f.read()
    return b""


def gerenciar_backup_db():
    """Renderiza os botões de gerenciamento local, upload de arquivo e sincronização manual."""
    st.subheader("💾 Backup e Sincronização (`bairro.db`)")
    
    col_down, col_up, col_sync = st.columns(3)

    # 1. Download do banco local
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

    # 2. Upload de banco do computador
    with col_up:
        st.markdown("**2. Enviar arquivo do computador**")
        arquivo_enviado = st.file_uploader(
            "Selecione um arquivo .db local",
            type=["db", "sqlite", "sqlite3"],
            key="uploader_db_bairro",
            label_visibility="collapsed"
        )
        if arquivo_enviado is not None:
            if st.button("⬆️ Restaurar/Substituir via Upload", use_container_width=True):
                try:
                    with open(ARQUIVO_DB_BAIRRO, "wb") as f:
                        f.write(arquivo_enviado.getbuffer())
                    
                    # Sincroniza o novo banco enviado para a nuvem Dropbox
                    enviar_db_para_dropbox()
                    st.success("✅ Banco de dados atualizado e enviado para o Dropbox com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar o arquivo enviado: {e}")

    # 3. Forçar restauração via Dropbox
    with col_sync:
        st.markdown("**3. Sincronizar via Dropbox**")
        if st.button("🔄 Restaurar da Nuvem", use_container_width=True):
            carregar_db_do_dropbox(forcar_download=True)
            st.rerun()
