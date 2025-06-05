from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
from datetime import datetime
from get_db import get_db


formulas_bp = Blueprint('formulas', __name__)

@formulas_bp.route('/nova_formula', methods=['GET', 'POST'])
def nova_formula():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            if request.method == 'POST':
                sigla = request.form.get('sigla', '').strip()
                formula = request.form.get('formula', '').strip()

                if not sigla or not formula:
                    flash("Ambos os campos (Sigla e Fórmula) são obrigatórios.", "error")
                    return redirect(request.url)

                # Buscar variável principal pelo nome abreviado (SIGLA)
                cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE SIGLA = ?", (sigla,))
                var_principal = cur.fetchone()
                if not var_principal:
                    flash(f"Variável '{sigla}' não encontrada.", "error")
                    return redirect(request.url)

                codvar = var_principal[0]

                # Inserir a fórmula
                cur.execute("""
                    INSERT INTO FORMULAS (NOME, DESCRICAO, FORMULA, DTHRULTMODIFICACAO, CODUSUARIO)
                    VALUES (?, ?, ?, ?, ?)
                    RETURNING CODFORMULA
                """, (sigla, f"Fórmula para {sigla}", formula, datetime.now(), 4))

                codformula = cur.fetchone()[0]

                # Vincular à variável
                cur.execute("""
                    INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?)
                """, (codformula, codvar, 4, datetime.now()))

                conn.commit()
                flash("Fórmula cadastrada com sucesso!", "success")
                return redirect(url_for('formulas.visualizar_formulas'))

            # Método GET - carregar siglas
            cur.execute("SELECT SIGLA FROM VARIAVEIS ORDER BY SIGLA")
            siglas = [row[0] for row in cur.fetchall()]
            return render_template('nova_formula.html', siglas=siglas)

    except Exception as e:
        current_app.logger.error(f"Erro ao cadastrar nova fórmula: {str(e)}")
        flash(f"Erro ao cadastrar fórmula: {str(e)}", "error")
        return redirect(request.url)
# Dentro de routes/formulas.py

@formulas_bp.route('/formulas')
def visualizar_formulas():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    # Configurações de paginação
    itens_por_pagina = 10
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * itens_por_pagina

    # Filtros
    filtro_sigla = request.args.get('sigla', '').strip()
    filtro_nome = request.args.get('nome', '').strip()
    filtro_formula = request.args.get('formula', '').strip()

    # Montar a consulta com filtros (para a tabela principal de fórmulas)
    query = """
        SELECT F.CODFORMULA, F.NOME, F.FORMULA, V.SIGLA
        FROM FORMULAS F
        JOIN FORMULA_VARIAVEL FV ON FV.CODFORMULA = F.CODFORMULA
        JOIN VARIAVEIS V ON V.CODVARIAVEL = FV.CODVARIAVEL
        WHERE 1=1
    """
    params = []
    if filtro_sigla:
        query += " AND UPPER(V.SIGLA) LIKE UPPER(?)"
        params.append(f"%{filtro_sigla}%")
    if filtro_nome:
        query += " AND UPPER(F.NOME) LIKE UPPER(?)"
        params.append(f"%{filtro_nome}%")
    if filtro_formula:
        query += " AND UPPER(F.FORMULA) LIKE UPPER(?)"
        params.append(f"%{filtro_formula}%")

    query += " GROUP BY F.CODFORMULA, F.NOME, F.FORMULA, V.SIGLA ORDER BY F.NOME"

    # Contagem total para paginação
    count_query = """
        SELECT COUNT(DISTINCT F.CODFORMULA)
        FROM FORMULAS F
        JOIN FORMULA_VARIAVEL FV ON FV.CODFORMULA = F.CODFORMULA
        JOIN VARIAVEIS V ON V.CODVARIAVEL = FV.CODVARIAVEL
        WHERE 1=1
    """
    count_params = []
    if filtro_sigla:
        count_query += " AND UPPER(V.SIGLA) LIKE UPPER(?)"
        count_params.append(f"%{filtro_sigla}%")
    if filtro_nome:
        count_query += " AND UPPER(F.NOME) LIKE UPPER(?)"
        count_params.append(f"%{filtro_nome}%")
    if filtro_formula:
        count_query += " AND UPPER(F.FORMULA) LIKE UPPER(?)"
        count_params.append(f"%{filtro_formula}%")

    try:
        with get_db() as (conn, cur):
            current_app.logger.info(f"Executando contagem: {count_query} com params: {count_params}")
            cur.execute(count_query, count_params)
            total_formulas = cur.fetchone()[0]
            total_paginas = (total_formulas + itens_por_pagina - 1) // itens_por_pagina

            paginated_query = f"""
                SELECT FIRST {itens_por_pagina} SKIP {offset}
                       F.CODFORMULA, F.NOME, F.FORMULA, V.SIGLA
                FROM ({query.replace(" ORDER BY F.NOME", "")}) F_SUB
                ORDER BY F_SUB.NOME
            """

            current_app.logger.info(f"Executando consulta paginada: {query} com LIMIT/OFFSET (simulado por FIRST/SKIP)") 

            final_query_for_display = f"""
                SELECT FIRST {itens_por_pagina} SKIP {offset}
                       * FROM ({query}) AS SubqueryAliasNameOptional
            """

            cur.execute(query.replace("SELECT F.CODFORMULA", f"SELECT FIRST {itens_por_pagina} SKIP {offset} F.CODFORMULA"), params)
            formulas_list = cur.fetchall()

            cur.execute("SELECT SIGLA FROM VARIAVEIS ORDER BY SIGLA")
            siglas_para_modal_list = [row[0] for row in cur.fetchall()]

            # Buscar variáveis detalhadas para as sugestões de autocomplete (lista de dicts)
            cur.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
            variaveis_para_sugestao_list = [{'sigla': row[0], 'nome_clinico': row[1]} for row in cur.fetchall()]

            return render_template('formulas.html',
                                formulas=formulas_list,
                                pagina=pagina,
                                total_paginas=total_paginas,
                                total_formulas=total_formulas,
                                filtro_sigla=filtro_sigla,
                                filtro_nome=filtro_nome,
                                filtro_formula=filtro_formula,
                                siglas_para_modal=siglas_para_modal_list,
                                variaveis_para_sugestao=variaveis_para_sugestao_list)

    except Exception as e:
        current_app.logger.error(f"Erro ao executar consulta em visualizar_formulas: {str(e)}")
        flash(f"Erro ao carregar fórmulas: {str(e)}", "error")
        return redirect(url_for('bibliotecas.biblioteca'))

