from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from get_db import get_db

grupos_bp = Blueprint('grupos', __name__)

@grupos_bp.route('/grupos_variaveis')
def listar_grupos():
    with get_db() as (conn, cur):
        cur.execute("SELECT CODGRUPO, NOME, DESCRICAO, ATIVO, DTHRULTMODIFICACAO FROM GRUPOS_VARIAVEIS ORDER BY NOME")
        grupos = cur.fetchall()
    return render_template('grupos_variaveis.html', grupos=grupos)

@grupos_bp.route('/novo_grupo', methods=['GET', 'POST'])
def novo_grupo():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = 1 if request.form.get('ativo') else 0
        dthr = datetime.now()
        if not nome:
            flash("Nome do grupo é obrigatório.", "error")
            return redirect(request.url)
        with get_db() as (conn, cur):
            cur.execute("""
                INSERT INTO GRUPOS_VARIAVEIS (NOME, DESCRICAO, ATIVO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?)
            """, (nome, descricao, ativo, dthr))
            conn.commit()
            flash("Grupo criado com sucesso!", "success")
        return redirect(url_for('grupos.listar_grupos'))
    return render_template('novo_grupo.html')

@grupos_bp.route('/editar_grupo/<int:codgrupo>', methods=['GET', 'POST'])
def editar_grupo(codgrupo):
    with get_db() as (conn, cur):
        if request.method == 'POST':
            nome = request.form['nome'].strip()
            descricao = request.form.get('descricao', '').strip()
            ativo = 1 if request.form.get('ativo') else 0
            dthr = datetime.now()
            if not nome:
                flash("Nome do grupo é obrigatório.", "error")
                return redirect(request.url)
            cur.execute("""
                UPDATE GRUPOS_VARIAVEIS 
                SET NOME = ?, DESCRICAO = ?, ATIVO = ?, DTHRULTMODIFICACAO = ?
                WHERE CODGRUPO = ?
            """, (nome, descricao, ativo, dthr, codgrupo))
            conn.commit()
            flash("Grupo atualizado com sucesso!", "success")
            return redirect(url_for('grupos.listar_grupos'))
        cur.execute("SELECT CODGRUPO, NOME, DESCRICAO, ATIVO FROM GRUPOS_VARIAVEIS WHERE CODGRUPO = ?", (codgrupo,))
        grupo = cur.fetchone()
        if not grupo:
            flash("Grupo não encontrado.", "error")
            return redirect(url_for('grupos.listar_grupos'))
    return render_template('editar_grupo.html', grupo=grupo)

@grupos_bp.route('/deletar_grupo/<int:codgrupo>', methods=['POST'])
def deletar_grupo(codgrupo):
    with get_db() as (conn, cur):
        cur.execute("DELETE FROM GRUPOS_VARIAVEIS WHERE CODGRUPO = ?", (codgrupo,))
        conn.commit()
        flash("Grupo deletado com sucesso!", "success")
    return redirect(url_for('grupos.listar_grupos'))