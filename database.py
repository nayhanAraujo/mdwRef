import os
import firebird.driver as fbd
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def conectar():
    try:
        # Configurações padrão para desenvolvimento local
        default_local_db = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'BD', 'REFERENCIAS.FDB'
        ).replace('\\', '/')  # Garante barras no formato Unix

        # Obtém configurações
        if current_app and 'DB_CONFIG' in current_app.config:
            db_config = current_app.config['DB_CONFIG']
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', '3052')
            database_path = db_config['database']
            user = db_config.get('user', 'SYSDBA')
            password = db_config.get('password', 'masterkey')
        else:
            host = os.environ.get('FIREBIRD_HOST', 'localhost')
            port = os.environ.get('FIREBIRD_PORT', '3052')
            
            if os.environ.get('FLY_APP_NAME'):
                database_path = os.environ.get('FIREBIRD_DB', '/app/data/REFERENCIAS.FDB')
            else:
                database_path = os.path.abspath(
                    os.environ.get('FIREBIRD_DB', default_local_db)
                ).replace('\\', '/')
            
            user = os.environ.get('FIREBIRD_USER', 'SYSDBA')
            password = os.environ.get('FIREBIRD_PASSWORD', 'masterkey')

        # Formato da string de conexão: host/port:database
        connection_string = f"{host}/{port}:{database_path}"

        logger.info(f"Tentando conectar com: {connection_string}")

        conn = fbd.connect(
            database=connection_string,
            user=user,
            password=password,
            charset='UTF8'
        )
        
        logger.info("Conexão estabelecida com sucesso!")
        return conn

    except Exception as e:
        logger.error(f"Falha na conexão: {str(e)}", exc_info=True)
        raise RuntimeError(f"Erro de conexão com o banco: {str(e)}") from e