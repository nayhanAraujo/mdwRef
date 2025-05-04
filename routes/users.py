from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
import hashlib
from datetime import datetime

users_bp = Blueprint('users', __name__)

def get_db():
    #from app import conn, cur
    #return conn, cur
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        raise Exception("Conexão com o banco de dados não foi inicializada.")
    return conn, cur

@users_bp.route('/novo_usuario', methods=['GET', 'POST'])
def novo_usuario():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        identificacao = request.form['identificacao'].strip().lower()
        senha = request.form['senha']
        perfil = request.form['perfil']
        status = int(request.form['status'])
        ucaseNome = nome
        cur.execute("SELECT 1 FROM USUARIO WHERE IDENTIFICACAO = ?", (identificacao,))
        if cur.fetchone():
            flash("Esse login já está em uso.", "error")
            return redirect(url_for('users.novo_usuario'))
        senha_criptografada = hashlib.sha256(senha.encode()).hexdigest()
        cur.execute("""
            INSERT INTO USUARIO (NOME, IDENTIFICACAO, UCASE_NOME, SENHA, PERFIL, STATUS, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nome, identificacao, ucaseNome, senha_criptografada, perfil, status, datetime.now()))
        conn.commit()
        flash("Usuário cadastrado com sucesso!", "success")
        return redirect(url_for('variables.home'))
    return render_template('novo_usuario.html')

@users_bp.route('/editar_usuario/<int:codusuario>', methods=['GET', 'POST'])
def editar_usuario(codusuario):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        identificacao = request.form['identificacao'].strip().lower()
        perfil = request.form['perfil']
        cur.execute("""
            UPDATE USUARIO SET NOME = ?, IDENTIFICACAO = ?, PERFIL = ?
            WHERE CODUSUARIO = ?
        """, (nome, identificacao, perfil, codusuario))
        conn.commit()
        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for('users.usuarios'))
    cur.execute("SELECT NOME, IDENTIFICACAO, PERFIL FROM USUARIO WHERE CODUSUARIO = ?", (codusuario,))
    usuario = cur.fetchone()
    return render_template('editar_usuario.html', codusuario=codusuario, usuario=usuario)

@users_bp.route('/excluir_usuario/<int:codusuario>', methods=['POST'])
def excluir_usuario(codusuario):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("DELETE FROM USUARIO WHERE CODUSUARIO = ?", (codusuario,))
    conn.commit()
    flash("Usuário excluído com sucesso!", "success")
    return redirect(url_for('users.usuarios'))

@users_bp.route('/visualizar_usuarios')
def usuarios():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("SELECT CODUSUARIO, NOME, IDENTIFICACAO, PERFIL FROM USUARIO ORDER BY NOME")
    usuarios = cur.fetchall()
    return render_template('visualizar_usuarios.html', usuarios=usuarios)