from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
from datetime import datetime
import re
import os
import uuid
import subprocess
import json
import uuid
variaveis_bp = Blueprint('variaveis', __name__)

def get_db():
    #from app import conn, cur
    #return conn, cur
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        raise Exception("Conexão com o banco de dados não foi inicializada.")
    return conn, cur
    

def parse_cs_file(file_content):
    """
    Função para parsear o arquivo .cs usando um script C# com Roslyn.
    Retorna uma estrutura de dados com os dados extraídos.
    """
    # Salvar o conteúdo do arquivo em um arquivo temporário
    temp_file = f"temp_{uuid.uuid4()}.cs"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(file_content)

    try:
        # Chamar o script C# para parsear o arquivo
        # Substitua pelo caminho correto do executável gerado
        result = subprocess.run(
        ['/app/ParseCSFile.exe', temp_file],
        capture_output=True,  # Captura a saída padrão e de erro
        text=True,            # Decodifica a saída como texto usando a codificação padrão
        check=True            # Levanta CalledProcessError se o processo retornar um código de saída diferente de zero
    )
        print(f"Saída bruta do script C# (stdout): {result.stdout!r}")  # Usar !r para mostrar a string com detalhes
        print(f"Saída de erro do script C# (stderr): {result.stderr!r}")

        # Parsear o JSON retornado
        try:
            if not result.stdout.strip():
                print("Erro: Saída do script C# está vazia.")
                dados = {"variaveis": [], "formulas": [], "normalidades": []}
            else:
                dados = json.loads(result.stdout)
                print(f"Dados parseados do JSON: {dados}")
        except json.JSONDecodeError as e:
            print(f"Erro ao parsear JSON: {e}")
            dados = {"variaveis": [], "formulas": [], "normalidades": []}

        # Verificar se 'variaveis' está presente e é uma lista
        if "variaveis" not in dados or not isinstance(dados["variaveis"], list):
            print("Erro: 'variaveis' não encontrado ou não é uma lista no JSON retornado.")
            dados["variaveis"] = []
        if "formulas" not in dados or not isinstance(dados["formulas"], list):
            dados["formulas"] = []
        if "normalidades" not in dados or not isinstance(dados["normalidades"], list):
            dados["normalidades"] = []

    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o script C#: {e.stderr}")
        dados = {"variaveis": [], "formulas": [], "normalidades": []}
    except Exception as e:
        print(f"Erro inesperado ao parsear o arquivo: {str(e)}")
        dados = {"variaveis": [], "formulas": [], "normalidades": []}
    finally:
        # Remover o arquivo temporário
        if os.path.exists(temp_file):
            os.remove(temp_file)

    print(f"Dados finais antes de adicionar existe_no_banco: {dados}")

    # Adicionar a flag existe_no_banco
    conn, cur = get_db()
    for variavel in dados["variaveis"]:
        codigo = variavel.get("codigo")
        if not codigo:
            print(f"Erro: Variável sem 'codigo': {variavel}")
            continue
        cur.execute("SELECT 1 FROM VARIAVEIS WHERE UPPER(VARIAVEL) = UPPER(?)", (codigo,))
        existe_no_banco = bool(cur.fetchone())
        variavel["existe_no_banco"] = existe_no_banco
        print(f"Verificação no banco para '{codigo}': Existe = {existe_no_banco}, Tipo = {type(existe_no_banco)}")

    print(f"Dados finais após adicionar existe_no_banco: {dados}")
    return dados

@variaveis_bp.route('/importar_variaveis', methods=['GET', 'POST'])
def importar_variaveis():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash("Nenhum arquivo enviado.", "error")
            return redirect(request.url)
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash("Nenhum arquivo selecionado.", "error")
            return redirect(request.url)
        if not arquivo.filename.endswith('.cs'):
            flash("Apenas arquivos .cs são permitidos.", "error")
            return redirect(request.url)

        # Ler o conteúdo do arquivo
        conteudo = arquivo.read().decode('utf-8', errors='ignore')

        # Parsear o arquivo
        dados = parse_cs_file(conteudo)
        print(f"Dados retornados por parse_cs_file: {dados}")  # Log adicional
        if not dados["variaveis"]:
            flash("Nenhuma variável encontrada no arquivo.", "error")
            return redirect(request.url)

        # Armazenar os dados na sessão para revisão
        session['dados_importacao'] = dados
        print(f"Dados armazenados na sessão: {session['dados_importacao']}")
        return redirect(url_for('variaveis.confirmar_importacao'))

    return render_template('importar_variaveis.html')

