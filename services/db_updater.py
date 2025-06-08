import logging
from datetime import datetime
from flask import g # Importar g

# Não precisa mais de 'current_app' aqui se todas as chamadas usarem 'g'
# Não precisa mais de 'import sys, os, from database import conectar' se
# esta unidade só for usada dentro do contexto de uma app Flask que já tem 'g' populado.

logger = logging.getLogger(__name__)

def get_db_from_g():
    """Obtém conexão e cursor de flask.g. Assume que g.db_conn e g.db_cur foram definidos em app.before_request."""
    if not hasattr(g, 'db_conn'):
        logger.error("DB_UPDATER: Conexão não encontrada em flask.g!")
        raise RuntimeError("Conexão com banco de dados não disponível em flask.g. Verifique app.py before_request.")
    if not hasattr(g, 'db_cur'):
        logger.error("DB_UPDATER: Cursor não encontrado em flask.g!")
        g.db_cur = g.db_conn.cursor()
        logger.info("DB_UPDATER: Novo cursor criado a partir da conexão em flask.g.")
    return g.db_conn, g.db_cur

def get_variable_cod(variable_sigla_or_name):
    """Busca CODVARIAVEL pela SIGLA ou NOME."""
    conn, cur = get_db_from_g() # Usar a conexão de g
    try:
        cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE SIGLA = ? OR NOME = ?",
                    (variable_sigla_or_name, variable_sigla_or_name))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"DB_UPDATER: Erro ao buscar CODVARIAVEL para '{variable_sigla_or_name}': {e}", exc_info=True)
        return None

def get_or_create_referencia(titulo, ano, descricao=None, codespecialidade=None, codusuario=None):
    """
    Busca uma referência existente ou cria uma nova.
    Retorna CODREFERENCIA.
    `codusuario` é obrigatório para criação.
    """
    conn, cur = get_db_from_g() # Usar a conexão de g
    try:
        cur.execute("SELECT CODREFERENCIA FROM REFERENCIA WHERE UPPER(TITULO) = UPPER(?) AND ANO = ?", (titulo.strip(), ano))
        result = cur.fetchone()
        if result:
            logger.info(f"Referência encontrada: {titulo} ({ano}), CODREFERENCIA: {result[0]}")
            return result[0]
        else:
            if codusuario is None:
                logger.error("CODUSUARIO é necessário para criar nova referência.")
                return None

            dthr = datetime.now()
            cur.execute(
                """
                INSERT INTO REFERENCIA (TITULO, ANO, DESCRICAO, CODUSUARIO, DTHRULTMODIFICACAO, CODESPECIALIDADE)
                VALUES (?, ?, ?, ?, ?, ?) RETURNING CODREFERENCIA
                """,
                (titulo.strip(), ano, descricao, codusuario, dthr, codespecialidade)
            )
            codreferencia = cur.fetchone()[0]
            conn.commit() # Commit após inserção
            logger.info(f"Nova referência criada: {titulo} ({ano}), CODREFERENCIA: {codreferencia}")
            return codreferencia
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro em get_or_create_referencia para '{titulo}': {e}", exc_info=True)
        return None

def insert_normalidade_batch(normalidades_data):
    """
    Insere uma lista de dados de normalidade.
    Cada item em normalidades_data deve ser um dicionário com as chaves:
    codvariavel, codreferencia, valormin, valormax, sexo, idade_min, idade_max, codusuario
    """
    conn, cur = get_db_from_g() # Usar a conexão de g
    try:
        sql = """
            INSERT INTO NORMALIDADE (CODVARIAVEL, CODREFERENCIA, VALORMIN, VALORMAX, SEXO, IDADE_MIN, IDADE_MAX, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params_list = []
        dthr = datetime.now()
        for item in normalidades_data:
            params_list.append((
                item['codvariavel'],
                item['codreferencia'],
                item.get('valormin'),
                item.get('valormax'),
                item.get('sexo', 'A')[:1].upper(), # Garante 1 char maiúsculo, default 'A'
                item.get('idade_min'),
                item.get('idade_max'),
                item['codusuario'],
                dthr
            ))

        if params_list:
            cur.executemany(sql, params_list)
            conn.commit()
            logger.info(f"{len(params_list)} registros de normalidade inseridos com sucesso.")
            return True
        logger.info("Nenhum dado de normalidade para inserir.")
        return False # Retorna False se não havia nada para inserir
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao inserir normalidades em lote: {e}", exc_info=True)
        return False