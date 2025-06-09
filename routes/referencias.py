from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app,jsonify
from datetime import datetime
import os
import uuid
from get_db import get_db

referencias_bp = Blueprint('referencias', __name__)



@referencias_bp.route('/nova_referencia', methods=['GET', 'POST'])
def nova_referencia():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        TITULO = request.form['TITULO']
        ano = request.form['ano']
        with get_db() as (conn, cur):
            cur.execute("""
                INSERT INTO REFERENCIA (TITULO, ANO, CODUSUARIO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?)
                RETURNING CODREFERENCIA
            """, (TITULO, ano, 4, datetime.now()))
            codreferencia = cur.fetchone()[0]
            conn.commit()
            flash("Referência cadastrada com sucesso!", "success")
            return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
    return render_template('nova_referencia.html')




@referencias_bp.route('/visualizar_referencias')
def visualizar_referencias():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    # Configurações de paginação
    itens_por_pagina = 10
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * itens_por_pagina

    # Filtros
    filtro_titulo = request.args.get('titulo', '').strip()
    filtro_ano = request.args.get('ano', '').strip()
    filtro_autor = request.args.get('autor', '').strip()
    filtro_abreviacao = request.args.get('abreviacao', '').strip()

    # Montar a consulta base
    query_base = """
        SELECT DISTINCT r.CODREFERENCIA, r.TITULO, r.ANO, 
               LIST(a.NOME || ' (' || COALESCE(a.ABREVIACAO, '') || ')', ', ') AS AUTORES,
               r.DESCRICAO, e.DESCRICAO AS ESPECIALIDADE
        FROM REFERENCIA r
        LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
        LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
        LEFT JOIN ESPECIALIDADE e ON r.CODESPECIALIDADE = e.CODESPECIALIDADE
        WHERE 1=1
    """
    params = []
    if filtro_titulo:
        query_base += " AND UPPER(r.TITULO) LIKE UPPER(?)"
        params.append(f"%{filtro_titulo}%")
    if filtro_ano:
        query_base += " AND r.ANO = ?"
        params.append(filtro_ano)
    if filtro_autor:
        query_base += " AND UPPER(a.NOME) LIKE UPPER(?)"
        params.append(f"%{filtro_autor}%")
    if filtro_abreviacao:
        query_base += " AND UPPER(a.ABREVIACAO) LIKE UPPER(?)"
        params.append(f"%{filtro_abreviacao}%")
    query_base += " GROUP BY r.CODREFERENCIA, r.TITULO, r.ANO, r.DESCRICAO, e.DESCRICAO ORDER BY r.ANO DESC"

    # Contagem total
    count_query = """
        SELECT COUNT(DISTINCT r.CODREFERENCIA)
        FROM REFERENCIA r
        LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
        LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
        WHERE 1=1
    """
    count_params = []
    if filtro_titulo:
        count_query += " AND UPPER(r.TITULO) LIKE UPPER(?)"
        count_params.append(f"%{filtro_titulo}%")
    if filtro_ano:
        count_query += " AND r.ANO = ?"
        count_params.append(filtro_ano)
    if filtro_autor:
        count_query += " AND UPPER(a.NOME) LIKE UPPER(?)"
        count_params.append(f"%{filtro_autor}%")
    if filtro_abreviacao:
        count_query += " AND UPPER(a.ABREVIACAO) LIKE UPPER(?)"
        count_params.append(f"%{filtro_abreviacao}%")

    try:
        with get_db() as (conn, cur):
            current_app.logger.info(f"Executando contagem: {count_query} com params: {count_params}")
            cur.execute(count_query, count_params)
            total_referencias = cur.fetchone()[0]
            total_paginas = (total_referencias + itens_por_pagina - 1) // itens_por_pagina

            # Consulta paginada
            paginated_query = f"""
                SELECT FIRST {itens_por_pagina} SKIP {offset}
                       r.CODREFERENCIA, r.TITULO, r.ANO, 
                       LIST(a.NOME || ' (' || COALESCE(a.ABREVIACAO, '') || ')', ', ') AS AUTORES,
                       r.DESCRICAO, e.DESCRICAO AS ESPECIALIDADE
                FROM REFERENCIA r
                LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
                LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
                LEFT JOIN ESPECIALIDADE e ON r.CODESPECIALIDADE = e.CODESPECIALIDADE
                WHERE 1=1
            """
            if filtro_titulo:
                paginated_query += " AND UPPER(r.TITULO) LIKE UPPER(?)"
            if filtro_ano:
                paginated_query += " AND r.ANO = ?"
            if filtro_autor:
                paginated_query += " AND UPPER(a.NOME) LIKE UPPER(?)"
            if filtro_abreviacao:
                paginated_query += " AND UPPER(a.ABREVIACAO) LIKE UPPER(?)"
            paginated_query += " GROUP BY r.CODREFERENCIA, r.TITULO, r.ANO, r.DESCRICAO, e.DESCRICAO ORDER BY r.ANO DESC"

            current_app.logger.info(f"Executando consulta paginada: {paginated_query} com params: {params}")
            cur.execute(paginated_query, params)
            referencias = cur.fetchall()

            return render_template('visualizar_referencias.html',
                                referencias=referencias,
                                pagina=pagina,
                                total_paginas=total_paginas,
                                filtro_titulo=filtro_titulo,
                                filtro_ano=filtro_ano,
                                filtro_autor=filtro_autor,
                                filtro_abreviacao=filtro_abreviacao)
    except Exception as e:
        current_app.logger.error(f"Erro ao executar consulta: {str(e)}")
        flash(f"Erro ao carregar referências: {str(e)}", "error")
        return redirect(url_for('bibliotecas.biblioteca'))



