import os
import firebird.driver as fbd
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def conectar():
    try:
        default_local_db = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'BD', 'REFERENCIAS.FDB'
        ).replace('\\', '/')

        if current_app and 'DB_CONFIG' in current_app.config:
            db_config = current_app.config['DB_CONFIG']
            host = db_config.get('host', '127.0.0.1')
            port = db_config.get('port', '3052')
            database_path = db_config['database']
            user = db_config.get('user', 'SYSDBA')
            password = db_config.get('password', 'masterkey')
        else:
            host = os.environ.get('FIREBIRD_HOST', '127.0.0.1')
            port = os.environ.get('FIREBIRD_PORT', '3052')
            database_path = os.path.abspath(
                os.environ.get('FIREBIRD_DB', default_local_db)
            ).replace('\\', '/')
            user = os.environ.get('FIREBIRD_USER', 'SYSDBA')
            password = os.environ.get('FIREBIRD_PASSWORD', 'masterkey')

        connection_string = f"{host}/{port}:{database_path}"
        logger.info(f"Tentando conectar com: {connection_string}")

        conn = fbd.connect(
            database=connection_string,
            user=user,
            password=password,
            charset='ISO8859_1'
        )
        logger.info("Conexão estabelecida com sucesso!")
        return conn
    except Exception as e:
        logger.error(f"Falha na conexão: {str(e)}", exc_info=True)
        raise RuntimeError(f"Erro de conexão com o banco: {str(e)}") from e