from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import hashlib
from datetime import datetime
from werkzeug.security import check_password_hash
from flask import current_app


auth_bp = Blueprint('auth', __name__)

def get_db():
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        raise Exception("Conexão com o banco de dados não foi inicializada.")
    return conn, cur

# from app import conn, cur  #local
 #   return conn, cur

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificacao = request.form['usuario'].strip().lower()
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        conn, cur = get_db()
        current_app.logger.info(f"Tentando login com usuário: {identificacao}")
        cur.execute("""
            SELECT CODUSUARIO, NOME FROM USUARIO
            WHERE IDENTIFICACAO = ? AND SENHA = ? AND STATUS = -1
        """, (identificacao, senha_hash))
        resultado = cur.fetchone()
        if resultado:
            # Salvar um dicionário com CODUSUARIO e NOME
            session['usuario'] = {
                'codusuario': resultado[0],
                'nome': resultado[1]
            }
            current_app.logger.info(f"Sessão configurada para usuário: {session['usuario']}, sessão: {session}")
            return redirect(url_for('variaveis.home'))
        current_app.logger.error(f"Falha no login: usuário {identificacao} ou senha inválidos")
        return render_template('login.html', erro='Usuário ou senha inválidos.')
    current_app.logger.info("Renderizando página de login")
    return render_template('login.html')

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    conn, cur = get_db()
    if request.method == 'POST':
        identificacao = request.form['identificacao'].strip().lower()
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        cur.execute("SELECT 1 FROM USUARIO WHERE IDENTIFICACAO = ?", (identificacao,))
        if not cur.fetchone():
            flash("Identificação não encontrada.", "error")
            return redirect(url_for('auth.forgot_password'))
        if new_password != confirm_password:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for('auth.forgot_password'))
        senha_criptografada = hashlib.sha256(new_password.encode()).hexdigest()
        cur.execute("""
            UPDATE USUARIO SET SENHA = ?, DTHRULTMODIFICACAO = ?
            WHERE IDENTIFICACAO = ?
        """, (senha_criptografada, datetime.now(), identificacao))
        conn.commit()
        flash("Senha alterada com sucesso! Faça login com a nova senha.", "success")
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')

@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('auth.login'))