@referencias_bp.route('/editar_referencia/<int:codreferencia>', methods=['GET', 'POST'])
def editar_referencia(codreferencia):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        TITULO = request.form['TITULO']
        ano = request.form['ano']
        with get_db() as (conn, cur):
            cur.execute("""
                UPDATE REFERENCIA SET
                TITULO = ?, ANO = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
                WHERE CODREFERENCIA = ?
            """, (TITULO, ano, datetime.now(), 4, codreferencia))
            conn.commit()
            flash("Referência atualizada com sucesso!", "success")
            return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
    
    with get_db() as (conn, cur):
        cur.execute("SELECT CODREFERENCIA, TITULO, ANO FROM REFERENCIA WHERE CODREFERENCIA = ?", (codreferencia,))
        referencia = cur.fetchone()
    return render_template('editar_referencia.html', referencia=referencia)

@referencias_bp.route('/excluir_referencia/<int:codreferencia>', methods=['POST'])
def excluir_referencia(codreferencia):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    with get_db() as (conn, cur):
        try:
            # Excluir arquivos associados
            cur.execute("SELECT LINK FROM ANEXOS WHERE CODREFERENCIA = ?", (codreferencia,))
            anexos = cur.fetchall()
            for anexo in anexos:
                LINK = anexo[0]
                if LINK and os.path.exists(LINK):
                    os.remove(LINK)
            cur.execute("DELETE FROM ANEXOS WHERE CODREFERENCIA = ?", (codreferencia,))
            cur.execute("DELETE FROM REFERENCIA WHERE CODREFERENCIA = ?", (codreferencia,))
            conn.commit()
            flash("Referência e anexos vinculados excluídos com sucesso!", "success")
        except Exception as e:
            conn.rollback()
            flash("Erro ao excluir: referência está vinculada a outras tabelas.", "error")
    return redirect(url_for('referencias.visualizar_referencias'))

