import os
import firebird.driver as fbd
from flask import current_app






def conectar():
    # Configurações via variáveis de ambiente (recomendado para produção)
    host = os.environ.get('FIREBIRD_HOST', 'localhost')  # Padrão: localhost
    port = os.environ.get('FIREBIRD_PORT', '3052')       # Padrão: 3050
    database_path = os.environ.get('FIREBIRD_DB', '/app/data/REFERENCIAS.FDB')  # Caminho no container
    user = os.environ.get('FIREBIRD_USER', 'SYSDBA')
    password = os.environ.get('FIREBIRD_PASSWORD', 'masterkey')

    try:
        conn = fbd.connect(
            host=f"{host}/{port}:{database_path}",  # Formato: "host/port:path"
            user=user,
            password=password
        )
        current_app.logger.info("Conexão com o Firebird estabelecida!")
        return conn
    except Exception as e:
        current_app.logger.error(f"Erro ao conectar ao Firebird: {e}")
        raise  # Relança a exceção para tratamento externo












#def conectar():
#    return fbd.connect(
#        r"nayhan/3052:C:\Users\nayhan\Documents\PROJETOS AZURE\6- AZURE - REFERENCIAS\REFERENCIAS\BANCO REFERENCIA\BD\REFERENCIAS.FDB",
#        user="SYSDBA",
#        password="masterkey"
#    )
