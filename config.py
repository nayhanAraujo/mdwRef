import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
# Isso é útil especialmente para desenvolvimento local.
# Em produção, as variáveis de ambiente geralmente são configuradas diretamente no servidor.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class Config:
    GROK_API_KEY = os.environ.get('GROK_API_KEY')
    # Configurações do Firebird já estão sendo carregadas em database.py
    # via current_app.config['DB_CONFIG'] em app.py.
    # Podemos manter assim ou centralizar aqui.
    # Por agora, vamos assumir que app.py lida com isso.

    # Outras configurações do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'uma_chave_secreta_padrao_para_desenvolvimento')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads_documentos_academicos') # Nova pasta para PDFs acadêmicos

    # ... outras configurações ...

# Certifique-se de que a pasta de upload para documentos acadêmicos existe
if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)