from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
import hashlib
from datetime import datetime
from get_db import get_db

users_bp = Blueprint('users', __name__)

@users_bp.route('/novo_usuario', methods=['GET', 'POST'])
def novo_usuario():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        identificacao = request.form.get('identificacao', '').strip().lower()
        senha = request.form.get('senha', '')  # Não remover espaços da senha intencionalmente
        confirmar_senha = request.form.get('confirmar_senha', '')
        perfil = request.form.get('perfil', '')
        status_str = request.form.get('status', '')  # Pegar como string primeiro

        form_data_for_rerender = {
            'nome': nome,
            'identificacao': identificacao,
            'perfil': perfil,
            'status_val': status_str
        }

        error_occurred = False

        # Validações básicas
        if not nome:
            flash("O campo Nome Completo é obrigatório.", "error")
            error_occurred = True

        if not identificacao:
            flash("O campo Login (Identificação) é obrigatório.", "error")
            error_occurred = True
        elif ' ' in identificacao:
            flash("O Login (Identificação) não pode conter espaços e deve ser uma única palavra.", "error")
            error_occurred = True

        if not senha:
            flash("O campo Senha é obrigatório.", "error")
            error_occurred = True
        elif len(senha) < 6:
            flash("A Senha deve ter no mínimo 6 caracteres.", "error")
            error_occurred = True

        if not confirmar_senha:
            flash("O campo Confirmar Senha é obrigatório.", "error")
            error_occurred = True
        elif senha != confirmar_senha:
            flash("As senhas não coincidem.", "error")
            error_occurred = True

        if not perfil:
            flash("O campo Perfil é obrigatório.", "error")
            error_occurred = True

        status = None
        if not status_str:
            flash("O campo Status é obrigatório.", "error")
            error_occurred = True
        else:
            try:
                status = int(status_str)
                if status not in [-1, 0]:
                    flash("Valor inválido para Status.", "error")
                    error_occurred = True
            except ValueError:
                flash("Valor inválido para Status.", "error")
                error_occurred = True

        if error_occurred:
            return render_template('novo_usuario.html', **form_data_for_rerender)

        # Verifica se o usuário já existe
        try:
            with get_db() as (conn, cur):
                cur.execute("SELECT 1 FROM USUARIO WHERE IDENTIFICACAO = ?", (identificacao,))
                if cur.fetchone():
                    flash("Esse login já está em uso.", "error")
                    return render_template('novo_usuario.html', **form_data_for_rerender)

                ucaseNome = nome
                senha_criptografada = hashlib.sha256(senha.encode()).hexdigest()

                cur.execute("""
                    INSERT INTO USUARIO (NOME, IDENTIFICACAO, UCASE_NOME, SENHA, PERFIL, STATUS, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nome, identificacao, ucaseNome, senha_criptografada, perfil, status, datetime.now()))
                conn.commit()
                flash("Usuário cadastrado com sucesso!", "success")
                return redirect(url_for('users.usuarios'))

        except Exception as e:
            current_app.logger.error(f"Erro ao interagir com o banco de dados: {str(e)}")
            flash(f"Erro interno ao cadastrar usuário. Por favor, tente novamente. Detalhes: {str(e)}", "error")
            return render_template('novo_usuario.html', **form_data_for_rerender)

    # Método GET: apenas renderiza o formulário vazio
    return render_template('novo_usuario.html', nome='', identificacao='', perfil='', status_val='-1')

@users_bp.route('/editar_usuario/<int:codusuario>', methods=['GET', 'POST'])
def editar_usuario(codusuario):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
   
    with get_db() as (conn, cur):
        if request.method == 'POST':
            nome = request.form['nome']
            identificacao = request.form['identificacao'].strip().lower()
            perfil = request.form['perfil']
            status = request.form['status']
        
            cur.execute("SELECT 1 FROM USUARIO WHERE IDENTIFICACAO = ? AND CODUSUARIO != ?", (identificacao, codusuario))
            if cur.fetchone():
                flash("Esse login (identificação) já está em uso por outro usuário.", "error")
                cur.execute("SELECT NOME, IDENTIFICACAO, PERFIL FROM USUARIO WHERE CODUSUARIO = ?", (codusuario,))
                usuario_original = cur.fetchone()
                return render_template('editar_usuario.html', 
                                    codusuario=codusuario, 
                                    usuario={'NOME': nome, 'IDENTIFICACAO': identificacao, 'PERFIL': perfil},
                                    usuario_original=usuario_original
                                    )

            if ' ' in identificacao:
                flash("O Login (Identificação) não pode conter espaços e deve ser uma única palavra.", "error")
                cur.execute("SELECT NOME, IDENTIFICACAO, PERFIL FROM USUARIO WHERE CODUSUARIO = ?", (codusuario,))
                usuario_original = cur.fetchone()
                return render_template('editar_usuario.html', 
                                    codusuario=codusuario, 
                                    usuario={'NOME': nome, 'IDENTIFICACAO': identificacao, 'PERFIL': perfil},
                                    usuario_original=usuario_original
                                    )
            try:
                cur.execute("""
                    UPDATE USUARIO SET NOME = ?, IDENTIFICACAO = ?, PERFIL = ?,STATUS = ?, DTHRULTMODIFICACAO = ?
                    WHERE CODUSUARIO = ?
                """, (nome, identificacao, perfil, status, datetime.now(), codusuario))
                conn.commit()
                flash("Usuário atualizado com sucesso!", "success")
                return redirect(url_for('users.usuarios'))
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"Erro ao atualizar usuário CODUSUARIO={codusuario}: {str(e)}")
                flash(f"Erro ao atualizar usuário: {str(e)}", "error")
                return redirect(url_for('users.usuarios'))
    
        cur.execute("SELECT NOME, IDENTIFICACAO, PERFIL, STATUS FROM USUARIO WHERE CODUSUARIO = ?", (codusuario,))
        usuario_db = cur.fetchone()
        if not usuario_db:
            flash("Usuário não encontrado.", "error")
            return redirect(url_for('users.usuarios'))
        usuario_data = {
            'NOME': usuario_db[0],
            'IDENTIFICACAO': usuario_db[1],
            'PERFIL': usuario_db[2],
            'STATUS': usuario_db[3]
        }    
        return render_template('editar_usuario.html', codusuario=codusuario, usuario=usuario_data)


@users_bp.route('/excluir_usuario/<int:codusuario>', methods=['POST'])
def excluir_usuario(codusuario):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
        
    with get_db() as (conn, cur):
        try:
            cur.execute("DELETE FROM USUARIO WHERE CODUSUARIO = ?", (codusuario,))
            if cur.rowcount == 0: # Nenhum usuário foi excluído
                flash("Usuário não encontrado ou já excluído.", "warning")
            else:
                conn.commit()
                flash("Usuário excluído com sucesso!", "success")
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao excluir usuário CODUSUARIO={codusuario}: {str(e)}")
            flash(f"Erro ao excluir usuário: {str(e)}", "error")
            
        return redirect(url_for('users.usuarios'))

@users_bp.route('/visualizar_usuarios')
def usuarios():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    with get_db() as (conn, cur):
        cur.execute("SELECT CODUSUARIO, NOME, IDENTIFICACAO, PERFIL, STATUS FROM USUARIO ORDER BY NOME") # Adicionado STATUS
        usuarios = cur.fetchall()
        return render_template('visualizar_usuarios.html', usuarios=usuarios)