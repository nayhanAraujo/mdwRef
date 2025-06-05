from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime
from collections import namedtuple
from get_db import get_db


pacotes_bp = Blueprint('pacotes', __name__)

@pacotes_bp.route('/pacotes/novo_pacote', methods=['GET', 'POST'])
def novo_pacote():
    if 'usuario' not in session:
        current_app.logger.error("Sessão de usuário não encontrada.")
        return redirect(url_for('auth.login'))

    codusuario = session['usuario']['codusuario']

    if request.method == 'POST':
        nome = request.form.get('nome').strip()
        descricao = request.form.get('descricao', '').strip() or None
        scriptlaudos = request.form.getlist('scriptlaudos[]')
        dthrultmodificacao = datetime.now()

        try:
            if not nome:
                flash('Nome do pacote é obrigatório.', 'error')
                return redirect(request.url)

            with get_db() as (conn, cur):
                # Verificar se o nome já existe
                cur.execute("SELECT 1 FROM PACOTES WHERE UPPER(NOME) = UPPER(?)", (nome,))
                if cur.fetchone():
                    flash("Já existe um pacote com esse nome.", "error")
                    return redirect(request.url)

                # Inserir pacote e obter CODPACOTE
                cur.execute("""
                    INSERT INTO PACOTES (NOME, DESCRICAO, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?)
                    RETURNING CODPACOTE
                """, (nome, descricao, codusuario, dthrultmodificacao))
                codpacote = cur.fetchone()[0]
                current_app.logger.info(f"Pacote CODPACOTE={codpacote} criado.")

                # Vincular scripts de laudo
                for codscriptlaudo in scriptlaudos:
                    if codscriptlaudo:
                        cur.execute("""
                            UPDATE SCRIPTLAUDO SET CODPACOTE = ?
                            WHERE CODSCRIPTLAUDO = ?
                        """, (codpacote, codscriptlaudo))
                current_app.logger.info(f"Atualizados {len(scriptlaudos)} scripts para CODPACOTE={codpacote}")

                conn.commit()
                flash("Pacote criado com sucesso!", "success")
                return redirect(url_for('pacotes.visualizar_pacotes'))

        except Exception as e:
            current_app.logger.error(f"Erro ao criar pacote: {str(e)}")
            flash(f"Erro ao criar pacote: {str(e)}", "error")
            return redirect(request.url)

    try:
        with get_db() as (conn, cur):
            # Carregar scripts disponíveis (sem pacote vinculado)
            cur.execute("SELECT CODSCRIPTLAUDO, NOME FROM SCRIPTLAUDO WHERE CODPACOTE IS NULL ORDER BY NOME")
            scriptlaudos = cur.fetchall()
            return render_template('novo_pacote.html', scriptlaudos=scriptlaudos)

    except Exception as e:
        current_app.logger.error(f"Erro ao carregar formulário de novo pacote: {str(e)}")
        flash(f"Erro ao carregar formulário: {str(e)}", "error")
        return redirect(url_for('pacotes.visualizar_pacotes'))

