from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime

linguagens_bp = Blueprint('linguagens', __name__)

def get_db():
    from app import conn, cur
    return conn, cur

@linguagens_bp.route('/visualizar_linguagens')
def visualizar_linguagens():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("SELECT CODLINGUAGEM, nome FROM TIPOLINGUAGEM ORDER BY nome")
    linguagens = cur.fetchall()
    return render_template('visualizar_linguagens.html', linguagens=linguagens)

@linguagens_bp.route('/nova_linguagem', methods=['GET', 'POST'])
def nova_linguagem():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        cur.execute("SELECT 1 FROM TIPOLINGUAGEM WHERE nome = ?", (nome,))
        if cur.fetchone():
            flash("Essa linguagem já está cadastrada.", "error")
            return redirect(url_for('linguagens.nova_linguagem'))
        cur.execute("""
            INSERT INTO TIPOLINGUAGEM (nome)
            VALUES (?)
        """, (nome,))
        conn.commit()
        flash("Linguagem cadastrada com sucesso!", "success")
        return redirect(url_for('linguagens.visualizar_linguagens'))
    return render_template('nova_linguagem.html')

@linguagens_bp.route('/editar_linguagem/<int:CODLINGUAGEM>', methods=['GET', 'POST'])
def editar_linguagem(CODLINGUAGEM):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        cur.execute("SELECT 1 FROM TIPOLINGUAGEM WHERE nome = ? AND CODLINGUAGEM != ?", (nome, CODLINGUAGEM))
        if cur.fetchone():
            flash("Essa linguagem já está cadastrada.", "error")
            return redirect(url_for('linguagens.editar_linguagem', CODLINGUAGEM=CODLINGUAGEM))
        cur.execute("""
            UPDATE TIPOLINGUAGEM SET
            nome = ?
            WHERE CODLINGUAGEM = ?
        """, (nome, CODLINGUAGEM))
        conn.commit()
        flash("Linguagem atualizada com sucesso!", "success")
        return redirect(url_for('linguagens.visualizar_linguagens'))
    cur.execute("SELECT CODLINGUAGEM, nome FROM TIPOLINGUAGEM WHERE CODLINGUAGEM = ?", (CODLINGUAGEM,))
    linguagem = cur.fetchone()
    return render_template('editar_linguagem.html', linguagem=linguagem)

@linguagens_bp.route('/excluir_linguagem/<int:CODLINGUAGEM>', methods=['POST'])
def excluir_linguagem(CODLINGUAGEM):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    try:
        cur.execute("DELETE FROM TIPOLINGUAGEM WHERE CODLINGUAGEM = ?", (CODLINGUAGEM,))
        conn.commit()
        flash("Linguagem excluída com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        flash("Erro ao excluir: linguagem está vinculada a outras tabelas.", "error")
    return redirect(url_for('linguagens.visualizar_linguagens'))