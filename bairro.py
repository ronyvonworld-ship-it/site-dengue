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


def listar_quarteiroes(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    """Retorna apenas os registros que satisfazem TODOS os filtros fornecidos."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    sql = """
        SELECT id, nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel 
        FROM quarteiroes 
        WHERE 1=1
    """
    params = []

    if f_bairro and f_bairro.strip():
        sql += " AND nome_bairro LIKE ?"
        params.append(f"%{f_bairro.strip()}%")

    if f_quarteirao and f_quarteirao.strip():
        sql += " AND num_quarteirao LIKE ?"
        params.append(f"%{f_quarteirao.strip()}%")

    if f_rua and f_rua.strip():
        sql += " AND nome_rua LIKE ?"
        params.append(f"%{f_rua.strip()}%")

    if f_imovel and f_imovel.strip():
        sql += " AND num_imovel LIKE ?"
        params.append(f"%{f_imovel.strip()}%")

    if f_tipo and f_tipo != "Todos":
        sql += " AND tipo_imovel = ?"
        params.append(f_tipo.strip())

    sql += " ORDER BY id DESC"

    cursor.execute(sql, params)
    dados = cursor.fetchall()
    conn.close()
    return dados
