import os
import firebird.driver as fbd
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def conectar():
    try:
        if current_app and 'DB_CONFIG' in current_app.config:
            db_config = current_app.config['DB_CONFIG']
            host = db_config['host']
            port = db_config['port']
            database_path = db_config['database']
            user = db_config['user']
            password = db_config['password']
        else:
            host = os.environ.get('FIREBIRD_HOST', 'localhost')
            port = os.environ.get('FIREBIRD_PORT', '3052')
            database_path = os.environ.get('FIREBIRD_DB', 'C:\\Users\\nayhan\\Documents\\PROJETOS AZURE\\6- AZURE - REFERENCIAS\\REFERENCIAS\\BD\\REFERENCIAS.FDB')
            user = os.environ.get('FIREBIRD_USER', 'SYSDBA')
            password = os.environ.get('FIREBIRD_PASSWORD', 'masterkey')

        # Formato da string de conexão: host/port:database
        connection_string = f"{host}/{port}:{database_path}"

        logger.info(f"Conectando ao Firebird: {connection_string}")

        conn = fbd.connect(
            database=connection_string,
            user=user,
            password=password
        )
        
        logger.info("Conexão com o Firebird estabelecida com sucesso!")
        return conn

    except Exception as e:
        logger.error(f"Erro ao conectar ao Firebird: {e}")
        raise