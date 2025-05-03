from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime

unidades_bp = Blueprint('unidades', __name__)

def get_db():
    from app import conn, cur
    return conn, cur

@unidades_bp.route('/visualizar_unidades')
def visualizar_unidades():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("SELECT CODUNIDADEMEDIDA, DESCRICAO, STATUS FROM UNIDADEMEDIDA ORDER BY DESCRICAO")
    unidades = cur.fetchall()
    return render_template('visualizar_unidades.html', unidades=unidades)

@unidades_bp.route('/nova_unidade', methods=['GET', 'POST'])
def nova_unidade():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        descricao = request.form['descricao']
        status = int(request.form['status'])
        cur.execute("SELECT 1 FROM UNIDADEMEDIDA WHERE DESCRICAO = ?", (descricao,))
        if cur.fetchone():
            flash("Essa unidade de medida já está cadastrada.", "error")
            return redirect(url_for('unidades.nova_unidade'))
        cur.execute("""
            INSERT INTO UNIDADEMEDIDA (DESCRICAO, STATUS, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?)
        """, (descricao, status, 4, datetime.now()))
        conn.commit()
        flash("Unidade de medida cadastrada com sucesso!", "success")
        return redirect(url_for('unidades.visualizar_unidades'))
    return render_template('nova_unidade.html')

@unidades_bp.route('/editar_unidade/<int:codunidademedida>', methods=['GET', 'POST'])
def editar_unidade(codunidademedida):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        descricao = request.form['descricao']
        status = int(request.form['status'])
        cur.execute("SELECT 1 FROM UNIDADEMEDIDA WHERE DESCRICAO = ? AND CODUNIDADEMEDIDA != ?", (descricao, codunidademedida))
        if cur.fetchone():
            flash("Essa unidade de medida já está cadastrada.", "error")
            return redirect(url_for('unidades.editar_unidade', codunidademedida=codunidademedida))
        cur.execute("""
            UPDATE UNIDADEMEDIDA SET
            DESCRICAO = ?, STATUS = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
            WHERE CODUNIDADEMEDIDA = ?
        """, (descricao, status, datetime.now(), 4, codunidademedida))
        conn.commit()
        flash("Unidade de medida atualizada com sucesso!", "success")
        return redirect(url_for('unidades.visualizar_unidades'))
    cur.execute("SELECT CODUNIDADEMEDIDA, DESCRICAO, STATUS FROM UNIDADEMEDIDA WHERE CODUNIDADEMEDIDA = ?", (codunidademedida,))
    unidade = cur.fetchone()
    return render_template('editar_unidade.html', unidade=unidade)

@unidades_bp.route('/excluir_unidade/<int:codunidademedida>', methods=['POST'])
def excluir_unidade(codunidademedida):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    try:
        cur.execute("DELETE FROM UNIDADEMEDIDA WHERE CODUNIDADEMEDIDA = ?", (codunidademedida,))
        conn.commit()
        flash("Unidade de medida excluída com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        flash("Erro ao excluir: unidade de medida está vinculada a outras tabelas.", "error")
    return redirect(url_for('unidades.visualizar_unidades'))