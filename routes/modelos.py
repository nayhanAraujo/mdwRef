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
    # A query base para selecionar os campos que serão paginados
    query_base_modelos = """
        SELECT CODMODELO, NOME
        FROM MODELO_MODO_TEXTO
        WHERE CODUSUARIO = ?
    """
    params_base = [codusuario]
    
    # Adiciona o filtro de nome à query base e aos parâmetros
    if filtro_nome:
        query_base_modelos += " AND UPPER(NOME) LIKE UPPER(?)"
        params_base.append(f"%{filtro_nome}%")
    
    # A ordenação deve ser aplicada antes da paginação (geralmente)
    # No entanto, com FIRST/SKIP do Firebird, a subconsulta pode ser necessária para garantir a ordem correta
    # ou aplicar a ordenação na query mais externa.

    # Contagem total com base nos filtros aplicados
    count_query = "SELECT COUNT(*) FROM (" + query_base_modelos + ")" # Conta sobre a query filtrada
    # Para count_params, usamos os mesmos params_base
    count_params = list(params_base) # Cria uma cópia para evitar modificação acidental

    try:
        current_app.logger.info(f"Executando contagem: {count_query} com params: {count_params}")
        cur.execute(count_query, count_params)
        total_modelos_result = cur.fetchone() # Adicionado _result
        total_modelos = total_modelos_result[0] if total_modelos_result else 0
        total_paginas = (total_modelos + itens_por_pagina - 1) // itens_por_pagina if total_modelos > 0 else 0
        
        # Consulta paginada
        # A ordenação principal (ORDER BY NOME) deve estar na query mais externa ou na subquery
        # para que FIRST e SKIP funcionem corretamente sobre o conjunto ordenado.
        # O Firebird aplica o ORDER BY *antes* de FIRST/SKIP se estiver na mesma query.
        
        paginated_query = f"""
            SELECT FIRST {itens_por_pagina} SKIP {offset}
                   sub.CODMODELO, sub.NOME
            FROM ({query_base_modelos} ORDER BY NOME) sub 
        """ 
        # params_base já contém codusuario e filtro_nome (se houver)
        
        current_app.logger.info(f"Executando consulta paginada: {paginated_query} com params: {params_base}")
        cur.execute(paginated_query, params_base)
        modelos = cur.fetchall()

        modelos_detalhes = []
        for modelo_tuple in modelos: # Renomeado para evitar conflito com o nome do blueprint/módulo
            codmodelo = modelo_tuple[0]
            cur.execute("""
                SELECT CODSECAO, NOME
                FROM SECAO_MODO_TEXTO
                WHERE CODMODELO = ?
                ORDER BY ORDEM, NOME
            """, (codmodelo,))
            secoes = cur.fetchall()
            modelos_detalhes.append({
                'modelo': modelo_tuple, # Passa a tupla inteira
                'secoes': secoes
                # 'codmodelo': codmodelo # Removido, já que modelo[0] pode ser usado no template
            })

        return render_template('visualizar_modelos.html',
                               modelos_detalhes=modelos_detalhes,
                               pagina=pagina,
                               total_paginas=total_paginas,
                               total_modelos=total_modelos, # Adicionando total_modelos
                               filtro_nome=filtro_nome)
    except Exception as e:
        current_app.logger.error(f"Erro ao executar consulta em visualizar_modelos: {str(e)}", exc_info=True)
        flash(f"Erro ao carregar modelos: {str(e)}", "error")
        # Redirecionar para uma página mais genérica em caso de erro
        return redirect(url_for('bibliotecas.biblioteca')) 


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
    


