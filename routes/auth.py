from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import hashlib
from datetime import datetime
from get_db import get_db
from werkzeug.security import check_password_hash
from flask import current_app

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificacao = request.form['usuario'].strip().lower()
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        with get_db() as (conn, cur):
            current_app.logger.info(f"Tentando login com usuário: {identificacao}")
            cur.execute("""
                SELECT CODUSUARIO, NOME, PERFIL FROM USUARIO
                WHERE IDENTIFICACAO = ? AND SENHA = ? AND STATUS = -1
            """, (identificacao, senha_hash))
            resultado = cur.fetchone()
            if resultado:
                # Salvar um dicionário com CODUSUARIO, NOME e PERFIL
                session['usuario'] = {
                    'codusuario': resultado[0],
                    'nome': resultado[1],
                    'role': resultado[2] 
                }
                current_app.logger.info(f"Sessão configurada para usuário: {session['usuario']}, sessão: {session}")
                return redirect(url_for('bibliotecas.biblioteca'))
            current_app.logger.error(f"Falha no login: usuário {identificacao} ou senha inválidos")
            return render_template('login.html', erro='Usuário ou senha inválidos.')
    current_app.logger.info("Renderizando página de login")
    return render_template('login.html')

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identificacao = request.form['identificacao'].strip().lower()
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        with get_db() as (conn, cur):
            cur.execute("SELECT 1 FROM USUARIO WHERE IDENTIFICACAO = ?", (identificacao,))
            if not cur.fetchone():
                flash("Identificação não encontrada.", "error")
                return redirect(url_for('auth.forgot_password'))
            
            if new_password != confirm_password:
                flash("As senhas não coincidem.", "error")
                return redirect(url_for('auth.forgot_password'))
            
            senha_criptografada = hashlib.sha256(new_password.encode()).hexdigest()
            try:
                cur.execute("""
                    UPDATE USUARIO SET SENHA = ?, DTHRULTMODIFICACAO = ?
                    WHERE IDENTIFICACAO = ?
                """, (senha_criptografada, datetime.now(), identificacao))
                conn.commit()
                flash("Senha alterada com sucesso! Faça login com a nova senha.", "success")
                return redirect(url_for('auth.login'))
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"Erro ao atualizar senha para usuário {identificacao}: {str(e)}")
                flash(f"Erro ao alterar senha: {str(e)}", "error")
                return redirect(url_for('auth.forgot_password'))
    
    return render_template('forgot_password.html')

@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('auth.login'))