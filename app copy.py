from flask import Flask, session, redirect, url_for, request, send_from_directory
from flask_session import Session
from database import conectar
from routes.auth import auth_bp
from routes.users import users_bp
from routes.variaveis import variaveis_bp
from routes.formulas import formulas_bp
from routes.referencias import referencias_bp
from routes.uploads import uploads_bp
from routes.bibliotecas import biblioteca_pb
from routes.unidades import unidades_bp
from routes.especialidades import especialidades_bp
from routes.linguagens import linguagens_bp
import os
import logging

def create_app():
    app = Flask(__name__)
    
    # Configuração básica
    app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_segura')
    
    # Configuração de logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()  # Log para stdout (capturado pelo Fly.io)
        ]
    )
    
    # Configuração de sessão
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_FILE_DIR'] = '/app/sessions'  # Diretório no container
    app.config['SESSION_FILE_THRESHOLD'] = 500
    
    # Configuração do diretório de upload
    app.config['UPLOAD_FOLDER'] = '/app/uploads'
    
    # Inicializar extensões
    Session(app)
    
    # Criar diretórios necessários
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Inicialização da conexão com o banco de dados
    @app.before_first_request
    def initialize_database():
        try:
            app.logger.info("Inicializando conexão com o banco de dados...")
            app.config['db_conn'] = conectar()
            app.logger.info("Conexão com o banco estabelecida com sucesso!")
        except Exception as e:
            app.logger.error(f"Erro ao conectar ao banco: {e}")
            raise
    
    # Filtro para extrair o nome do arquivo do caminho
    @app.template_filter('basename')
    def basename_filter(path):
        if path:
            return os.path.basename(path)
        return ''
    
    # Rotas básicas
    @app.route('/')
    def index():
        if 'usuario' not in session:
            return redirect(url_for('auth.login'))
        return redirect(url_for('variaveis.home'))
    
    @app.route('/login')
    def login_redirect():
        return redirect(url_for('auth.login'))
    
    # Rota para servir arquivos enviados
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    # Processador de contexto para menu
    @app.context_processor
    def inject_menu_links():
        if request.endpoint in ['auth.login', 'auth.forgot_password']:
            return dict(links_menu=[])
        links = [
            ('Início', 'variaveis.home', 'house'),
            ('Nova Variável', 'variaveis.nova_variavel', 'plus-circle'),
            ('Nova Fórmula', 'formulas.nova_formula', 'calculator'),
            ('Cadastrar Referência', 'referencias.nova_referencia', 'book'),
            ('Cadastrar Usuário', 'users.novo_usuario', 'person-plus'),
            ('Visualizar Usuários', 'users.usuarios', 'people-fill'),
            ('Fórmulas Cadastradas', 'formulas.visualizar_formulas', 'calculator-fill'),
            ('Visualizar Variáveis', 'variaveis.visualizar_variaveis', 'card-list'),
            ('Visualizar Unidades', 'unidades.visualizar_unidades', 'speedometer2'),
            ('Visualizar Especialidades', 'especialidades.visualizar_especialidades', 'briefcase-fill'),
            ('Visualizar Linguagens', 'linguagens.visualizar_linguagens', 'translate'),
            ('Biblioteca', 'bibliotecas.biblioteca', 'collection'),
        ]
        return dict(links_menu=links)
    
    # Registrar Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(variaveis_bp, url_prefix='/variaveis')
    app.register_blueprint(formulas_bp, url_prefix='/formulas')
    app.register_blueprint(referencias_bp, url_prefix='/referencias')
    app.register_blueprint(uploads_bp, url_prefix='/uploads')
    app.register_blueprint(biblioteca_pb, url_prefix='/bibliotecas')
    app.register_blueprint(unidades_bp, url_prefix='/unidades')
    app.register_blueprint(especialidades_bp, url_prefix='/especialidades')
    app.register_blueprint(linguagens_bp, url_prefix='/linguagens')
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)