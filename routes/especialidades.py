from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime

especialidades_bp = Blueprint('especialidades', __name__)

def get_db():
    from app import conn, cur
    return conn, cur

@especialidades_bp.route('/visualizar_especialidades')
def visualizar_especialidades():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("SELECT CODESPECIALIDADE, nome FROM ESPECIALIDADE ORDER BY nome")
    especialidades = cur.fetchall()
    return render_template('visualizar_especialidades.html', especialidades=especialidades)

@especialidades_bp.route('/nova_especialidade', methods=['GET', 'POST'])
def nova_especialidade():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        cur.execute("SELECT 1 FROM  ESPECIALIDADE WHERE NOME= ?", (nome,))
        if cur.fetchone():
            flash("Essa especialidade já está cadastrada.", "error")
            return redirect(url_for('especialidades.nova_especialidade'))
        cur.execute("""
            INSERT INTO ESPECIALIDADE (nome, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?)
        """, (nome, 4, datetime.now()))
        conn.commit()
        flash("Especialidade cadastrada com sucesso!", "success")
        return redirect(url_for('especialidades.visualizar_especialidades'))
    return render_template('nova_especialidade.html')

@especialidades_bp.route('/editar_especialidade/<int:codespecialidade>', methods=['GET', 'POST'])
def editar_especialidade(codespecialidade):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        cur.execute("SELECT 1 FROM  ESPECIALIDADE WHERE NOME= ? AND CODESPECIALIDADE != ?", (nome, codespecialidade))
        if cur.fetchone():
            flash("Essa especialidade já está cadastrada.", "error")
            return redirect(url_for('especialidades.editar_especialidade', codespecialidade=codespecialidade))
        cur.execute("""
            UPDATE ESPECIALIDADE SET
            nome = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
            WHERE CODESPECIALIDADE = ?
        """, (nome, datetime.now(), 4, codespecialidade))
        conn.commit()
        flash("Especialidade atualizada com sucesso!", "success")
        return redirect(url_for('especialidades.visualizar_especialidades'))
    cur.execute("SELECT CODESPECIALIDADE, nome FROM ESPECIALIDADE WHERE CODESPECIALIDADE = ?", (codespecialidade,))
    especialidade = cur.fetchone()
    return render_template('editar_especialidade.html', especialidade=especialidade)

@especialidades_bp.route('/excluir_especialidade/<int:codespecialidade>', methods=['POST'])
def excluir_especialidade(codespecialidade):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    try:
        cur.execute("DELETE FROM ESPECIALIDADE WHERE CODESPECIALIDADE = ?", (codespecialidade,))
        conn.commit()
        flash("Especialidade excluída com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        flash("Erro ao excluir: especialidade está vinculada a outras tabelas.", "error")
    return redirect(url_for('especialidades.visualizar_especialidades'))