@variaveis_bp.route('/confirmar_importacao', methods=['GET', 'POST'])
def confirmar_importacao():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    if 'dados_importacao' not in session:
        flash("Nenhum dado para importar.", "error")
        return redirect(url_for('variaveis.importar_variaveis'))

    dados = session['dados_importacao']
    for variavel in dados["variaveis"]:
        print(f"Dados para o template - Variável: {variavel['codigo']}, Existe no banco: {variavel['existe_no_banco']}, Tipo: {type(variavel['existe_no_banco'])}")

    if request.method == 'POST':
        conn, cur = get_db()
        try:
            variaveis_selecionadas = request.form.getlist('variaveis[]')
            print(f"Variáveis selecionadas: {variaveis_selecionadas}")

            variaveis_inseridas = 0

            for variavel in dados["variaveis"]:
                if variavel["codigo"] not in variaveis_selecionadas:
                    continue

                cur.execute("SELECT CODUNIDADEMEDIDA FROM UNIDADEMEDIDA WHERE DESCRICAO = ?", (variavel["unidade"],))
                unidade = cur.fetchone()
                if not unidade:
                    cur.execute("INSERT INTO UNIDADEMEDIDA (DESCRICAO, STATUS, CODUSUARIO, DTHRULTMODIFICACAO) VALUES (?, ?, ?, ?)",
                                (variavel["unidade"], -1, 4, datetime.now()))
                    cur.execute("SELECT CODUNIDADEMEDIDA FROM UNIDADEMEDIDA WHERE DESCRICAO = ?", (variavel["unidade"],))
                    unidade = cur.fetchone()
                codunidade = unidade[0]
                print(f"Unidade encontrada/inserida: {variavel['unidade']} -> CODUNIDADEMEDIDA: {codunidade}")

                cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE VARIAVEL = ?", (variavel["codigo"],))
                if cur.fetchone():
                    print(f"Variável {variavel['codigo']} já existe no banco, pulando...")
                    continue

                cur.execute("""
                    INSERT INTO VARIAVEIS (NOME, VARIAVEL, SIGLA, ABREVIACAO, DESCRICAO, CODUNIDADEMEDIDA, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING CODVARIAVEL
                """, (variavel["nome"], variavel["codigo"], variavel["sigla"], variavel["abreviacao"], "", codunidade, 4, datetime.now()))
                codvar = cur.fetchone()[0]
                print(f"Variável inserida: CODVARIAVEL: {codvar}, Nome: {variavel['nome']}")

                variaveis_inseridas += 1

                for normalidade in [n for n in dados["normalidades"] if n["variavel"] == variavel["codigo"]]:
                    cur.execute("SELECT CODREFERENCIA FROM REFERENCIA WHERE AUTOR = ? AND ANO = ?", (normalidade["referencia"], "Unknown"))
                    referencia = cur.fetchone()
                    if not referencia:
                        cur.execute("INSERT INTO REFERENCIA (AUTOR, ANO, CODUSUARIO, DTHRULTMODIFICACAO) VALUES (?, ?, ?, ?)",
                                    (normalidade["referencia"], "Unknown", 4, datetime.now()))
                        cur.execute("SELECT CODREFERENCIA FROM REFERENCIA WHERE AUTOR = ? AND ANO = ?", (normalidade["referencia"], "Unknown"))
                        referencia = cur.fetchone()
                    codreferencia = referencia[0]
                    print(f"Referência encontrada/inserida: {normalidade['referencia']} -> CODREFERENCIA: {codreferencia}")

                    cur.execute("""
                        INSERT INTO NORMALIDADE (CODVARIAVEL, CODREFERENCIA, VALORMIN, VALORMAX, SEXO, IDADE_MIN, IDADE_MAX, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (codvar, codreferencia, normalidade["valor_min"], normalidade["valor_max"], normalidade["sexo"],
                          normalidade["idade_min"], normalidade["idade_max"], 4, datetime.now()))
                    print(f"Normalidade inserida para CODVARIAVEL: {codvar}")

                for formula in [f for f in dados["formulas"] if f["variavel"] == variavel["codigo"]]:
                    cur.execute("""
                        INSERT INTO FORMULAS (NOME, DESCRICAO, FORMULA, CASADECIMAIS, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?, ?, ?)
                        RETURNING CODFORMULA
                    """, (variavel["sigla"], f"Fórmula para {variavel['sigla']}", formula["expressao"], formula["casas_decimais"], 4, datetime.now()))
                    codform = cur.fetchone()[0]
                    cur.execute("""
                        INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?)
                    """, (codform, codvar, 4, datetime.now()))
                    print(f"Fórmula inserida: CODFORMULA: {codform}, CODVARIAVEL: {codvar}")

            conn.commit()
            session.pop('dados_importacao', None)

            if variaveis_inseridas > 0:
                flash(f"{variaveis_inseridas} variável(is) importada(s) com sucesso!", "success")
            else:
                flash("Nenhuma variável foi importada, pois todas as selecionadas já existem no banco.", "warning")

        except Exception as e:
            conn.rollback()
            flash(f"Erro ao importar variáveis: {str(e)}", "error")
            print(f"Erro durante a importação: {str(e)}")
        return redirect(url_for('variaveis.visualizar_variaveis'))

    return render_template('confirmar_importacao.html', dados=dados)

@variaveis_bp.route('/')
def home():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("""
        SELECT U.DESCRICAO, COUNT(*) FROM VARIAVEIS V
        JOIN UNIDADEMEDIDA U ON V.CODUNIDADEMEDIDA = U.CODUNIDADEMEDIDA
        GROUP BY U.DESCRICAO
        ORDER BY COUNT(*) DESC
    """)
    variaveis_unidade = cur.fetchall()
    labels1 = [row[0] for row in variaveis_unidade]
    dados1 = [row[1] for row in variaveis_unidade]
    cur.execute("SELECT COUNT(DISTINCT CODVARIAVEL) FROM FORMULA_VARIAVEL")
    com_formula = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM VARIAVEIS")
    total_variaveis = cur.fetchone()[0]
    sem_formula = total_variaveis - com_formula
    cur.execute("SELECT v.CODUNIDADEMEDIDA, COUNT(*) FROM VARIAVEIS v GROUP BY 1 ORDER BY CODUNIDADEMEDIDA")
    decimais = cur.fetchall()
    labels2 = [str(row[0]) for row in decimais]
    dados2 = [row[1] for row in decimais]
    cur.execute("SELECT COUNT(DISTINCT CODVARIAVEL) FROM NORMALIDADE")
    com_normalidade = cur.fetchone()[0]
    sem_normalidade = total_variaveis - com_normalidade
    return render_template('index.html',
        labels1=labels1, dados1=dados1,
        labels2=labels2, dados2=dados2,
        com_formula=com_formula, sem_formula=sem_formula,
        com_normalidade=com_normalidade, sem_normalidade=sem_normalidade)

@variaveis_bp.route('/visualizar_variaveis')
def visualizar_variaveis():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()

    # Configurações de paginação
    itens_por_pagina = 10
    pagina = request.args.get('page', 1, type=int)  # Obter o número da página da query string, padrão é 1
    offset = (pagina - 1) * itens_por_pagina

    # Obter o número total de variáveis para calcular o número de páginas
    cur.execute("SELECT COUNT(*) FROM VARIAVEIS")
    total_variaveis = cur.fetchone()[0]
    total_paginas = (total_variaveis + itens_por_pagina - 1) // itens_por_pagina  # Arredonda para cima

    # Consulta com LIMIT e OFFSET para buscar apenas as variáveis da página atual
    cur.execute(f"""
        SELECT FIRST {itens_por_pagina} SKIP {offset} 
            CODVARIAVEL, NOME, VARIAVEL, SIGLA, ABREVIACAO 
        FROM VARIAVEIS 
        ORDER BY NOME
    """)
    variaveis = cur.fetchall()

    variaveis_detalhes = []
    for variavel in variaveis:
        codvariavel = variavel[0]
        cur.execute("""
            SELECT f.FORMULA, f.CASADECIMAIS
            FROM FORMULAS f
            JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
            WHERE fv.CODVARIAVEL = ?
        """, (codvariavel,))
        formula = cur.fetchone()
        print(f"Variável {codvariavel} - Fórmula: {formula}")  # Log de depuração
        cur.execute("""
            SELECT tl.DESCRICAO, el.EQUACAO, r.AUTOR, r.ANO
            FROM EQUACOES_LINGUAGEM el
            JOIN TIPOLINGUAGEM tl ON el.CODLINGUAGEM = tl.CODLINGUAGEM
            JOIN FORMULA_VARIAVEL fv ON el.CODFORMULA = fv.CODFORMULA
            LEFT JOIN REFERENCIA r ON el.CODREFERENCIA = r.CODREFERENCIA
            WHERE fv.CODVARIAVEL = ?
        """, (codvariavel,))
        equacoes = cur.fetchall()
        cur.execute("""
            SELECT n.SEXO, n.VALORMIN, n.VALORMAX, n.IDADE_MIN, n.IDADE_MAX, r.AUTOR, r.ANO
            FROM NORMALIDADE n
            LEFT JOIN REFERENCIA r ON n.CODREFERENCIA = r.CODREFERENCIA
            WHERE n.CODVARIAVEL = ?
        """, (codvariavel,))
        normalidade = cur.fetchone()
        cur.execute("SELECT ALTERNATIVA FROM VARIAVEIS_ALTERNATIVAS WHERE CODVARIAVEL = ? ORDER BY ALTERNATIVA", (codvariavel,))
        alternativas = [row[0] for row in cur.fetchall()]
        variaveis_detalhes.append({
            'variavel': variavel,
            'formula': formula,
            'equacoes': equacoes,
            'normalidade': normalidade,
            'alternativas': alternativas
        })

    return render_template('visualizar_variaveis.html', 
                           variaveis_detalhes=variaveis_detalhes,
                           pagina=pagina,
                           total_paginas=total_paginas)

@variaveis_bp.route('/nova_variavel', methods=['GET', 'POST'])
def nova_variavel():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        sigla = request.form['sigla'].strip().upper()
        descricao = request.form['descricao']
        unidade = request.form['unidade']
        casas_decimais = request.form['casas_decimais']
        variavel = request.form['variavel']
        alternativas = request.form.getlist('alternativas[]')
        if not sigla.startswith("VR_"):
            flash(("error", "A variável deve começar com 'VR_'"))
            return redirect(request.url)
        if variavel.startswith("<<") or variavel.endswith(">>"):
            flash(("error", "A variável não pode começar com '<<' ou terminar com '>>'"))
            return redirect(request.url)
        cur.execute("SELECT 1 FROM VARIAVEIS WHERE UPPER(VARIAVEL) = ?", (variavel,))
        if cur.fetchone():
            flash("Já existe um registro no banco com essa variável.", "error")
            return redirect(request.url)
        cur.execute("""
            INSERT INTO VARIAVEIS (NOME, VARIAVEL, SIGLA, DESCRICAO, CODUNIDADEMEDIDA, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING CODVARIAVEL
        """, (nome, variavel, sigla, descricao, unidade, 4, datetime.now()))
        codvar = cur.fetchone()[0]
        for alternativa in alternativas:
            if alternativa.strip():
                cur.execute("""
                    INSERT INTO VARIAVEIS_ALTERNATIVAS (CODVARIAVEL, ALTERNATIVA, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?)
                """, (codvar, alternativa.strip(), 4, datetime.now()))
        if 'possui_formula' in request.form:
            formula = request.form['formula']
            cur.execute("""
                INSERT INTO FORMULAS (NOME, DESCRICAO, FORMULA, CASADECIMAIS, CODUSUARIO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING CODFORMULA
            """, (sigla, f"Fórmula para {sigla}", formula, casas_decimais, 4, datetime.now()))
            codform = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?)
            """, (codform, codvar, 4, datetime.now()))
            # Salvar equações em diferentes linguagens
            equacoes_linguagem = request.form.getlist('equacoes_linguagem[]')
            equacoes_referencia = request.form.getlist('equacoes_referencia[]')
            equacoes_texto = request.form.getlist('equacoes_texto[]')
            for codlinguagem, codreferencia, equacao in zip(equacoes_linguagem, equacoes_referencia, equacoes_texto):
                if codlinguagem and equacao.strip():  # Ignorar se linguagem ou equação estiverem vazias
                    codreferencia = codreferencia if codreferencia else None
                    cur.execute("""
                        INSERT INTO EQUACOES_LINGUAGEM (CODFORMULA, CODLINGUAGEM, EQUACAO, CODREFERENCIA, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (codform, codlinguagem, equacao.strip(), codreferencia, 4, datetime.now()))
        if 'possui_normalidade' in request.form:
            sexo = request.form['sexo']
            valormin = request.form['valormin'] or None
            valormax = request.form['valormax'] or None
            idade_min = request.form['idade_min'] or None
            idade_max = request.form['idade_max'] or None
            referencia = request.form['referencia'] or None
            cur.execute("""
                INSERT INTO NORMALIDADE (CODVARIAVEL, CODREFERENCIA, VALORMIN, VALORMAX, SEXO, IDADE_MIN, IDADE_MAX, CODUSUARIO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codvar, referencia, valormin, valormax, sexo, idade_min, idade_max, 4, datetime.now()))
        conn.commit()
        flash(("success", "Variável, alternativas, equações e normalidade cadastradas com sucesso!"))
        return redirect(url_for('variaveis.nova_variavel'))
    # Buscar linguagens disponíveis
    cur.execute("SELECT CODLINGUAGEM, NOME FROM TIPOLINGUAGEM ORDER BY DESCRICAO")
    linguagens = cur.fetchall()
    cur.execute("SELECT CODUNIDADEMEDIDA, DESCRICAO FROM UNIDADEMEDIDA ORDER BY DESCRICAO")
    unidades = cur.fetchall()
    cur.execute("SELECT CODREFERENCIA, AUTOR, ANO FROM REFERENCIA ORDER BY ANO DESC")
    referencias = cur.fetchall()
    cur.execute("SELECT VARIAVEL, NOME FROM VARIAVEIS ORDER BY VARIAVEL")
    variaveis_existentes = [(row[0], row[1]) for row in cur.fetchall()]
    return render_template('nova_variavel.html', 
                         unidades=unidades, 
                         referencias=referencias, 
                         variaveis_existentes=variaveis_existentes,
                         linguagens=linguagens)


@variaveis_bp.route('/editar_variavel/<int:codvariavel>', methods=['GET', 'POST'])
def editar_variavel(codvariavel):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        sigla = request.form['sigla'].strip().upper()
        abreviacao = request.form['abreviacao']
        casas_decimais = request.form['casas_decimais']
        descricao = request.form['descricao']
        codunidade = request.form['unidade']
        variavel = request.form['variavel']
        alternativas = request.form.getlist('alternativas[]')
        if not sigla.startswith("VR_"):
            flash(("error", "A variável deve começar com 'VR_'"))
            return redirect(request.url)
        if variavel.startswith("<<") or variavel.endswith(">>"):
            flash(("error", "A variável não pode começar com '<<' ou terminar com '>>'"))
            return redirect(request.url)
        cur.execute("SELECT 1 FROM VARIAVEIS WHERE UPPER(VARIAVEL) = ? AND CODVARIAVEL != ?", (variavel, codvariavel))
        if cur.fetchone():
            flash("Já existe um registro no banco com essa variável.", "error")
            return redirect(request.url)
        cur.execute("""
            UPDATE VARIAVEIS SET
            NOME = ?, VARIAVEL=?, SIGLA = ?, ABREVIACAO = ?, CASASDECIMAIS = ?, DESCRICAO = ?, CODUNIDADEMEDIDA = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
            WHERE CODVARIAVEL = ?
        """, (nome, variavel, sigla, abreviacao, casas_decimais, descricao, codunidade, datetime.now(), 4, codvariavel))
        # Atualizar variáveis alternativas
        cur.execute("DELETE FROM VARIAVEIS_ALTERNATIVAS WHERE CODVARIAVEL = ?", (codvariavel,))
        for alternativa in alternativas:
            if alternativa.strip():
                cur.execute("""
                    INSERT INTO VARIAVEIS_ALTERNATIVAS (CODVARIAVEL, ALTERNATIVA, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?)
                """, (codvariavel, alternativa.strip(), 4, datetime.now()))
        if 'formula' in request.form:
            formula = request.form['formula']
            casas_formula = request.form.get('formula_casas_decimais', 2)
            cur.execute("""
                UPDATE FORMULAS SET
                FORMULA = ?, CASADECIMAIS = ?, DTHRULTMODIFICACAO = ?
                WHERE CODFORMULA = (
                  SELECT CODFORMULA FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?
                )
            """, (formula, casas_formula, datetime.now(), codvariavel))
            # Atualizar equações em diferentes linguagens
            cur.execute("DELETE FROM EQUACOES_LINGUAGEM WHERE CODFORMULA = (SELECT CODFORMULA FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?)", (codvariavel,))
            equacoes_linguagem = request.form.getlist('equacoes_linguagem[]')
            equacoes_referencia = request.form.getlist('equacoes_referencia[]')
            equacoes_texto = request.form.getlist('equacoes_texto[]')
            for codlinguagem, codreferencia, equacao in zip(equacoes_linguagem, equacoes_referencia, equacoes_texto):
                if codlinguagem and equacao.strip():
                    codreferencia = codreferencia if codreferencia else None
                    cur.execute("""
                        INSERT INTO EQUACOES_LINGUAGEM (CODFORMULA, CODLINGUAGEM, EQUACAO, CODREFERENCIA, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES ((SELECT CODFORMULA FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?), ?, ?, ?, ?, ?)
                    """, (codvariavel, codlinguagem, equacao.strip(), codreferencia, 4, datetime.now()))
        if 'sexo' in request.form:
            sexo = request.form['sexo']
            valormin = request.form['valormin'] or None
            valormax = request.form['valormax'] or None
            idade_min = request.form['idade_min'] or None
            idade_max = request.form['idade_max'] or None
            codreferencia = request.form['referencia'] or None
            cur.execute("""
                UPDATE NORMALIDADE SET
                SEXO = ?, VALORMIN = ?, VALORMAX = ?, IDADE_MIN = ?, IDADE_MAX = ?, CODREFERENCIA = ?, DTHRULTMODIFICACAO = ?
                WHERE CODVARIAVEL = ?
            """, (sexo, valormin, valormax, idade_min, idade_max, codreferencia, datetime.now(), codvariavel))
        conn.commit()
        flash("Alterações salvas com sucesso!", "success")
        return redirect(url_for('variaveis.visualizar_variaveis'))
    # Buscar dados atuais da variável
    cur.execute("""
        SELECT v.NOME, v.VARIAVEL, v.SIGLA, v.ABREVIACAO, v.CASASDECIMAIS, v.DESCRICAO, v.CODUNIDADEMEDIDA,
               f.FORMULA, f.CASADECIMAIS as FORMULA_CASAS,
               n.SEXO, n.VALORMIN, n.VALORMAX, n.IDADE_MIN, n.IDADE_MAX, n.CODREFERENCIA
        FROM VARIAVEIS v
        LEFT JOIN FORMULA_VARIAVEL fv ON v.CODVARIAVEL = fv.CODVARIAVEL
        LEFT JOIN FORMULAS f ON fv.CODFORMULA = f.CODFORMULA
        LEFT JOIN NORMALIDADE n ON v.CODVARIAVEL = n.CODVARIAVEL
        WHERE v.CODVARIAVEL = ?
    """, (codvariavel,))
    variavel = cur.fetchone()
    # Buscar variáveis alternativas
    cur.execute("SELECT ALTERNATIVA FROM VARIAVEIS_ALTERNATIVAS WHERE CODVARIAVEL = ? ORDER BY ALTERNATIVA", (codvariavel,))
    alternativas = [row[0] for row in cur.fetchall()]
    # Buscar equações em diferentes linguagens
    cur.execute("""
        SELECT EL.CODLINGUAGEM, el.EQUACAO, el.CODREFERENCIA
        FROM EQUACOES_LINGUAGEM el
        JOIN FORMULA_VARIAVEL fv ON el.CODFORMULA = fv.CODFORMULA
        WHERE fv.CODVARIAVEL = ?
    """, (codvariavel,))
    equacoes = [{'codlinguagem': row[0], 'equacao': row[1], 'codreferencia': row[2]} for row in cur.fetchall()]
    # Buscar opções para os selects
    cur.execute("SELECT CODLINGUAGEM, NOME FROM TIPOLINGUAGEM ORDER BY DESCRICAO")
    linguagens = cur.fetchall()
    cur.execute("SELECT CODUNIDADEMEDIDA, DESCRICAO FROM UNIDADEMEDIDA ORDER BY DESCRICAO")
    unidades = cur.fetchall()
    cur.execute("SELECT CODREFERENCIA, AUTOR, ANO FROM REFERENCIA ORDER BY ANO DESC")
    referencias = cur.fetchall()
    cur.execute("SELECT VARIAVEL, NOME FROM VARIAVEIS ORDER BY VARIAVEL")
    variaveis_existentes = [(row[0], row[1]) for row in cur.fetchall()]
    return render_template('editar_variavel.html',
                         variavel=variavel,
                         alternativas=alternativas,
                         equacoes=equacoes,
                         unidades=unidades,
                         referencias=referencias,
                         codvariavel=codvariavel,
                         variaveis_existentes=variaveis_existentes,
                         linguagens=linguagens)



@variaveis_bp.route('/excluir_variavel/<int:codvariavel>', methods=["POST"])
def excluir_variavel(codvariavel):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("SELECT CODFORMULA FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
    formulas = cur.fetchall()
    cur.execute("SELECT SEXO, VALORMIN, VALORMAX, IDADE_MIN, IDADE_MAX, CODREFERENCIA FROM NORMALIDADE WHERE CODVARIAVEL = ?", (codvariavel,))
    normalidades = cur.fetchall()
    if formulas or normalidades:
        session['exclusao_variavel'] = {
            'codvariavel': codvariavel,
            'formulas': [f[0] for f in formulas],
            'normalidades': [{
                'sexo': n[0],
                'valormin': n[1],
                'valormax': n[2],
                'idade_min': n[3],
                'idade_max': n[4],
                'codreferencia': n[5]
            } for n in normalidades]
        }
        return redirect(url_for('variaveis.confirmar_exclusao_variavel'))
    cur.execute("DELETE FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
    conn.commit()
    flash("Variável excluída com sucesso!", "success")
    return redirect(url_for('variaveis.visualizar_variaveis'))

@variaveis_bp.route('/confirmar_exclusao_variavel', methods=['GET', 'POST'])
def confirmar_exclusao_variavel():
    if 'exclusao_variavel' not in session:
        return redirect(url_for('variaveis.home'))
    conn, cur = get_db()
    data = session['exclusao_variavel']
    codvar = data['codvariavel']
    formulas = data['formulas']
    normalidades = data['normalidades']
    if request.method == 'POST':
        cur.execute("DELETE FROM NORMALIDADE WHERE CODVARIAVEL = ?", (codvar,))
        for codformula in formulas:
            cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODFORMULA = ?", (codformula,))
            cur.execute("DELETE FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
        cur.execute("DELETE FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvar,))
        conn.commit()
        session.pop('exclusao_variavel')
        flash("Variável, fórmulas e normalidades vinculadas excluídas com sucesso!", "success")
        return redirect(url_for('variaveis.home'))
    return render_template('confirmar_exclusao_variavel.html', 
                         codvariavel=codvar, 
                         formulas=formulas, 
                         normalidades=normalidades)

@variaveis_bp.route('/verificar_vinculo_variavel/<int:codvariavel>')
def verificar_vinculo_variavel(codvariavel):
    conn, cur = get_db()
    cur.execute("SELECT COUNT(*) FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
    total_formulas = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM NORMALIDADE WHERE CODVARIAVEL = ?", (codvariavel,))
    total_normalidades = cur.fetchone()[0]
    return {"vinculada": (total_formulas > 0 or total_normalidades > 0), 
            "total_formulas": total_formulas, 
            "total_normalidades": total_normalidades}