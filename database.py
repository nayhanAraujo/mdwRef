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
            port = int(db_config['port'])
            database_path = db_config['database']
            user = db_config['user']
            password = db_config['password']
        else:
            host = os.environ.get('FIREBIRD_HOST', 'localhost')
            port = int(os.environ.get('FIREBIRD_PORT', '3052'))
            database_path = os.environ.get('FIREBIRD_DB', '/app/data/REFERENCIAS.FDB')
            user = os.environ.get('FIREBIRD_USER', 'SYSDBA')
            password = os.environ.get('FIREBIRD_PASSWORD', 'masterkey')

        logger.info(f"Conectando ao Firebird: {host}:{port}:{database_path}")

        conn = fbd.connect(
        database=f"{host}/{port}:{database_path}",
        user=user,
        password=password,
        charset='ISO8859_1'
    )
        
        logger.info("Conexão com o Firebird estabelecida com sucesso!")
        return conn

    except Exception as e:
        logger.error(f"Erro ao conectar ao Firebird: {e}")
        raise