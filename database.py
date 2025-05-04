import os
import firebird.driver as fbd
import logging

logger = logging.getLogger(__name__)

def conectar():
    host = os.environ.get('FIREBIRD_HOST', 'localhost')
    port = os.environ.get('FIREBIRD_PORT', '3052')
    database_path = os.environ.get('FIREBIRD_DB', '/app/data/REFERENCIAS.FDB')
    user = os.environ.get('FIREBIRD_USER', 'SYSDBA')
    password = os.environ.get('FIREBIRD_PASSWORD', 'masterkey')

    try:
        conn = fbd.connect(
            database=database_path,
            host=host,
            port=int(port),
            user=user,
            password=password
        )
        logger.info("Conexão com o Firebird estabelecida!")
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao Firebird: {e}")
        raise



    #def conectar():
#    return fbd.connect(
#        r"nayhan/3052:C:\Users\nayhan\Documents\PROJETOS AZURE\6- AZURE - REFERENCIAS\REFERENCIAS\BANCO REFERENCIA\BD\REFERENCIAS.FDB",
#        user="SYSDBA",
#        password="masterkey"
#    )