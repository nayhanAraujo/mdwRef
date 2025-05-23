from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app,jsonify
from datetime import datetime

modelos_bp = Blueprint('modelos', __name__)

def get_db():
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        raise Exception("Conexão com o banco de dados não foi inicializada.")
    return conn, cur

@modelos_bp.route('/novo_modelo', methods=['GET', 'POST'])
def novo_modelo():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
# Log para depuração
    current_app.logger.info(f"Conteúdo de session['usuario']: {session['usuario']}")

    # Garantir que session['usuario'] é um dicionário e tem a chave 'codusuario'
    if not isinstance(session['usuario'], dict) or 'codusuario' not in session['usuario']:
        flash("Erro na sessão do usuário. Por favor, faça login novamente.", "error")
        return redirect(url_for('auth.logout'))

    if request.method == 'POST':
        nome = request.form['nome'].strip()

        if not nome:
            flash("O nome do modelo é obrigatório.", "error")
            return redirect(request.url)

        codusuario = session['usuario']['codusuario']

        # Verificar se o nome do modelo já existe para o usuário
        cur.execute("SELECT 1 FROM MODELO_MODO_TEXTO WHERE UPPER(NOME) = UPPER(?) AND CODUSUARIO = ?", (nome, codusuario))
        if cur.fetchone():
            flash("Já existe um modelo com esse nome.", "error")
            return redirect(request.url)

        try:
            cur.execute("""
                INSERT INTO MODELO_MODO_TEXTO (NOME, CODUSUARIO)
                VALUES (?, ?)
                RETURNING CODMODELO
            """, (nome, codusuario))
            codmodelo = cur.fetchone()[0]
            conn.commit()
            flash("Modelo criado com sucesso!", "success")
            return redirect(url_for('modelos.visualizar_modelos'))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao criar modelo: {str(e)}", "error")
            return redirect(request.url)

    return render_template('novo_modelo.html')



@modelos_bp.route('/visualizar_modelos')
def visualizar_modelos():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    codusuario = session['usuario']['codusuario']

    # Configurações de paginação
    itens_por_pagina = 10
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * itens_por_pagina

    # Filtro por nome
    filtro_nome = request.args.get('nome', '').strip()

    # Consulta para modelos com filtro
    query = """
        SELECT CODMODELO, NOME
        FROM MODELO_MODO_TEXTO
        WHERE CODUSUARIO = ?
    """
    params = [codusuario]
    if filtro_nome:
        query += " AND UPPER(NOME) LIKE UPPER(?)"
        params.append(f"%{filtro_nome}%")
    query += " ORDER BY NOME"

    # Contagem total
    count_query = """
        SELECT COUNT(*)
        FROM MODELO_MODO_TEXTO
        WHERE CODUSUARIO = ?
    """
    count_params = [codusuario]
    if filtro_nome:
        count_query += " AND UPPER(NOME) LIKE UPPER(?)"
        count_params.append(f"%{filtro_nome}%")

    try:
        current_app.logger.info(f"Executando contagem: {count_query} com params: {count_params}")
        cur.execute(count_query, count_params)
        total_modelos = cur.fetchone()[0]
        total_paginas = (total_modelos + itens_por_pagina - 1) // itens_por_pagina

        # Consulta paginada
        paginated_query = f"""
            SELECT FIRST {itens_por_pagina} SKIP {offset}
                   CODMODELO, NOME
            FROM MODELO_MODO_TEXTO
            WHERE CODUSUARIO = ?
        """
        if filtro_nome:
            paginated_query += " AND UPPER(NOME) LIKE UPPER(?)"
        paginated_query += " ORDER BY NOME"

        current_app.logger.info(f"Executando consulta paginada: {paginated_query} com params: {params}")
        cur.execute(paginated_query, params)
        modelos = cur.fetchall()

        # Carregar seções para cada modelo
        modelos_detalhes = []
        for modelo in modelos:
            codmodelo = modelo[0]
            cur.execute("""
                SELECT CODSECAO, NOME
                FROM SECAO_MODO_TEXTO
                WHERE CODMODELO = ?
                ORDER BY ORDEM, NOME
            """, (codmodelo,))
            secoes = cur.fetchall()
            modelos_detalhes.append({
                'modelo': modelo,
                'secoes': secoes
            })

        return render_template('visualizar_modelos.html',
                               modelos_detalhes=modelos_detalhes,
                               pagina=pagina,
                               total_paginas=total_paginas,
                               filtro_nome=filtro_nome)
    except Exception as e:
        current_app.logger.error(f"Erro ao executar consulta: {str(e)}")
        flash(f"Erro ao carregar modelos: {str(e)}", "error")
        return redirect(url_for('variaveis.home'))


@modelos_bp.route('/excluir_modelo/<int:codmodelo>', methods=['POST'])
def excluir_modelo(codmodelo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    codusuario = session['usuario']['codusuario']

    try:
        # Verificar se o modelo pertence ao usuário
        cur.execute("SELECT 1 FROM MODELO_MODO_TEXTO WHERE CODMODELO = ? AND CODUSUARIO = ?", (codmodelo, codusuario))
        if not cur.fetchone():
            flash("Modelo não encontrado ou você não tem permissão para excluí-lo.", "error")
            return redirect(url_for('modelos.visualizar_modelos'))

        # Excluir associações de variáveis (SECAO_VARIAVEL)
        cur.execute("""
            DELETE FROM SECAO_VARIAVEL
            WHERE CODSECAO IN (SELECT CODSECAO FROM SECAO_MODO_TEXTO WHERE CODMODELO = ?)
        """, (codmodelo,))

        # Excluir seções associadas ao modelo
        cur.execute("DELETE FROM SECAO_MODO_TEXTO WHERE CODMODELO = ?", (codmodelo,))

        # Excluir o modelo
        cur.execute("DELETE FROM MODELO_MODO_TEXTO WHERE CODMODELO = ?", (codmodelo,))

        conn.commit()
        flash("Modelo excluído com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao excluir modelo: {str(e)}", "error")

    return redirect(url_for('modelos.visualizar_modelos'))




@modelos_bp.route('/get_secoes/<int:codmodelo>', methods=['GET'])
def get_secoes(codmodelo):
    if 'usuario' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    conn, cur = get_db()
    try:
        cur.execute("""
            SELECT NOME, ORDEM
            FROM SECAO_MODO_TEXTO
            WHERE CODMODELO = ?
            ORDER BY ORDEM, NOME
        """, (codmodelo,))
        secoes = [{'nome': row[0], 'ordem': row[1]} for row in cur.fetchall()]
        return jsonify(secoes)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar seções: {str(e)}")
        return jsonify({'error': str(e)}), 500
    


