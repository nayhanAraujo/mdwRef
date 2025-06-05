from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
from datetime import datetime
from get_db import get_db


linguagens_bp = Blueprint('linguagens', __name__)



@linguagens_bp.route('/visualizar_linguagens')
def visualizar_linguagens():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT CODLINGUAGEM, nome FROM TIPOLINGUAGEM ORDER BY nome")
            linguagens = cur.fetchall()
            return render_template('visualizar_linguagens.html', linguagens=linguagens)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar linguagens: {str(e)}")
        flash("Erro ao carregar as linguagens. Tente novamente mais tarde.", "error")
        return redirect(url_for('linguagens.visualizar_linguagens'))

@linguagens_bp.route('/nova_linguagem', methods=['GET', 'POST'])
def nova_linguagem():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()

        try:
            with get_db() as (conn, cur):
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

        except Exception as e:
            current_app.logger.error(f"Erro ao cadastrar nova linguagem: {str(e)}")
            flash("Erro ao cadastrar a linguagem. Por favor, tente novamente.", "error")
            return redirect(url_for('linguagens.nova_linguagem'))

    return render_template('nova_linguagem.html')

@linguagens_bp.route('/editar_linguagem/<int:CODLINGUAGEM>', methods=['GET', 'POST'])
def editar_linguagem(CODLINGUAGEM):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()

        try:
            with get_db() as (conn, cur):
                cur.execute(
                    "SELECT 1 FROM TIPOLINGUAGEM WHERE nome = ? AND CODLINGUAGEM != ?",
                    (nome, CODLINGUAGEM)
                )
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

        except Exception as e:
            current_app.logger.error(f"Erro ao atualizar linguagem: {str(e)}")
            flash("Erro ao atualizar a linguagem. Por favor, tente novamente.", "error")
            return redirect(url_for('linguagens.editar_linguagem', CODLINGUAGEM=CODLINGUAGEM))

    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT CODLINGUAGEM, nome FROM TIPOLINGUAGEM WHERE CODLINGUAGEM = ?", (CODLINGUAGEM,))
            linguagem = cur.fetchone()

            if not linguagem:
                flash("Linguagem não encontrada.", "error")
                return redirect(url_for('linguagens.visualizar_linguagens'))

            return render_template('editar_linguagem.html', linguagem=linguagem)

    except Exception as e:
        current_app.logger.error(f"Erro ao carregar dados da linguagem: {str(e)}")
        flash("Erro ao carregar os dados da linguagem.", "error")
        return redirect(url_for('linguagens.visualizar_linguagens'))

@linguagens_bp.route('/excluir_linguagem/<int:CODLINGUAGEM>', methods=['POST'])
def excluir_linguagem(CODLINGUAGEM):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            cur.execute("DELETE FROM TIPOLINGUAGEM WHERE CODLINGUAGEM = ?", (CODLINGUAGEM,))
            conn.commit()
            flash("Linguagem excluída com sucesso!", "success")

    except Exception as e:
        current_app.logger.error(f"Erro ao excluir linguagem: {str(e)}")
        flash("Erro ao excluir: linguagem está vinculada a outras tabelas ou ocorreu um problema interno.", "error")

    return redirect(url_for('linguagens.visualizar_linguagens'))