@formulas_bp.route('/editar_formula/<int:codformula>', methods=['GET', 'POST'])
def editar_formula(codformula):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            if request.method == 'POST':
                nova_formula = request.form['formula']
                cur.execute("""
                    UPDATE FORMULAS 
                    SET FORMULA = ?, DTHRULTMODIFICACAO = ? 
                    WHERE CODFORMULA = ?
                """, (nova_formula, datetime.now(), codformula))
                conn.commit()
                flash("Fórmula atualizada com sucesso!", "success")
                return redirect(url_for('formulas.visualizar_formulas'))

            cur.execute("SELECT FORMULA, NOME FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
            formula = cur.fetchone()
            
            if not formula:
                flash("Fórmula não encontrada.", "error")
                return redirect(url_for('formulas.visualizar_formulas'))

            return render_template('editar_formula.html', 
                                codformula=codformula, 
                                formula=formula[0], 
                                nome=formula[1])

    except Exception as e:
        current_app.logger.error(f"Erro ao editar fórmula {codformula}: {str(e)}")
        flash(f"Erro ao editar fórmula: {str(e)}", "error")
        return redirect(url_for('formulas.visualizar_formulas'))

@formulas_bp.route('/excluir_formula/<int:codformula>', methods=['GET', 'POST'])
def excluir_formula(codformula):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db() as (conn, cur):
            # Buscar informações da fórmula
            cur.execute("SELECT NOME, FORMULA FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
            formula = cur.fetchone()
            
            if not formula:
                flash("Fórmula não encontrada.", "error")
                return redirect(url_for('formulas.visualizar_formulas'))

            if request.method == 'POST':
                # Excluir vínculos primeiro
                cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODFORMULA = ?", (codformula,))
                
                # Excluir a fórmula
                cur.execute("DELETE FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
                
                conn.commit()
                flash("Fórmula excluída com sucesso!", "success")
                return redirect(url_for('formulas.visualizar_formulas'))

            # GET - Mostrar página de confirmação
            return render_template('confirmar_exclusao_formula.html',
                                codformula=codformula,
                                nome=formula[0],
                                formula=formula[1])

    except Exception as e:
        current_app.logger.error(f"Erro ao excluir fórmula {codformula}: {str(e)}")
        flash(f"Erro ao excluir fórmula: {str(e)}", "error")
        return redirect(url_for('formulas.visualizar_formulas'))