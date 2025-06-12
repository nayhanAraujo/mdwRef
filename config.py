import os
from dotenv import load_dotenv


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class Config:
    GROK_API_KEY = os.environ.get('GROK_API_KEY')

    SECRET_KEY = os.environ.get('SECRET_KEY', 'uma_chave_secreta_padrao_para_desenvolvimento')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads_documentos_academicos') 

if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)