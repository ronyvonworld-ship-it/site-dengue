# Trecho a adicionar / atualizar em bairro.py
import sqlite3
from datetime import datetime


def obter_resumo_por_datas(data_inicio, data_fim):
    """
    Retorna o resumo acumulado dos lançamentos diários no período selecionado.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT 
            COUNT(id) AS total_lancados,
            SUM(CASE WHEN situacao = 'Normal' THEN 1 ELSE 0 END) AS total_normal,
            SUM(CASE WHEN situacao = 'Fechado' THEN 1 ELSE 0 END) AS total_fechado,
            SUM(CASE WHEN situacao = 'Recuperado' THEN 1 ELSE 0 END) AS total_recuperado,
            COALESCE(SUM(depositos_eliminados), 0) AS total_eliminados,
            COALESCE(SUM(depositos_tratados), 0) AS total_tratados,
            COALESCE(SUM(gramas_medicamento), 0.0) AS total_gramas
        FROM diario_bairro
        WHERE DATE(data_registro) BETWEEN DATE(?) AND DATE(?)
    """

    cursor.execute(query, (data_inicio, data_fim))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "total_lancados": row[0] or 0,
            "total_normal": row[1] or 0,
            "total_fechado": row[2] or 0,
            "total_recuperado": row[3] or 0,
            "total_eliminados": row[4] or 0,
            "total_tratados": row[5] or 0,
            "total_gramas": row[6] or 0.0,
        }
    return {
        "total_lancados": 0,
        "total_normal": 0,
        "total_fechado": 0,
        "total_recuperado": 0,
        "total_eliminados": 0,
        "total_tratados": 0,
        "total_gramas": 0.0,
    }


def verificar_status_quarteirao(bairro_nome, quarteirao_num):
    """
    Verifica se todos os imóveis cadastrados em um quarteirão possuem lançamento no ciclo atual.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total de imóveis cadastrados no quarteirão
    cursor.execute(
        """
        SELECT COUNT(*) FROM imoveis 
        WHERE LOWER(bairro) = LOWER(?) AND LOWER(quarteirao) = LOWER(?)
    """,
        (bairro_nome, quarteirao_num),
    )
    total_cadastrados = cursor.fetchone()[0]

    if total_cadastrados == 0:
        conn.close()
        return False, 0, 0

    # Total de imóveis com lançamento no ciclo atual
    cursor.execute(
        """
        SELECT COUNT(DISTINCT imovel_id) FROM diario_bairro
        WHERE LOWER(bairro) = LOWER(?) AND LOWER(quarteirao) = LOWER(?)
    """,
        (bairro_nome, quarteirao_num),
    )
    total_lancados = cursor.fetchone()[0]
    conn.close()

    concluido = total_lancados >= total_cadastrados
    return concluido, total_lancados, total_cadastrados
