from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from datetime import datetime

scripts_bp = Blueprint('scripts', __name__)

def get_db():
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        raise Exception("Conexão com o banco de dados não foi inicializada.")
    return conn, cur

@scripts_bp.route('/novo_script', methods=['GET', 'POST'])
def novo_script():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        descricao = request.form['descricao'].strip()
        linguagem = request.form['linguagem'].strip() or None
        caminho_projeto = request.form['caminho_projeto'].strip() or None

        # Validações
        if not nome:
            flash("O nome do script é obrigatório.", "error")
            return redirect(request.url)

        # Verificar se o nome já existe
        cur.execute("SELECT 1 FROM SCRIPTLAUDO WHERE UPPER(NOME) = UPPER(?)", (nome,))
        if cur.fetchone():
            flash("Já existe um script com esse nome.", "error")
            return redirect(request.url)

        try:
            # Inserir o novo script
            cur.execute("""
                INSERT INTO SCRIPTLAUDO (NOME, DESCRICAO, LINGUAGEM, CAMINHO_PROJETO)
                VALUES (?, ?, ?, ?)
                RETURNING CODSCRIPTLAUDO
            """, (nome, descricao, linguagem, caminho_projeto))
            codscriptlaudo = cur.fetchone()[0]
            conn.commit()
            flash("Script cadastrado com sucesso!", "success")
            return redirect(url_for('variaveis.home'))
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao cadastrar script: {str(e)}")
            flash(f"Erro ao cadastrar script: {str(e)}", "error")
            return redirect(request.url)

    return render_template('novo_script.html')

@scripts_bp.route('/visualizar_scripts')
def visualizar_scripts():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    # Configurações de paginação
    itens_por_pagina = 10
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * itens_por_pagina

    # Obter o número total de scripts
    cur.execute("SELECT COUNT(*) FROM SCRIPTLAUDO")
    total_scripts = cur.fetchone()[0]
    total_paginas = (total_scripts + itens_por_pagina - 1) // itens_por_pagina

    # Buscar scripts da página atual
    cur.execute(f"""
        SELECT FIRST {itens_por_pagina} SKIP {offset}
            CODSCRIPTLAUDO, NOME, DESCRICAO, LINGUAGEM, CAMINHO_PROJETO
        FROM SCRIPTLAUDO
        ORDER BY NOME
    """)
    scripts = cur.fetchall()

    scripts_detalhes = []
    for script in scripts:
        codscriptlaudo = script[0]
        # Buscar variáveis vinculadas ao script
        cur.execute("""
            SELECT v.VARIAVEL, v.NOME
            FROM SCRIPTLAUDO_VARIAVEL sv
            JOIN VARIAVEIS v ON sv.CODVARIAVEL = v.CODVARIAVEL
            WHERE sv.CODSCRIPTLAUDO = ?
        """, (codscriptlaudo,))
        variaveis = cur.fetchall()
        scripts_detalhes.append({
            'script': script,
            'variaveis': variaveis
        })

    return render_template('visualizar_scripts.html',
                           scripts_detalhes=scripts_detalhes,
                           pagina=pagina,
                           total_paginas=total_paginas)


@scripts_bp.route('/vincular_variaveis/<int:codscriptlaudo>', methods=['GET', 'POST'])
def vincular_variaveis(codscriptlaudo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()

    # Garantir que session['usuario'] é um dicionário e tem a chave 'codusuario'
    if not isinstance(session['usuario'], dict) or 'codusuario' not in session['usuario']:
        flash("Erro na sessão do usuário. Por favor, faça login novamente.", "error")
        return redirect(url_for('auth.logout'))

    # Buscar informações do script
    cur.execute("SELECT NOME FROM SCRIPTLAUDO WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
    script = cur.fetchone()
    if not script:
        flash("Script não encontrado.", "error")
        return redirect(url_for('scripts.visualizar_scripts'))
    nome_script = script[0]

    if request.method == 'POST':
        variaveis = request.form.getlist('variaveis[]')

        try:
            # Remover vínculos existentes
            cur.execute("DELETE FROM SCRIPTLAUDO_VARIAVEL WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))

            # Adicionar novos vínculos
            for codvariavel in variaveis:
                cur.execute("""
                    INSERT INTO SCRIPTLAUDO_VARIAVEL (CODSCRIPTLAUDO, CODVARIAVEL)
                    VALUES (?, ?)
                """, (codscriptlaudo, codvariavel))

            conn.commit()
            flash("Variáveis vinculadas com sucesso!", "success")
            return redirect(url_for('scripts.visualizar_scripts'))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao vincular variáveis: {str(e)}", "error")
            return redirect(url_for('scripts.vincular_variaveis', codscriptlaudo=codscriptlaudo))

    # Buscar variáveis associadas ao script
    cur.execute("SELECT CODVARIAVEL FROM SCRIPTLAUDO_VARIAVEL WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
    variaveis_associadas = [row[0] for row in cur.fetchall()]

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

    return render_template('vincular_variaveis.html',
                           codscriptlaudo=codscriptlaudo,
                           nome_script=nome_script,
                           variaveis=variaveis_detalhes,
                           variaveis_associadas=variaveis_associadas)