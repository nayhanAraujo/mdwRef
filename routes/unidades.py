from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services import db_updater
from datetime import datetime

unidades_bp = Blueprint('unidades', __name__)

def get_db():
    return db_updater.get_db_from_g()

@unidades_bp.route('/visualizar_unidades')
def visualizar_unidades():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    conn, cur = get_db()
    
    # Obter página atual (default = 1)
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = 10
    
    # Calcular skip
    skip = (pagina - 1) * itens_por_pagina
    
    # Contar total de registros
    cur.execute("SELECT COUNT(*) FROM UNIDADEMEDIDA")
    total_registros = cur.fetchone()[0]
    
    # Calcular total de páginas
    total_paginas = (total_registros + itens_por_pagina - 1) // itens_por_pagina
    
    # Buscar registros da página atual usando FIRST e SKIP (sintaxe Firebird)
    cur.execute("""
        SELECT FIRST ? SKIP ? CODUNIDADEMEDIDA, DESCRICAO, STATUS 
        FROM UNIDADEMEDIDA 
        ORDER BY DESCRICAO
    """, (itens_por_pagina, skip))
    unidades = cur.fetchall()
    
    return render_template('visualizar_unidades.html', 
                         unidades=unidades,
                         pagina_atual=pagina,
                         total_paginas=total_paginas,
                         total_registros=total_registros)

@unidades_bp.route('/nova_unidade', methods=['GET', 'POST'])
def nova_unidade():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        conn, cur = get_db()
        descricao = request.form['descricao']
        status = int(request.form['status'])
        
        try:
            cur.execute("SELECT 1 FROM UNIDADEMEDIDA WHERE DESCRICAO = ?", (descricao,))
            if cur.fetchone():
                flash("Essa unidade de medida já está cadastrada.", "error")
                return redirect(url_for('unidades.visualizar_unidades'))
            
            cur.execute("""
                INSERT INTO UNIDADEMEDIDA (DESCRICAO, STATUS, CODUSUARIO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?)
            """, (descricao, status, session['usuario']['codusuario'], datetime.now()))
            conn.commit()
            flash("Unidade de medida cadastrada com sucesso!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao cadastrar unidade de medida: {str(e)}", "error")
        
        return redirect(url_for('unidades.visualizar_unidades'))
    
    return redirect(url_for('unidades.visualizar_unidades'))

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