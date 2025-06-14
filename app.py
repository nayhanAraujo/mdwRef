from flask import Flask, session, redirect, url_for, request, send_from_directory, current_app,g
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
from routes.scripts import scripts_bp
from routes.secoes import secoes_bp
from routes.modelos import modelos_bp
from routes.pacotes import pacotes_bp
from routes.grupos import grupos_bp
from routes.agente_referencias   import agente_bp
from routes.codigos_universais import codigos_universais_bp
from routes.autores import autores_bp
from dotenv import load_dotenv  # Adicione este import
from datetime import timedelta

import os
import logging

# Carrega variáveis do .env localmente
if os.path.exists('.env'):
    load_dotenv('.env')
    
# Configurações adap    táveis para local/dev
IS_LOCAL = os.environ.get('FLASK_ENV') == 'development'



def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_segura')
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Verifica se está rodando localmente (desenvolvimento)
    is_local = os.environ.get('FLASK_ENV') == 'development' or os.getenv('FLASK_DEBUG') == '1'
    
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions') if is_local else '/app/sessions'
    app.config['SESSION_FILE_THRESHOLD'] = 500
    app.config['SESSION_COOKIE_SECURE'] = not is_local
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
    app.config['UPLOAD_FOLDER_INTERFACES'] = 'static/uploads/interfaces'
    app.config['UPLOAD_FOLDER_IMPRESSOES'] = 'static/uploads/impressoes'
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/Uploads') if is_local else '/app/uploads'
    app.config['UPLOAD_FOLDER_DOCUMENTOS'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads_documentos_academicos') if is_local else '/app/uploads_documentos_academicos'

    app.config.update(
        SMTP_SERVER='smtp.gmail.com',
        SMTP_PORT=587,
        SMTP_USERNAME='nayhanbsb@gmail.com',
        SMTP_PASSWORD='txkt aiqx qqvk vjdr',
        SMTP_SENDER='nayhanbsb@gmail.com'
    )  
 

    app.config['DB_CONFIG'] = {
            'host': os.environ.get('LOCAL_DB_HOST', '127.0.0.1'),
            'port': os.environ.get('LOCAL_DB_PORT', '3052'),
            'database': os.environ.get('LOCAL_DB_PATH', 'C:\\Users\\nayhan\\Documents\\PROJETOS AZURE\\6- AZURE - REFERENCIAS\\REFERENCIAS\\BD\\REFERENCIAS.FDB'),
            'user': os.environ.get('LOCAL_DB_USER', 'SYSDBA'),
            'password': os.environ.get('LOCAL_DB_PASSWORD', 'masterkey')
        } if is_local else {
            'host': os.environ.get('FIREBIRD_HOST', '127.0.0.1'),
            'port': os.environ.get('FIREBIRD_PORT', '3050'),
            'database': os.environ.get('FIREBIRD_DB', '/app/data/REFERENCIAS.FDB'),
            'user': os.environ.get('FIREBIRD_USER', 'SYSDBA'),
            'password': os.environ.get('FIREBIRD_PASSWORD', 'masterkey')
        }

    try:
            os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            os.makedirs(app.config['UPLOAD_FOLDER_DOCUMENTOS'], exist_ok=True)
    except OSError as e:
            app.logger.error(f"Erro ao criar diretórios: {e}")


    Session(app)

    @app.before_request
    def _open_db_connection():
        """Abre uma conexão para cada request e armazena em flask.g."""
        g.db_conn = conectar()
        g.db_cur = g.db_conn.cursor()

    @app.teardown_appcontext
    def _close_db_connection(exception=None):
        """Fecha a conexão e o cursor ao final do contexto da aplicação."""
        db_cur = g.pop('db_cur', None)
        if db_cur is not None:
            db_cur.close()
        db_conn = g.pop('db_conn', None)
        if db_conn is not None:
            db_conn.close()

    @app.template_filter('basename')
    def basename_filter(path):
        if path:
            return os.path.basename(path)
        return ''

    @app.route('/')
    def index():
        if 'usuario' not in session:
            app.logger.info("Nenhuma sessão encontrada, redirecionando para login")
            return redirect(url_for('auth.login'))
        app.logger.info(f"Sessão encontrada: {session['usuario']}")
        return redirect(url_for('variaveis.home'))

    @app.route('/login')
    def login_redirect():
        app.logger.info("Redirecionando para auth.login")
        return redirect(url_for('auth.login'))

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Processador de contexto para menu
    @app.context_processor
    def inject_menu_links():
        if request.endpoint in ['auth.login', 'auth.forgot_password']:
            return dict(links_menu=[])
        links = [
      
    ('Dashboards', 'variaveis.home', 'speedometer'),  # Painel → velocímetro
    ('Novo Script', 'scripts.novo_script', 'file-earmark-plus'),  # Novo → arquivo com +
    ('Visualizar pacotes', 'scripts.visualizar_scripts', 'box-seam'),  # Visualizar → arquivo com texto
    #('Nova Seção', 'secoes.nova_secao', 'file-earmark-plus'),  # Seções → arquivo com +
    #('Visualizar Seções', 'secoes.visualizar_secoes', 'file-earmark-text'),  
    #('Novo Modo texto', 'modelos.novo_modelo', 'file-earmark-plus'),  # Novo modelo → arquivo com +
    ('Visualizar Modelos', 'modelos.visualizar_modelos', 'file-earmark-text'),  # Visualizar modelo → arquivo com texto
    ('Nova Variável', 'variaveis.nova_variavel', 'clipboard-plus'),  # Nova variável → clipboard +
    #('Nova Fórmula', 'formulas.nova_formula', 'calculator'),  # Fórmula → calculadora
    #('Cadastrar Referência', 'referencias.nova_referencia', 'book-half'),  # Referência → livro meio aberto
    #('Cadastrar Usuário', 'users.novo_usuario', 'person-plus'),  
    #('Visualizar Usuários', 'users.usuarios', 'people'),  
    ('Visualizar Variáveis', 'variaveis.visualizar_variaveis', 'card-list'),  # Lista → cartão com lista
    ('Fórmulas Cadastradas', 'formulas.visualizar_formulas', 'calculator-fill'),  # Calculadora preenchida
    #('Visualizar Unidades', 'unidades.visualizar_unidades', 'rulers'),  
    #('Visualizar Especialidades', 'especialidades.visualizar_especialidades', 'briefcase'),  # Profissões → maleta
    #('Visualizar Linguagens', 'linguagens.visualizar_linguagens', 'translate'),  # Linguagens → ícone de tradução
    ('Gerenciar Classificações', 'variaveis.gerenciar_grupos_classificacoes', 'tags-fill'),  # Classificações → tags
    ('Agentes', 'agente_referencias.dashboard', 'robot'), # Ícone 'robot' ou outro de sua preferência

    #('Códigos Universais', 'codigos_universais.visualizar_codigos_universais', 'qr-code-scan'),  
    ('Biblioteca', 'bibliotecas.biblioteca', 'bookshelf'),  # Biblioteca → prateleira de livros
    #('Pacotes', 'pacotes.visualizar_pacotes', 'box-seam')
    
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
    app.register_blueprint(scripts_bp,url_prefix='/scripts')
    app.register_blueprint(secoes_bp, url_prefix='/secoes') 
    app.register_blueprint(modelos_bp, url_prefix='/modelos')
    app.register_blueprint(codigos_universais_bp, url_prefix='/codigos_universais')  # Adicione esta linha
    app.register_blueprint(pacotes_bp,url_prefix='/pacotes')
    app.register_blueprint(agente_bp,url_prefix='/agente')
    app.register_blueprint(autores_bp, url_prefix='/autores')
    app.register_blueprint(grupos_bp)




    return app

app = create_app()

if __name__ == '__main__':
    # Configuração específica para desenvolvimento local
    os.environ['FLASK_ENV'] = 'development'
    load_dotenv()  # Garante o carregamento das variáveis
    
    #app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)