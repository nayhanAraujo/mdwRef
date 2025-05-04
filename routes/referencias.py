from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from datetime import datetime
import os
import uuid

referencias_bp = Blueprint('referencias', __name__)

def get_db():
    #from app import conn, cur
    #return conn, cur
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        raise Exception("Conexão com o banco de dados não foi inicializada.")
    return conn, cur

@referencias_bp.route('/nova_referencia', methods=['GET', 'POST'])
def nova_referencia():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        autor = request.form['autor']
        ano = request.form['ano']
        cur.execute("""
            INSERT INTO REFERENCIA (AUTOR, ANO, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?)
            RETURNING CODREFERENCIA
        """, (autor, ano, 4, datetime.now()))
        codreferencia = cur.fetchone()[0]
        conn.commit()
        flash("Referência cadastrada com sucesso!", "success")
        return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
    return render_template('nova_referencia.html')

@referencias_bp.route('/visualizar_referencias')
def visualizar_referencias():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("SELECT CODREFERENCIA, AUTOR, ANO FROM REFERENCIA ORDER BY ANO DESC")
    referencias = cur.fetchall()
    return render_template('visualizar_referencias.html', referencias=referencias)

@referencias_bp.route('/editar_referencia/<int:codreferencia>', methods=['GET', 'POST'])
def editar_referencia(codreferencia):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        autor = request.form['autor']
        ano = request.form['ano']
        cur.execute("""
            UPDATE REFERENCIA SET
            AUTOR = ?, ANO = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
            WHERE CODREFERENCIA = ?
        """, (autor, ano, datetime.now(), 4, codreferencia))
        conn.commit()
        flash("Referência atualizada com sucesso!", "success")
        return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
    cur.execute("SELECT CODREFERENCIA, AUTOR, ANO FROM REFERENCIA WHERE CODREFERENCIA = ?", (codreferencia,))
    referencia = cur.fetchone()
    return render_template('editar_referencia.html', referencia=referencia)

@referencias_bp.route('/excluir_referencia/<int:codreferencia>', methods=['POST'])
def excluir_referencia(codreferencia):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    try:
        # Excluir arquivos associados
        cur.execute("SELECT CAMINHO FROM ANEXOS WHERE CODREFERENCIA = ?", (codreferencia,))
        anexos = cur.fetchall()
        for anexo in anexos:
            caminho = anexo[0]
            if caminho and os.path.exists(caminho):
                os.remove(caminho)
        cur.execute("DELETE FROM ANEXOS WHERE CODREFERENCIA = ?", (codreferencia,))
        cur.execute("DELETE FROM REFERENCIA WHERE CODREFERENCIA = ?", (codreferencia,))
        conn.commit()
        flash("Referência e anexos vinculados excluídos com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        flash("Erro ao excluir: referência está vinculada a outras tabelas.", "error")
    return redirect(url_for('referencias.visualizar_referencias'))

@referencias_bp.route('/visualizar_anexos/<int:codreferencia>', methods=['GET', 'POST'])
def visualizar_anexos(codreferencia):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        descricao = request.form['descricao']
        nome = request.form['nome']
        link = request.form['link']
        caminho = None
        if 'arquivo' in request.files:
            arquivo = request.files['arquivo']
            if arquivo and arquivo.filename:
                extensao = os.path.splitext(arquivo.filename)[1].lower()
                if extensao != '.pdf':
                    flash("Apenas arquivos PDF são permitidos.", "error")
                    return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
                nome_arquivo = f"{uuid.uuid4()}{extensao}"
                caminho = os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo)
                arquivo.save(caminho)
        cur.execute("""
            INSERT INTO ANEXOS (CODREFERENCIA, DESCRICAO, NOME, LINK, CAMINHO, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (codreferencia, descricao, nome, link, caminho, 4, datetime.now()))
        conn.commit()
        flash("Anexo adicionado com sucesso!", "success")
        return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
    cur.execute("SELECT CODREFERENCIA, AUTOR, ANO FROM REFERENCIA WHERE CODREFERENCIA = ?", (codreferencia,))
    referencia = cur.fetchone()
    cur.execute("SELECT CODANEXO, DESCRICAO, NOME, LINK, CAMINHO FROM ANEXOS WHERE CODREFERENCIA = ?", (codreferencia,))
    anexos = cur.fetchall()
    return render_template('visualizar_anexos.html', referencia=referencia, anexos=anexos)

@referencias_bp.route('/editar_anexo/<int:codanexo>', methods=['GET', 'POST'])
def editar_anexo(codanexo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        descricao = request.form['descricao']
        nome = request.form['nome']
        link = request.form['link']
        cur.execute("SELECT CODREFERENCIA, CAMINHO FROM ANEXOS WHERE CODANEXO = ?", (codanexo,))
        result = cur.fetchone()
        codreferencia, caminho_antigo = result
        caminho = caminho_antigo
        if 'arquivo' in request.files:
            arquivo = request.files['arquivo']
            if arquivo and arquivo.filename:
                extensao = os.path.splitext(arquivo.filename)[1].lower()
                if extensao != '.pdf':
                    flash("Apenas arquivos PDF são permitidos.", "error")
                    return redirect(url_for('referencias.editar_anexo', codanexo=codanexo))
                if caminho_antigo and os.path.exists(caminho_antigo):
                    os.remove(caminho_antigo)
                nome_arquivo = f"{uuid.uuid4()}{extensao}"
                caminho = os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo)
                arquivo.save(caminho)
        cur.execute("""
            UPDATE ANEXOS SET
            DESCRICAO = ?, NOME = ?, LINK = ?, CAMINHO = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
            WHERE CODANEXO = ?
        """, (descricao, nome, link, caminho, datetime.now(), 4, codanexo))
        conn.commit()
        flash("Anexo atualizado com sucesso!", "success")
        return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
    cur.execute("SELECT CODANEXO, CODREFERENCIA, DESCRICAO, NOME, LINK, CAMINHO FROM ANEXOS WHERE CODANEXO = ?", (codanexo,))
    anexo = cur.fetchone()
    return render_template('editar_anexo.html', anexo=anexo)

@referencias_bp.route('/excluir_anexo/<int:codanexo>', methods=['POST'])
def excluir_anexo(codanexo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("SELECT CODREFERENCIA, CAMINHO FROM ANEXOS WHERE CODANEXO = ?", (codanexo,))
    result = cur.fetchone()
    codreferencia, caminho = result
    if caminho and os.path.exists(caminho):
        os.remove(caminho)
    cur.execute("DELETE FROM ANEXOS WHERE CODANEXO = ?", (codanexo,))
    conn.commit()
    flash("Anexo excluído com sucesso!", "success")
    return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))