import logging
from datetime import datetime
from flask import current_app # Para obter a conexão do app Flask

logger = logging.getLogger(__name__)

def get_db_from_app():
    """Obtém conexão e cursor do contexto da aplicação Flask."""
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        # Isso pode acontecer se chamado fora de um request context ou se before_request não rodou.
        # Para scripts standalone, você precisaria de uma conexão direta.
        from database import conectar # Importação local para evitar dependência circular no nível do módulo
        logger.warning("Obtendo nova conexão com o BD fora do contexto Flask.")
        conn = conectar()
        cur = conn.cursor()
        # Nota: Esta conexão precisaria ser gerenciada (fechada) manualmente se usada assim.
    return conn, cur


def get_variable_cod(variable_sigla_or_name):
    """Busca CODVARIAVEL pela SIGLA ou NOME."""
    conn, cur = get_db_from_app()
    try:
        cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE SIGLA = ? OR NOME = ?", (variable_sigla_or_name, variable_sigla_or_name))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Erro ao buscar CODVARIAVEL para '{variable_sigla_or_name}': {e}")
        return None

def get_or_create_referencia(titulo, ano, descricao=None, codespecialidade=None, codusuario=None):
    """
    Busca uma referência existente ou cria uma nova.
    Retorna CODREFERENCIA.
    `codusuario` é obrigatório para criação.
    """
    conn, cur = get_db_from_app()
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
        logger.error(f"Erro em get_or_create_referencia para '{titulo}': {e}")
        return None

def insert_normalidade_batch(normalidades_data):
    """
    Insere uma lista de dados de normalidade.
    Cada item em normalidades_data deve ser um dicionário com as chaves:
    codvariavel, codreferencia, valormin, valormax, sexo, idade_min, idade_max, codusuario
    """
    conn, cur = get_db_from_app()
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
                item.get('sexo', 'A')[:1], # Garante que seja apenas 1 caractere, default 'A'
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
        return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao inserir normalidades em lote: {e}")
        return False