@pacotes_bp.route('/pacotes/visualizar_pacotes')
def visualizar_pacotes():
    if 'usuario' not in session:
        current_app.logger.error("Sessão de usuário não encontrada.")
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT CODPACOTE, NOME, DESCRICAO, DTHRULTMODIFICACAO
                FROM PACOTES
                ORDER BY NOME
            """)
            Pacote = namedtuple('Pacote', ['codpacote', 'nome', 'descricao', 'dthrultmodificacao'])
            pacotes = [Pacote(*row) for row in cur.fetchall()]
            current_app.logger.info(f"Carregados {len(pacotes)} pacotes.")
            return render_template('visualizar_pacotes.html', pacotes=pacotes)

    except Exception as e:
        current_app.logger.error(f"Erro ao visualizar pacotes: {str(e)}")
        flash(f"Erro ao visualizar pacotes: {str(e)}", "error")
        return redirect(url_for('bibliotecas.biblioteca'))

@pacotes_bp.route('/pacotes/editar_pacote/<int:codpacote>', methods=['GET', 'POST'])
def editar_pacote(codpacote):
    if 'usuario' not in session:
        current_app.logger.error("Sessão de usuário não encontrada.")
        return redirect(url_for('auth.login'))

    codusuario = session['usuario']['codusuario']

    if request.method == 'POST':
        nome = request.form.get('nome').strip()
        descricao = request.form.get('descricao', '').strip() or None
        dthrultmodificacao = datetime.now()

        try:
            if not nome:
                flash('Nome do pacote é obrigatório.', 'error')
                return redirect(request.url)

            with get_db() as (conn, cur):
                # Verificar se o nome já existe para outro pacote
                cur.execute("SELECT 1 FROM PACOTES WHERE UPPER(NOME) = UPPER(?) AND CODPACOTE != ?", (nome, codpacote))
                if cur.fetchone():
                    flash("Já existe um pacote com esse nome.", "error")
                    return redirect(request.url)

                # Atualizar pacote
                cur.execute("""
                    UPDATE PACOTES
                    SET NOME = ?, DESCRICAO = ?, CODUSUARIO = ?, DTHRULTMODIFICACAO = ?
                    WHERE CODPACOTE = ?
                """, (nome, descricao, codusuario, dthrultmodificacao, codpacote))
                current_app.logger.info(f"Pacote CODPACOTE={codpacote} atualizado.")

                conn.commit()
                flash("Pacote atualizado com sucesso!", "success")
                return redirect(url_for('pacotes.visualizar_pacotes'))

        except Exception as e:
            current_app.logger.error(f"Erro ao atualizar pacote CODPACOTE={codpacote}: {str(e)}")
            flash(f"Erro ao atualizar pacote: {str(e)}", "error")
            return redirect(request.url)

    try:
        with get_db() as (conn, cur):
            # Carregar pacote
            cur.execute("""
                SELECT NOME, DESCRICAO
                FROM PACOTES
                WHERE CODPACOTE = ?
            """, (codpacote,))
            pacote = cur.fetchone()
            if not pacote:
                current_app.logger.warning(f"Pacote CODPACOTE={codpacote} não encontrado.")
                flash("Pacote não encontrado.", "error")
                return redirect(url_for('pacotes.visualizar_pacotes'))
            current_app.logger.info(f"Pacote encontrado: CODPACOTE={codpacote}, NOME={pacote[0]}")

            return render_template('editar_pacote.html',
                                   pacote={'nome': pacote[0], 'descricao': pacote[1]})

    except Exception as e:
        current_app.logger.error(f"Erro ao carregar formulário para CODPACOTE={codpacote}: {str(e)}")
        flash(f"Erro ao carregar formulário: {str(e)}", "error")
        return redirect(url_for('pacotes.visualizar_pacotes'))

@pacotes_bp.route('/pacotes/excluir_pacote/<int:codpacote>')
def excluir_pacote(codpacote):
    if 'usuario' not in session:
        current_app.logger.error("Sessão de usuário não encontrada.")
        return redirect(url_for('auth.login'))

    if not codpacote:
        current_app.logger.error("CODPACOTE inválido fornecido.")
        flash("Código do pacote inválido.", "error")
        return redirect(url_for('pacotes.visualizar_pacotes'))

    codusuario = session['usuario']['codusuario']
    dthrultmodificacao = datetime.now()

    try:
        with get_db() as (conn, cur):
            # Desvincular scripts
            cur.execute("UPDATE SCRIPTLAUDO SET CODPACOTE = NULL WHERE CODPACOTE = ?", (codpacote,))
            current_app.logger.info(f"Desvinculados scripts de CODPACOTE={codpacote}")

            # Excluir pacote
            cur.execute("DELETE FROM PACOTES WHERE CODPACOTE = ?", (codpacote,))
            conn.commit()
            current_app.logger.info(f"Pacote CODPACOTE={codpacote} excluído.")
            flash("Pacote excluído com sucesso!", "success")

    except Exception as e:
        current_app.logger.error(f"Erro ao excluir pacote CODPACOTE={codpacote}: {str(e)}")
        flash(f"Erro ao excluir pacote: {str(e)}", "error")

    return redirect(url_for('pacotes.visualizar_pacotes'))