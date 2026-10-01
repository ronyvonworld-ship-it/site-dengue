import sqlite3
import os
import streamlit as st

ARQUIVO_DB_BAIRRO = "bairro.db"


def init_db_bairro():
    """Cria a tabela de quarteirões/imóveis caso ela não exista."""
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
    """Insere um novo imóvel no banco de dados."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quarteiroes (nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (bairro, quarteirao, rua, lado, imovel, tipo))
    conn.commit()
    conn.close()


def atualizar_quarteirao(id_reg, bairro, quarteirao, rua, lado, imovel, tipo):
    """Atualiza as informações de um imóvel existente pelo ID."""
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


def excluir_quarteirao(id_reg):
    """Remove um registro pelo ID."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quarteiroes WHERE id = ?", (id_reg,))
    conn.commit()
    conn.close()


def montar_clausula_where(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    """Função auxiliar para construir a instrução WHERE com base nos filtros."""
    sql_where = " WHERE 1=1"
    params = []

    if f_bairro and f_bairro.strip():
        sql_where += " AND nome_bairro LIKE ?"
        params.append(f"%{f_bairro.strip()}%")

    if f_quarteirao and f_quarteirao.strip():
        sql_where += " AND num_quarteirao LIKE ?"
        params.append(f"%{f_quarteirao.strip()}%")

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
    """Retorna os registros em ordem inversa de ID (do maior/mais recente para o menor)."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    sql_where, params = montar_clausula_where(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)
    
    # ORDEM INVERSA APLICADA AQUI (ORDER BY id DESC)
    sql = """
        SELECT id, nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel 
        FROM quarteiroes 
    """ + sql_where + " ORDER BY id DESC"

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


# --- FUNÇÕES DE INTERFACE COM CONFIRMAÇÃO ---

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


# --- FUNÇÕES DE DOWNLOAD E UPLOAD DO BANCO DE DADOS ---

def obter_bytes_db():
    """Garante que o banco existe e retorna os bytes do arquivo para download."""
    init_db_bairro()
    if os.path.exists(ARQUIVO_DB_BAIRRO):
        with open(ARQUIVO_DB_BAIRRO, "rb") as f:
            return f.read()
    return b""


def gerenciar_backup_db():
    """Renderiza os botões de Download e Upload para gerenciamento do arquivo .db."""
    st.subheader("💾 Backup e Restauração do Banco de Dados (`bairro.db`)")
    
    col_down, col_up = st.columns(2)

    # Download do arquivo DB
    with col_down:
        st.markdown("**1. Baixar cópia do banco de dados**")
        bytes_db = obter_bytes_db()
        st.download_button(
            label="⬇️ Baixar bairro.db",
            data=bytes_db,
            file_name="bairro.db",
            mime="application/x-sqlite3",
            use_container_width=True
        )

    # Upload e substituição do arquivo DB com tratamento de bloqueio e substituição segura
    with col_up:
        st.markdown("**2. Restaurar/Substituir banco de dados**")
        arquivo_enviado = st.file_uploader("Selecione um arquivo .db", type=["db", "sqlite3", "sqlite"], key="uploader_db")

        if arquivo_enviado is not None:
            if st.button("⚠️ Confirmar Sobrescrita do Banco", use_container_width=True, key="btn_confirmar_upload"):
                try:
                    # Lê os bytes do arquivo enviado antes de tocar no arquivo do disco
                    conteudo_novo = arquivo_enviado.getvalue()

                    # Força a limpeza de conexões pendentes do SQLite no thread
                    sqlite3.connect(ARQUIVO_DB_BAIRRO).close()

                    # Sobrescreve o arquivo
                    with open(ARQUIVO_DB_BAIRRO, "wb") as f:
                        f.write(conteudo_novo)

                    st.cache_data.clear()
                    st.success("Banco de dados substituído com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar arquivo: {e}")
