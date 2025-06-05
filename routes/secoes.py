from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app,jsonify
from datetime import datetime
from get_db import get_db

secoes_bp = Blueprint('secoes', __name__)



@secoes_bp.route('/nova_secao/<int:codmodelo>', methods=['GET', 'POST'])
def nova_secao(codmodelo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    # Garantir que session['usuario'] é um dicionário e tem a chave 'codusuario'
    if not isinstance(session['usuario'], dict) or 'codusuario' not in session['usuario']:
        flash("Erro na sessão do usuário. Por favor, faça login novamente.", "error")
        return redirect(url_for('auth.logout'))

    codusuario = session['usuario']['codusuario']

    with get_db() as (conn, cur):
        # Verificar se o modelo pertence ao usuário
        cur.execute("SELECT 1 FROM MODELO_MODO_TEXTO WHERE CODMODELO = ? AND CODUSUARIO = ?", (codmodelo, codusuario))
        if not cur.fetchone():
            flash("Modelo não encontrado ou você não tem permissão para acessá-lo.", "error")
            return redirect(url_for('modelos.visualizar_modelos'))

        if request.method == 'POST':
            nome = request.form['nome'].strip()
            variaveis = request.form.getlist('variaveis[]')

            if not nome:
                flash("O nome da seção é obrigatório.", "error")
                return redirect(url_for('secoes.nova_secao', codmodelo=codmodelo))

            # Verificar se o nome da seção já existe dentro do modelo
            cur.execute("SELECT 1 FROM SECAO_MODO_TEXTO WHERE UPPER(NOME) = UPPER(?) AND CODMODELO = ?", (nome, codmodelo))
            if cur.fetchone():
                flash("Já existe uma seção com esse nome neste modelo.", "error")
                return redirect(url_for('secoes.nova_secao', codmodelo=codmodelo))

            try:
                # Obter a maior ordem atual para o modelo
                cur.execute("SELECT COALESCE(MAX(ORDEM), 0) FROM SECAO_MODO_TEXTO WHERE CODMODELO = ?", (codmodelo,))
                ordem = cur.fetchone()[0] + 1

                # Inserir a nova seção
                cur.execute("""
                    INSERT INTO SECAO_MODO_TEXTO (NOME, CODMODELO, ORDEM)
                    VALUES (?, ?, ?)
                    RETURNING CODSECAO
                """, (nome, codmodelo, ordem))
                codsecao = cur.fetchone()[0]

                # Associar variáveis à seção
                for codvariavel in variaveis:
                    cur.execute("""
                        INSERT INTO SECAO_VARIAVEL (CODSECAO, CODVARIAVEL)
                        VALUES (?, ?)
                    """, (codsecao, codvariavel))

                conn.commit()
                flash("Seção criada com sucesso!", "success")
                return redirect(url_for('secoes.visualizar_secoes', codmodelo=codmodelo))
            except Exception as e:
                conn.rollback()
                flash(f"Erro ao criar seção: {str(e)}", "error")
                return redirect(url_for('secoes.nova_secao', codmodelo=codmodelo))

        # Buscar todas as variáveis disponíveis com fórmulas e normalidades
        cur.execute("""
            SELECT v.CODVARIAVEL, v.NOME, v.SIGLA
            FROM VARIAVEIS v
            ORDER BY v.NOME
        """)
        variaveis = cur.fetchall()

        variaveis_detalhes = []
        for variavel in variaveis:
            codvariavel = variavel[0]
            # Buscar fórmula associada
            cur.execute("""
                SELECT f.FORMULA
                FROM FORMULAS f
                JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
                WHERE fv.CODVARIAVEL = ?
            """, (codvariavel,))
            formula = cur.fetchone()
            formula_texto = formula[0] if formula else "Nenhuma fórmula"

            # Buscar normalidades associadas
            cur.execute("""
                SELECT SEXO, VALORMIN, VALORMAX
                FROM NORMALIDADE
                WHERE CODVARIAVEL = ?
            """, (codvariavel,))
            normalidades = cur.fetchall()
            normalidade_texto = ""
            for normalidade in normalidades:
                sexo, valormin, valormax = normalidade
                normalidade_texto += f"{sexo}: {valormin} a {valormax}; "
            normalidade_texto = normalidade_texto.rstrip("; ") or "Nenhuma normalidade"

            variaveis_detalhes.append({
                'codvariavel': variavel[0],
                'nome': variavel[1],
                'sigla': variavel[2],
                'formula': formula_texto,
                'normalidade': normalidade_texto
            })

        return render_template('nova_secao.html', variaveis=variaveis_detalhes, codmodelo=codmodelo)

@secoes_bp.route('/visualizar_secoes/<int:codmodelo>', methods=['GET'])
def visualizar_secoes(codmodelo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    # Usando context manager para conexão segura
    try:
        with get_db() as (conn, cur):
            # Configurações de paginação
            itens_por_pagina = 10
            pagina = request.args.get('page', 1, type=int)
            offset = (pagina - 1) * itens_por_pagina

            # Obter o nome do modelo
            cur.execute("SELECT NOME FROM MODELO_MODO_TEXTO WHERE CODMODELO = ?", (codmodelo,))
            modelo = cur.fetchone()
            if not modelo:
                flash("Modelo não encontrado.", "error")
                return redirect(url_for('modelos.visualizar_modelos'))
            nome_modelo = modelo[0]

            # Consulta para seções com paginação
            query = """
                SELECT CODSECAO, NOME
                FROM SECAO_MODO_TEXTO
                WHERE CODMODELO = ?
                ORDER BY ORDEM, NOME
            """
            count_query = """
                SELECT COUNT(*)
                FROM SECAO_MODO_TEXTO
                WHERE CODMODELO = ?
            """
            
            current_app.logger.info(f"Executando contagem: {count_query} com params: {[codmodelo]}")
            cur.execute(count_query, [codmodelo])
            total_secoes = cur.fetchone()[0]
            total_paginas = (total_secoes + itens_por_pagina - 1) // itens_por_pagina

            paginated_query = f"""
                SELECT FIRST {itens_por_pagina} SKIP {offset}
                       CODSECAO, NOME
                FROM SECAO_MODO_TEXTO
                WHERE CODMODELO = ?
                ORDER BY ORDEM, NOME
            """
            
            current_app.logger.info(f"Executando consulta paginada: {paginated_query} com params: {[codmodelo]}")
            cur.execute(paginated_query, [codmodelo])
            secoes = cur.fetchall()

            # Carregar variáveis para cada seção
            secoes_detalhes = []
            for secao in secoes:
                codsecao = secao[0]
                cur.execute("""
                    SELECT V.CODVARIAVEL, V.NOME, V.SIGLA
                    FROM SECAO_VARIAVEL SV
                    JOIN VARIAVEIS V ON SV.CODVARIAVEL = V.CODVARIAVEL
                    WHERE SV.CODSECAO = ?
                    ORDER BY V.SIGLA
                """, (codsecao,))
                variaveis = cur.fetchall()
                secoes_detalhes.append({
                    'secao': secao,
                    'variaveis': variaveis
                })

            return render_template('visualizar_secoes.html',
                                codmodelo=codmodelo,
                                nome_modelo=nome_modelo,
                                secoes_detalhes=secoes_detalhes,
                                pagina=pagina,
                                total_paginas=total_paginas)
    except Exception as e:
        current_app.logger.error(f"Erro ao executar consulta: {str(e)}")
        flash(f"Erro ao carregar seções: {str(e)}", "error")
        return redirect(url_for('modelos.visualizar_modelos'))

@secoes_bp.route('/editar_secao/<int:codsecao>', methods=['GET', 'POST'])
def editar_secao(codsecao):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    codusuario = session['usuario']['codusuario']

    with get_db() as (conn, cur):
        # Buscar informações da seção
        cur.execute("""
            SELECT s.NOME, s.CODMODELO
            FROM SECAO_MODO_TEXTO s
            JOIN MODELO_MODO_TEXTO m ON s.CODMODELO = m.CODMODELO
            WHERE s.CODSECAO = ? AND m.CODUSUARIO = ?
        """, (codsecao, codusuario))
        secao = cur.fetchone()
        if not secao:
            flash("Seção não encontrada ou você não tem permissão para editá-la.", "error")
            return redirect(url_for('modelos.visualizar_modelos'))

        nome_secao, codmodelo = secao

        if request.method == 'POST':
            nome = request.form['nome'].strip()
            variaveis = request.form.getlist('variaveis[]')

            if not nome:
                flash("O nome da seção é obrigatório.", "error")
                return redirect(url_for('secoes.editar_secao', codsecao=codsecao))

            # Verificar se o nome da seção já existe dentro do modelo (exceto para a própria seção)
            cur.execute("""
                SELECT 1 FROM SECAO_MODO_TEXTO
                WHERE UPPER(NOME) = UPPER(?) AND CODMODELO = ? AND CODSECAO != ?
            """, (nome, codmodelo, codsecao))
            if cur.fetchone():
                flash("Já existe uma seção com esse nome neste modelo.", "error")
                return redirect(url_for('secoes.editar_secao', codsecao=codsecao))

            try:
                # Atualizar a seção
                cur.execute("""
                    UPDATE SECAO_MODO_TEXTO
                    SET NOME = ?
                    WHERE CODSECAO = ?
                """, (nome, codsecao))

                # Remover associações de variáveis existentes
                cur.execute("DELETE FROM SECAO_VARIAVEL WHERE CODSECAO = ?", (codsecao,))

                # Associar novas variáveis
                for codvariavel in variaveis:
                    cur.execute("""
                        INSERT INTO SECAO_VARIAVEL (CODSECAO, CODVARIAVEL)
                        VALUES (?, ?)
                    """, (codsecao, codvariavel))

                conn.commit()
                flash("Seção atualizada com sucesso!", "success")
                return redirect(url_for('secoes.visualizar_secoes', codmodelo=codmodelo))
            except Exception as e:
                conn.rollback()
                flash(f"Erro ao atualizar seção: {str(e)}", "error")
                return redirect(url_for('secoes.editar_secao', codsecao=codsecao))

        # Buscar variáveis associadas à seção
        cur.execute("SELECT CODVARIAVEL FROM SECAO_VARIAVEL WHERE CODSECAO = ?", (codsecao,))
        variaveis_associadas = [row[0] for row in cur.fetchall()]

        # Buscar todas as variáveis disponíveis com fórmulas e normalidades
        cur.execute("""
            SELECT v.CODVARIAVEL, v.NOME, v.SIGLA
            FROM VARIAVEIS v
            ORDER BY v.NOME
        """)
        variaveis = cur.fetchall()

        todas_variaveis = []
        for variavel in variaveis:
            codvariavel = variavel[0]
            # Buscar fórmula associada
            cur.execute("""
                SELECT f.FORMULA
                FROM FORMULAS f
                JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
                WHERE fv.CODVARIAVEL = ?
            """, (codvariavel,))
            formula = cur.fetchone()
            formula_texto = formula[0] if formula else "Nenhuma fórmula"

            # Buscar normalidades associadas
            cur.execute("""
                SELECT SEXO, VALORMIN, VALORMAX
                FROM NORMALIDADE
                WHERE CODVARIAVEL = ?
            """, (codvariavel,))
            normalidades = cur.fetchall()
            normalidade_texto = ""
            for normalidade in normalidades:
                sexo, valormin, valormax = normalidade
                normalidade_texto += f"{sexo}: {valormin} a {valormax}; "
            normalidade_texto = normalidade_texto.rstrip("; ") or "Nenhuma normalidade"

            todas_variaveis.append({
                'codvariavel': variavel[0],
                'nome': variavel[1],
                'sigla': variavel[2],
                'formula': formula_texto,
                'normalidade': normalidade_texto
            })

        return render_template('editar_secao.html',
                            codsecao=codsecao,
                            nome_secao=nome_secao,
                            codmodelo=codmodelo,
                            variaveis_associadas=variaveis_associadas,
                            todas_variaveis=todas_variaveis)



@secoes_bp.route('/excluir_secao/<int:codsecao>', methods=['POST'])
def excluir_secao(codsecao):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    codusuario = session['usuario']['codusuario']

    try:
        with get_db() as (conn, cur):
            # Buscar o CODMODELO da seção
            cur.execute("""
                SELECT s.CODMODELO
                FROM SECAO_MODO_TEXTO s
                JOIN MODELO_MODO_TEXTO m ON s.CODMODELO = m.CODMODELO
                WHERE s.CODSECAO = ? AND m.CODUSUARIO = ?
            """, (codsecao, codusuario))
            secao = cur.fetchone()
            if not secao:
                flash("Seção não encontrada ou você não tem permissão para excluí-la.", "error")
                return redirect(url_for('modelos.visualizar_modelos'))

            codmodelo = secao[0]

            # Excluir associações de variáveis
            cur.execute("DELETE FROM SECAO_VARIAVEL WHERE CODSECAO = ?", (codsecao,))

            # Excluir a seção
            cur.execute("DELETE FROM SECAO_MODO_TEXTO WHERE CODSECAO = ?", (codsecao,))

            conn.commit()
            flash("Seção excluída com sucesso!", "success")
    except Exception as e:
        with get_db() as (conn, _):
            conn.rollback()
        flash(f"Erro ao excluir seção: {str(e)}", "error")

    return redirect(url_for('secoes.visualizar_secoes', codmodelo=codmodelo))

@secoes_bp.route('/ordenar_secoes/<int:codmodelo>', methods=['POST'])
def ordenar_secoes(codmodelo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    codusuario = session['usuario']['codusuario']

    with get_db() as (conn, cur):
        # Verificar se o modelo pertence ao usuário
        cur.execute("SELECT 1 FROM MODELO_MODO_TEXTO WHERE CODMODELO = ? AND CODUSUARIO = ?", (codmodelo, codusuario))
        if not cur.fetchone():
            flash("Modelo não encontrado ou você não tem permissão para acessá-lo.", "error")
            return redirect(url_for('modelos.visualizar_modelos'))

        try:
            # Obter a nova ordem das seções
            ordem_secoes = request.form.getlist('ordem[]')

            # Atualizar a ordem de cada seção
            for ordem, codsecao in enumerate(ordem_secoes, start=1):
                cur.execute("""
                    UPDATE SECAO_MODO_TEXTO
                    SET ORDEM = ?
                    WHERE CODSECAO = ?
                """, (ordem, codsecao))

            conn.commit()
            flash("Ordem das seções atualizada com sucesso!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao atualizar a ordem das seções: {str(e)}", "error")

    return redirect(url_for('secoes.visualizar_secoes', codmodelo=codmodelo))


@secoes_bp.route('/editar_nome_modelo', methods=['POST'])
def editar_nome_modelo():
    if 'usuario' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    try:
        with get_db() as (conn, cur):
            data = request.get_json()
            codmodelo = data.get('codmodelo')
            novo_nome = data.get('nome')

            if not codmodelo or not novo_nome:
                return jsonify({'error': 'Código do modelo ou nome inválido'}), 400

            cur.execute("""
                UPDATE MODELO_MODO_TEXTO
                SET NOME = ?, DTHRULTMODIFICACAO = ?
                WHERE CODMODELO = ?
            """, (novo_nome, datetime.now(), codmodelo))
            
            if cur.rowcount == 0:
                return jsonify({'error': 'Modelo não encontrado'}), 404

            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        with get_db() as (conn, _):
            conn.rollback()
        current_app.logger.error(f"Erro ao atualizar nome do modelo: {str(e)}")
        return jsonify({'error': str(e)}), 500