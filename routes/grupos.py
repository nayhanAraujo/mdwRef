from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
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






@grupos_bp.route('/associar_grupos', methods=['GET'])
def associar_grupos():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    with get_db() as (conn, cur):
        # Variáveis ainda não associadas a nenhum grupo
        cur.execute("""
            SELECT V.CODVARIAVEL, V.NOME, V.VARIAVEL
            FROM VARIAVEIS V
            WHERE V.CODGRUPO IS NULL
        """)
        variaveis_sem_grupo = cur.fetchall()

        # Grupos cadastrados
        cur.execute("SELECT CODGRUPO, NOME FROM GRUPOS_VARIAVEIS ORDER BY NOME")
        grupos = cur.fetchall()

        # Variáveis por grupo
        variaveis_por_grupo = {}
        for grupo in grupos:
            cur.execute("""
                SELECT CODVARIAVEL, NOME, VARIAVEL
                FROM VARIAVEIS
                WHERE CODGRUPO = ?
            """, (grupo[0],))
            variaveis_por_grupo[grupo[0]] = cur.fetchall()

    return render_template(
        'associar_grupos.html',
        variaveis_sem_grupo=variaveis_sem_grupo,
        grupos=grupos,
        variaveis_por_grupo=variaveis_por_grupo
    )

@grupos_bp.route('/atualizar_grupo_variavel', methods=['POST'])
def atualizar_grupo_variavel():
    if 'usuario' not in session:
        return jsonify({"success": False, "message": "Usuário não autenticado"}), 401

    data = request.get_json()
    codvariavel = data.get('codvariavel')
    codgrupo = data.get('codgrupo')

    if not codvariavel:
        return jsonify({"success": False, "message": "Código da variável é obrigatório"}), 400

    try:
        codgrupo = int(codgrupo) if codgrupo else None
        codvariavel = int(codvariavel)

        with get_db() as (conn, cur):
            cur.execute(
                "UPDATE VARIAVEIS SET CODGRUPO = ?, DTHRULTMODIFICACAO = ? WHERE CODVARIAVEL = ?",
                (codgrupo, datetime.now(), codvariavel)
            )
            conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
