import sqlite3

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
    """Retorna apenas os registros que satisfazem TODOS os filtros fornecidos."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    sql_where, params = montar_clausula_where(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)
    sql = """
        SELECT id, nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel 
        FROM quarteiroes 
    """ + sql_where + " ORDER BY id DESC"

    cursor.execute(sql, params)
    dados = cursor.fetchall()
    conn.close()
    return dados


def obter_resumo_filtros(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    """
    Retorna o total geral e a contagem agrupada por tipo de imóvel
    considerando exclusivamente os filtros aplicados.
    """
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    sql_where, params = montar_clausula_where(f_bairro, f_quarteirao, f_rua, f_imovel, f_tipo)

    # 1. Total Geral de Imóveis Filtrados
    sql_total = "SELECT COUNT(*) FROM quarteiroes" + sql_where
    cursor.execute(sql_total, params)
    total_imoveis = cursor.fetchone()[0]

    # 2. Total Por Tipo de Imóvel
    sql_por_tipo = "SELECT tipo_imovel, COUNT(*) FROM quarteiroes" + sql_where + " GROUP BY tipo_imovel"
    cursor.execute(sql_por_tipo, params)
    por_tipo = dict(cursor.fetchall())

    conn.close()
    return total_imoveis, por_tipo
