from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from get_db import get_db

autores_bp = Blueprint('autores', __name__)

@autores_bp.route('/visualizar_autores')
def visualizar_autores():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT a.CODAUTOR, a.NOME, a.ABREVIACAO, t.DESCRICAO FROM AUTORES a LEFT JOIN TIPO_AUTOR t ON a.CODTIPO = t.CODTIPO ORDER BY a.NOME"
            )
            autores = cur.fetchall()
            return render_template('visualizar_autores.html', autores=autores)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar autores: {str(e)}")
        flash("Erro ao carregar autores.", "error")
        return redirect(url_for('bibliotecas.biblioteca'))

@autores_bp.route('/novo_autor', methods=['GET', 'POST'])
def novo_autor():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        abreviacao = request.form.get('abreviacao', '').strip() or None
        orcid = request.form.get('orcid', '').strip() or None
        pais = request.form.get('pais', '').strip() or None
        url = request.form.get('url', '').strip() or None
        codtipo = request.form.get('codtipo') or None

        try:
            with get_db() as (conn, cur):
                cur.execute("SELECT 1 FROM AUTORES WHERE NOME = ?", (nome,))
                if cur.fetchone():
                    flash("Autor já cadastrado.", "error")
                    return redirect(url_for('autores.novo_autor'))

                cur.execute(
                    """
                    INSERT INTO AUTORES (NOME, ABREVIACAO, ORCID, PAIS, URL, CODTIPO)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (nome, abreviacao, orcid, pais, url, codtipo)
                )
                conn.commit()
                flash("Autor cadastrado com sucesso!", "success")
                return redirect(url_for('autores.visualizar_autores'))
        except Exception as e:
            current_app.logger.error(f"Erro ao cadastrar autor: {str(e)}")
            flash("Erro ao cadastrar autor.", "error")
            return redirect(url_for('autores.novo_autor'))

    return render_template('novo_autor.html')

@autores_bp.route('/editar_autor/<int:codautor>', methods=['GET', 'POST'])
def editar_autor(codautor):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        abreviacao = request.form.get('abreviacao', '').strip() or None
        orcid = request.form.get('orcid', '').strip() or None
        pais = request.form.get('pais', '').strip() or None
        url = request.form.get('url', '').strip() or None
        codtipo = request.form.get('codtipo') or None

        try:
            with get_db() as (conn, cur):
                cur.execute(
                    "SELECT 1 FROM AUTORES WHERE NOME = ? AND CODAUTOR != ?",
                    (nome, codautor)
                )
                if cur.fetchone():
                    flash("Outro autor com este nome já existe.", "error")
                    return redirect(url_for('autores.editar_autor', codautor=codautor))

                cur.execute(
                    """
                    UPDATE AUTORES SET NOME=?, ABREVIACAO=?, ORCID=?, PAIS=?, URL=?, CODTIPO=? WHERE CODAUTOR=?
                    """,
                    (nome, abreviacao, orcid, pais, url, codtipo, codautor)
                )
                conn.commit()
                flash("Autor atualizado com sucesso!", "success")
                return redirect(url_for('autores.visualizar_autores'))
        except Exception as e:
            current_app.logger.error(f"Erro ao atualizar autor: {str(e)}")
            flash("Erro ao atualizar autor.", "error")
            return redirect(url_for('autores.editar_autor', codautor=codautor))

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT CODAUTOR, NOME, ABREVIACAO, ORCID, PAIS, URL, CODTIPO FROM AUTORES WHERE CODAUTOR = ?",
                (codautor,)
            )
            autor = cur.fetchone()
            return render_template('editar_autor.html', autor=autor)
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar autor: {str(e)}")
        flash("Erro ao carregar autor.", "error")
        return redirect(url_for('autores.visualizar_autores'))

@autores_bp.route('/excluir_autor/<int:codautor>', methods=['POST'])
def excluir_autor(codautor):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            cur.execute("DELETE FROM AUTORES WHERE CODAUTOR = ?", (codautor,))
            conn.commit()
            flash("Autor excluído com sucesso!", "success")
    except Exception as e:
        current_app.logger.error(f"Erro ao excluir autor: {str(e)}")
        flash("Erro ao excluir autor.", "error")
    return redirect(url_for('autores.visualizar_autores'))

@autores_bp.route('/vincular_autores/<int:codreferencia>', methods=['GET', 'POST'])
def vincular_autores(codreferencia):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    with get_db() as (conn, cur):
        if request.method == 'POST':
            autores = request.form.getlist('autores[]')
            try:
                cur.execute("DELETE FROM REFERENCIA_AUTORES WHERE CODREFERENCIA = ?", (codreferencia,))
                for codautor in autores:
                    cur.execute(
                        "INSERT INTO REFERENCIA_AUTORES (CODREFERENCIA, CODAUTOR) VALUES (?, ?)",
                        (codreferencia, codautor)
                    )
                conn.commit()
                flash("Autores vinculados com sucesso!", "success")
                return redirect(url_for('referencias.visualizar_referencias'))
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"Erro ao vincular autores: {str(e)}")
                flash("Erro ao vincular autores.", "error")
                return redirect(url_for('autores.vincular_autores', codreferencia=codreferencia))

        cur.execute("SELECT TITULO FROM REFERENCIA WHERE CODREFERENCIA = ?", (codreferencia,))
        ref = cur.fetchone()
        if not ref:
            flash("Referência não encontrada.", "error")
            return redirect(url_for('referencias.visualizar_referencias'))
        titulo_ref = ref[0]

        cur.execute("SELECT CODAUTOR FROM REFERENCIA_AUTORES WHERE CODREFERENCIA = ?", (codreferencia,))
        autores_associados = [row[0] for row in cur.fetchall()]

        cur.execute("SELECT CODAUTOR, NOME, ABREVIACAO FROM AUTORES ORDER BY NOME")
        autores = cur.fetchall()

        return render_template('vincular_autores.html', codreferencia=codreferencia, titulo_ref=titulo_ref, autores=autores, autores_associados=autores_associados)