@referencias_bp.route('/visualizar_anexos/<int:codreferencia>', methods=['GET', 'POST'])
def visualizar_anexos(codreferencia):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        descricao = request.form['descricao']
        nome = request.form['nome']
        link = request.form['link']
        LINK = None
        if 'arquivo' in request.files:
            arquivo = request.files['arquivo']
            if arquivo and arquivo.filename:
                extensao = os.path.splitext(arquivo.filename)[1].lower()
                if extensao != '.pdf':
                    flash("Apenas arquivos PDF são permitidos.", "error")
                    return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
                nome_arquivo = f"{uuid.uuid4()}{extensao}"
                LINK = os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo)
                arquivo.save(LINK)
        
        with get_db() as (conn, cur):
            cur.execute("""
                INSERT INTO ANEXOS (CODREFERENCIA, DESCRICAO, NOME, LINK, LINK, CODUSUARIO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (codreferencia, descricao, nome, link, LINK, 4, datetime.now()))
            conn.commit()
            flash("Anexo adicionado com sucesso!", "success")
            return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
    
    with get_db() as (conn, cur):
        cur.execute("SELECT CODREFERENCIA, TITULO, ANO FROM REFERENCIA WHERE CODREFERENCIA = ?", (codreferencia,))
        referencia = cur.fetchone()
        cur.execute("SELECT CODANEXO, DESCRICAO, NOME, LINK, LINK FROM ANEXOS WHERE CODREFERENCIA = ?", (codreferencia,))
        anexos = cur.fetchall()
    return render_template('visualizar_anexos.html', referencia=referencia, anexos=anexos)

@referencias_bp.route('/editar_anexo/<int:codanexo>', methods=['GET', 'POST'])
def editar_anexo(codanexo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        descricao = request.form['descricao']
        nome = request.form['nome']
        link = request.form['link']
        
        with get_db() as (conn, cur):
            cur.execute("SELECT CODREFERENCIA, LINK FROM ANEXOS WHERE CODANEXO = ?", (codanexo,))
            result = cur.fetchone()
            codreferencia, LINK_antigo = result
            LINK = LINK_antigo
            
            if 'arquivo' in request.files:
                arquivo = request.files['arquivo']
                if arquivo and arquivo.filename:
                    extensao = os.path.splitext(arquivo.filename)[1].lower()
                    if extensao != '.pdf':
                        flash("Apenas arquivos PDF são permitidos.", "error")
                        return redirect(url_for('referencias.editar_anexo', codanexo=codanexo))
                    if LINK_antigo and os.path.exists(LINK_antigo):
                        os.remove(LINK_antigo)
                    nome_arquivo = f"{uuid.uuid4()}{extensao}"
                    LINK = os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo)
                    arquivo.save(LINK)
            
            cur.execute("""
                UPDATE ANEXOS SET
                DESCRICAO = ?, NOME = ?, LINK = ?, LINK = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
                WHERE CODANEXO = ?
            """, (descricao, nome, link, LINK, datetime.now(), 4, codanexo))
            conn.commit()
            flash("Anexo atualizado com sucesso!", "success")
            return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))
    
    with get_db() as (conn, cur):
        cur.execute("SELECT CODANEXO, CODREFERENCIA, DESCRICAO, NOME, LINK, LINK FROM ANEXOS WHERE CODANEXO = ?", (codanexo,))
        anexo = cur.fetchone()
    return render_template('editar_anexo.html', anexo=anexo)

@referencias_bp.route('/excluir_anexo/<int:codanexo>', methods=['POST'])
def excluir_anexo(codanexo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    with get_db() as (conn, cur):
        cur.execute("SELECT CODREFERENCIA, LINK FROM ANEXOS WHERE CODANEXO = ?", (codanexo,))
        result = cur.fetchone()
        codreferencia, LINK = result
        if LINK and os.path.exists(LINK):
            os.remove(LINK)
        cur.execute("DELETE FROM ANEXOS WHERE CODANEXO = ?", (codanexo,))
        conn.commit()
        flash("Anexo excluído com sucesso!", "success")
    return redirect(url_for('referencias.visualizar_anexos', codreferencia=codreferencia))




@referencias_bp.route('/get_anexos/<int:codreferencia>', methods=['GET'])
def get_anexos(codreferencia):
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT TIPO_ANEXO, LINK, DESCRICAO
                FROM ANEXOS
                WHERE CODREFERENCIA = ?
            """, (codreferencia,))
            anexos = []
            for row in cur.fetchall():
                tipo = row[0]
                link = row[1]
                descricao = row[2] or tipo

                # Usar LINK diretamente, validando se é não nulo
                url = link if link else ''

                anexos.append({
                    'tipo': tipo,
                    'caminho': url,  # Mantemos o nome 'caminho' para compatibilidade com o frontend
                    'descricao': descricao
                })
            return jsonify(anexos)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar anexos: {str(e)}")
        return jsonify({'error': str(e)}), 500