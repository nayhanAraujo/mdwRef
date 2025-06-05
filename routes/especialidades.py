from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
from datetime import datetime
from get_db import get_db


especialidades_bp = Blueprint('especialidades', __name__)



@especialidades_bp.route('/visualizar_especialidades')
def visualizar_especialidades():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT CODESPECIALIDADE, nome FROM ESPECIALIDADE ORDER BY nome")
            especialidades = cur.fetchall()
            return render_template('visualizar_especialidades.html', especialidades=especialidades)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar especialidades: {str(e)}")
        flash("Erro ao carregar as especialidades. Tente novamente mais tarde.", "error")
        return redirect(url_for('especialidades.visualizar_especialidades'))

@especialidades_bp.route('/nova_especialidade', methods=['GET', 'POST'])
def nova_especialidade():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()

        if not nome:
            flash("O campo Nome é obrigatório.", "error")
            return redirect(request.url)

        try:
            with get_db() as (conn, cur):
                cur.execute("SELECT 1 FROM ESPECIALIDADE WHERE NOME = ?", (nome,))
                if cur.fetchone():
                    flash("Essa especialidade já está cadastrada.", "error")
                    return redirect(request.url)

                cur.execute("""
                    INSERT INTO ESPECIALIDADE (nome, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?)
                """, (nome, 4, datetime.now()))

                conn.commit()
                flash("Especialidade cadastrada com sucesso!", "success")
                return redirect(url_for('especialidades.visualizar_especialidades'))

        except Exception as e:
            current_app.logger.error(f"Erro ao cadastrar nova especialidade: {str(e)}")
            flash("Erro ao cadastrar a especialidade. Por favor, tente novamente.", "error")
            return redirect(request.url)

    return render_template('nova_especialidade.html')

@especialidades_bp.route('/editar_especialidade/<int:codespecialidade>', methods=['GET', 'POST'])
def editar_especialidade(codespecialidade):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()

        if not nome:
            flash("O campo Nome é obrigatório.", "error")
            return redirect(request.url)

        try:
            with get_db() as (conn, cur):
                cur.execute(
                    "SELECT 1 FROM ESPECIALIDADE WHERE NOME = ? AND CODESPECIALIDADE != ?",
                    (nome, codespecialidade)
                )
                if cur.fetchone():
                    flash("Essa especialidade já está cadastrada.", "error")
                    return redirect(request.url)

                cur.execute("""
                    UPDATE ESPECIALIDADE SET
                    nome = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
                    WHERE CODESPECIALIDADE = ?
                """, (nome, datetime.now(), 4, codespecialidade))

                conn.commit()
                flash("Especialidade atualizada com sucesso!", "success")
                return redirect(url_for('especialidades.visualizar_especialidades'))

        except Exception as e:
            current_app.logger.error(f"Erro ao atualizar especialidade CODESPECIALIDADE={codespecialidade}: {str(e)}")
            flash("Erro ao atualizar a especialidade. Por favor, tente novamente.", "error")
            return redirect(request.url)

    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT CODESPECIALIDADE, nome FROM ESPECIALIDADE WHERE CODESPECIALIDADE = ?", (codespecialidade,))
            especialidade = cur.fetchone()

            if not especialidade:
                flash("Especialidade não encontrada.", "error")
                return redirect(url_for('especialidades.visualizar_especialidades'))

            return render_template('editar_especialidade.html', especialidade=especialidade)

    except Exception as e:
        current_app.logger.error(f"Erro ao carregar dados da especialidade: {str(e)}")
        flash("Erro ao carregar os dados da especialidade.", "error")
        return redirect(url_for('especialidades.visualizar_especialidades'))

@especialidades_bp.route('/excluir_especialidade/<int:codespecialidade>', methods=['POST'])
def excluir_especialidade(codespecialidade):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            cur.execute("DELETE FROM ESPECIALIDADE WHERE CODESPECIALIDADE = ?", (codespecialidade,))
            conn.commit()
            flash("Especialidade excluída com sucesso!", "success")

    except Exception as e:
        current_app.logger.error(f"Erro ao excluir especialidade CODESPECIALIDADE={codespecialidade}: {str(e)}")
        flash("Erro ao excluir: especialidade está vinculada a outras tabelas ou ocorreu um problema interno.", "error")

    return redirect(url_for('especialidades.visualizar_especialidades'))