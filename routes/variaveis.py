from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app,jsonify
from werkzeug.utils import secure_filename
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
        # Obter o caminho do executável a partir de uma variável de ambiente
        parse_cs_executable = os.environ.get('PARSE_CS_EXECUTABLE', '/app/ParseCSFile.exe')
        # Normalizar o caminho para o sistema operacional atual
        parse_cs_executable = os.path.normpath(parse_cs_executable)
        current_app.logger.info(f"Usando executável ParseCSFile em: {parse_cs_executable}")

        # Verificar se o executável existe
        if not os.path.exists(parse_cs_executable):
            current_app.logger.error(f"Executável não encontrado no caminho: {parse_cs_executable}")
            raise FileNotFoundError(f"Executável não encontrado: {parse_cs_executable}")

        # Chamar o script C# para parsear o arquivo
        result = subprocess.run(
            [parse_cs_executable, temp_file],
            capture_output=True,
            text=True,
            check=True
        )
        current_app.logger.debug(f"Saída bruta do script C# (stdout): {result.stdout!r}")
        current_app.logger.debug(f"Saída de erro do script C# (stderr): {result.stderr!r}")

        # Parsear o JSON retornado
        try:
            if not result.stdout.strip():
                print("Erro: Saída do script C# está vazia.")
                dados = {"variaveis": [], "formulas": [], "normalidades": []}
            else:
                dados = json.loads(result.stdout)
                current_app.logger.debug(f"Dados parseados do JSON: {dados}")
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
        current_app.logger.error(f"Erro ao executar o script C#: {e.stderr}")
        dados = {"variaveis": [], "formulas": [], "normalidades": []}
    except Exception as e:
        current_app.logger.error(f"Erro inesperado ao parsear o arquivo: {str(e)}")
        dados = {"variaveis": [], "formulas": [], "normalidades": []}
    finally:
        # Remover o arquivo temporário
        if os.path.exists(temp_file):
            os.remove(temp_file)

    current_app.logger.debug(f"Dados finais antes de adicionar existe_no_banco: {dados}")

    # Adicionar a flag existe_no_banco
    conn, cur = get_db()
    for variavel in dados["variaveis"]:
        codigo = variavel.get("codigo")
        if not codigo:
            current_app.logger.error(f"Erro: Variável sem 'codigo': {variavel}")
            continue
        cur.execute("SELECT 1 FROM VARIAVEIS WHERE UPPER(VARIAVEL) = UPPER(?)", (codigo,))
        existe_no_banco = bool(cur.fetchone())
        variavel["existe_no_banco"] = existe_no_banco
        current_app.logger.debug(f"Verificação no banco para '{codigo}': Existe = {existe_no_banco}, Tipo = {type(existe_no_banco)}")

    current_app.logger.debug(f"Dados finais após adicionar existe_no_banco: {dados}")
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
        current_app.logger.info(f"Dados retornados por parse_cs_file: {dados}")
        if not dados["variaveis"]:
            flash("Nenhuma variável encontrada no arquivo.", "error")
            return redirect(request.url)

        # Armazenar os dados na sessão para revisão
        session['dados_importacao'] = dados
        current_app.logger.info(f"Dados armazenados na sessão: {session['dados_importacao']}")
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
        current_app.logger.info(f"Dados para o template - Variável: {variavel['codigo']}, Existe no banco: {variavel['existe_no_banco']}, Tipo: {type(variavel['existe_no_banco'])}")

    if request.method == 'POST':
        conn, cur = get_db()
        try:
            variaveis_selecionadas = request.form.getlist('variaveis[]')
            current_app.logger.info(f"Variáveis selecionadas: {variaveis_selecionadas}")

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
                current_app.logger.info(f"Unidade encontrada/inserida: {variavel['unidade']} -> CODUNIDADEMEDIDA: {codunidade}")

                cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE VARIAVEL = ?", (variavel["codigo"],))
                if cur.fetchone():
                    current_app.logger.info(f"Variável {variavel['codigo']} já existe no banco, pulando...")
                    continue

                cur.execute("""
                    INSERT INTO VARIAVEIS (NOME, VARIAVEL, SIGLA, ABREVIACAO, DESCRICAO, CODUNIDADEMEDIDA, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING CODVARIAVEL
                """, (variavel["nome"], variavel["codigo"], variavel["sigla"], variavel["abreviacao"], "", codunidade, 4, datetime.now()))
                codvar = cur.fetchone()[0]
                current_app.logger.info(f"Variável inserida: CODVARIAVEL: {codvar}, Nome: {variavel['nome']}")

                variaveis_inseridas += 1

                for normalidade in [n for n in dados["normalidades"] if n["variavel"] == variavel["codigo"]]:
                    cur.execute("SELECT CODREFERENCIA FROM REFERENCIA WHERE TITULO = ? AND ANO = ?", (normalidade["referencia"], "Unknown"))
                    referencia = cur.fetchone()
                    if not referencia:
                        cur.execute("INSERT INTO REFERENCIA (TITULO, ANO, CODUSUARIO, DTHRULTMODIFICACAO) VALUES (?, ?, ?, ?)",
                                    (normalidade["referencia"], "Unknown", 4, datetime.now()))
                        cur.execute("SELECT CODREFERENCIA FROM REFERENCIA WHERE TITULO = ? AND ANO = ?", (normalidade["referencia"], "Unknown"))
                        referencia = cur.fetchone()
                    codreferencia = referencia[0]
                    current_app.logger.info(f"Referência encontrada/inserida: {normalidade['referencia']} -> CODREFERENCIA: {codreferencia}")

                    cur.execute("""
                        INSERT INTO NORMALIDADE (CODVARIAVEL, CODREFERENCIA, VALORMIN, VALORMAX, SEXO, IDADE_MIN, IDADE_MAX, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (codvar, codreferencia, normalidade["valor_min"], normalidade["valor_max"], normalidade["sexo"],
                          normalidade["idade_min"], normalidade["idade_max"], 4, datetime.now()))
                    current_app.logger.info(f"Normalidade inserida para CODVARIAVEL: {codvar}")

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
                    current_app.logger.info(f"Fórmula inserida: CODFORMULA: {codform}, CODVARIAVEL: {codvar}")

            conn.commit()
            session.pop('dados_importacao', None)

            if variaveis_inseridas > 0:
                flash(f"{variaveis_inseridas} variável(is) importada(s) com sucesso!", "success")
            else:
                flash("Nenhuma variável foi importada, pois todas as selecionadas já existem no banco.", "warning")

        except Exception as e:
            conn.rollback()
            flash(f"Erro ao importar variáveis: {str(e)}", "error")
            current_app.logger.error(f"Erro durante a importação: {str(e)}")
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
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * itens_por_pagina

    # Filtro de variável
    variavel_filtro = request.args.get('variavel', '').strip()

    # Consulta com filtro
    query = """
        SELECT CODVARIAVEL, NOME, VARIAVEL, SIGLA, ABREVIACAO
        FROM VARIAVEIS
        WHERE 1=1
    """
    params = []
    if variavel_filtro:
        query += " AND UPPER(VARIAVEL) LIKE UPPER(?)"
        params.append(f"%{variavel_filtro}%")
    query += " ORDER BY NOME"

    # Contagem total
    count_query = "SELECT COUNT(*) FROM VARIAVEIS WHERE 1=1"
    if variavel_filtro:
        count_query += " AND UPPER(VARIAVEL) LIKE UPPER(?)"
    cur.execute(count_query, params)
    total_variaveis = cur.fetchone()[0]
    total_paginas = (total_variaveis + itens_por_pagina - 1) // itens_por_pagina

    # Consulta paginada
    paginated_query = f"""
        SELECT FIRST {itens_por_pagina} SKIP {offset}
            CODVARIAVEL, NOME, VARIAVEL, SIGLA, ABREVIACAO
        FROM ({query})
    """
    cur.execute(paginated_query, params)
    variaveis = cur.fetchall()

    variaveis_detalhes = []
    for variavel in variaveis:
        codvariavel = variavel[0]
        # Fórmula
        cur.execute("""
            SELECT f.FORMULA, f.CASADECIMAIS
            FROM FORMULAS f
            JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
            WHERE fv.CODVARIAVEL = ?
        """, (codvariavel,))
        formula = cur.fetchone()

        # Equações
        cur.execute("""
            SELECT tl.DESCRICAO, el.EQUACAO, LIST(a.NOME, ', ') AS AUTORES, r.ANO
            FROM EQUACOES_LINGUAGEM el
            JOIN TIPOLINGUAGEM tl ON el.CODLINGUAGEM = tl.CODLINGUAGEM
            JOIN FORMULA_VARIAVEL fv ON el.CODFORMULA = fv.CODFORMULA
            LEFT JOIN REFERENCIA r ON el.CODREFERENCIA = r.CODREFERENCIA
            LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
            LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
            WHERE fv.CODVARIAVEL = ?
            GROUP BY tl.DESCRICAO, el.EQUACAO, r.ANO
        """, (codvariavel,))
        equacoes = cur.fetchall()

        # Normalidade
        cur.execute("""
            SELECT n.SEXO, n.VALORMIN, n.VALORMAX, n.IDADE_MIN, n.IDADE_MAX, LIST(a.NOME, ', ') AS AUTORES, r.ANO
            FROM NORMALIDADE n
            LEFT JOIN REFERENCIA r ON n.CODREFERENCIA = r.CODREFERENCIA
            LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
            LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
            WHERE n.CODVARIAVEL = ?
            GROUP BY n.SEXO, n.VALORMIN, n.VALORMAX, n.IDADE_MIN, n.IDADE_MAX, r.ANO
        """, (codvariavel,))
        normalidade = cur.fetchone()

        # Alternativas
        cur.execute("SELECT ALTERNATIVA FROM VARIAVEIS_ALTERNATIVAS WHERE CODVARIAVEL = ? ORDER BY ALTERNATIVA", (codvariavel,))
        alternativas = [row[0] for row in cur.fetchall()]

        # Scripts
        cur.execute("""
            SELECT s.CODSCRIPTLAUDO, s.NOME
            FROM SCRIPTLAUDO_VARIAVEL sv
            JOIN SCRIPTLAUDO s ON sv.CODSCRIPTLAUDO = s.CODSCRIPTLAUDO
            WHERE sv.CODVARIAVEL = ?
        """, (codvariavel,))
        scripts = cur.fetchall()

        # Anexos
        cur.execute("""
            SELECT a.CODANEXO, a.TIPO_ANEXO, a.CAMINHO, a.LINK, a.DESCRICAO, LIST(aut.NOME, ', ') AS AUTORES, r.ANO
            FROM ANEXO_VARIAVEL_FORMULA avf
            JOIN ANEXOS a ON avf.COD_ANEXO = a.CODANEXO
            LEFT JOIN REFERENCIA r ON avf.COD_REFERENCIA = r.CODREFERENCIA
            LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
            LEFT JOIN AUTORES aut ON ra.CODAUTOR = aut.CODAUTOR
            WHERE avf.CODVARIAVEL = ?
            GROUP BY a.CODANEXO, a.TIPO_ANEXO, a.CAMINHO, a.LINK, a.DESCRICAO, r.ANO
        """, (codvariavel,))
        anexos = [{'cod_anexo': row[0], 'tipo_anexo': row[1], 'caminho': row[2] or row[3], 'descricao': row[4], 
                   'referencia': {'autores': row[5], 'ano': row[6]} if row[5] else None} for row in cur.fetchall()]

        variaveis_detalhes.append({
            'variavel': variavel,
            'formula': formula,
            'equacoes': equacoes,
            'normalidade': normalidade,
            'alternativas': alternativas,
            'scripts': scripts,
            'anexos': anexos
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
    codusuario = session['usuario']['codusuario']

    if request.method == 'POST':
        nome = request.form['nome'].strip()
        variavel = request.form['variavel'].strip()
        sigla = request.form['sigla'].strip().upper()
        abreviacao = request.form['abreviacao'].strip()
        descricao = request.form['descricao'].strip() or None
        unidade = request.form['unidade']
        casas_decimais = request.form['casas_decimais']
        possui_formula = 'possui_formula' in request.form
        possui_normalidade = 'possui_normalidade' in request.form
        alternativas = request.form.getlist('alternativas[]')
        scripts = request.form.getlist('scripts[]')
        formula = request.form.get('formula', '').strip() or None
        equacoes_linguagem = request.form.getlist('equacoes_linguagem[]')
        equacoes_referencia = request.form.getlist('equacoes_referencia[]')
        equacoes_texto = request.form.getlist('equacoes_texto[]')
        sexo = request.form.getlist('sexo[]')
        idade_min = request.form.get('idade_min', '').strip() or None
        idade_max = request.form.get('idade_max', '').strip() or None
        referencia_normalidade = request.form.get('referencia', '').strip() or None

        # Normalidade
        normalidades = []
        if possui_normalidade and sexo:
            if len(sexo) == 2:  # Ambos os sexos selecionados
                valormin_m = request.form.get('valormin_m', '').strip() or None
                valormax_m = request.form.get('valormax_m', '').strip() or None
                valormin_f = request.form.get('valormin_f', '').strip() or None
                valormax_f = request.form.get('valormax_f', '').strip() or None
                if not (valormin_m and valormax_m and valormin_f and valormax_f):
                    flash("Valores mínimos e máximos são obrigatórios para ambos os sexos.", "error")
                    return redirect(request.url)
                normalidades.append(('M', valormin_m, valormax_m))
                normalidades.append(('F', valormin_f, valormax_f))
            elif len(sexo) == 1:  # Apenas um sexo
                valormin = request.form.get('valormin', '').strip() or None
                valormax = request.form.get('valormax', '').strip() or None
                if not (valormin and valormax):
                    flash("Valores mínimo e máximo são obrigatórios.", "error")
                    return redirect(request.url)
                normalidades.append((sexo[0], valormin, valormax))
            else:
                flash("Pelo menos um sexo deve ser selecionado.", "error")
                return redirect(request.url)

        # Validações
        if not variavel.startswith('VR_'):
            flash("A Variável deve começar com 'VR_'.", "error")
            return redirect(request.url)

        cur.execute("SELECT 1 FROM VARIAVEIS WHERE UPPER(SIGLA) = UPPER(?)", (sigla,))
        if cur.fetchone():
            flash("Já existe uma variável com essa sigla.", "error")
            return redirect(request.url)

        try:
            # Inserir a variável
            cur.execute("""
                INSERT INTO VARIAVEIS (NOME, VARIAVEL, SIGLA, ABREVIACAO, DESCRICAO, CODUNIDADEMEDIDA, CASASDECIMAIS)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING CODVARIAVEL
            """, (nome, variavel, sigla, abreviacao, descricao, unidade, casas_decimais))
            codvariavel = cur.fetchone()[0]

            # Inserir alternativas
            for alternativa in alternativas:
                if alternativa.strip():
                    cur.execute("INSERT INTO VARIAVEIS_ALTERNATIVAS (CODVARIAVEL, ALTERNATIVA) VALUES (?, ?)", 
                               (codvariavel, alternativa.strip()))

            # Inserir scripts vinculados
            for codscript in scripts:
                if codscript:
                    cur.execute("INSERT INTO SCRIPTLAUDO_VARIAVEL (CODSCRIPTLAUDO, CODVARIAVEL) VALUES (?, ?)", 
                               (codscript, codvariavel))

            # Inserir fórmula
            if possui_formula and formula:
                cur.execute("""
                    INSERT INTO FORMULAS (FORMULA, CASADECIMAIS, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?)
                    RETURNING CODFORMULA
                """, (formula, casas_decimais, datetime.now()))
                codformula = cur.fetchone()[0]

                cur.execute("INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL) VALUES (?, ?)", 
                           (codformula, codvariavel))

                # Inserir equações
                for linguagem, referencia, texto in zip(equacoes_linguagem, equacoes_referencia, equacoes_texto):
                    if linguagem and texto:
                        cur.execute("INSERT INTO EQUACOES_LINGUAGEM (CODFORMULA, CODLINGUAGEM, CODREFERENCIA, EQUACAO) VALUES (?, ?, ?, ?)", 
                                   (codformula, linguagem, referencia or None, texto.strip()))

            # Inserir normalidade
            if normalidades:
                for sexo, valormin, valormax in normalidades:
                    cur.execute("""
                        INSERT INTO NORMALIDADE (CODVARIAVEL, SEXO, VALORMIN, VALORMAX, IDADE_MIN, IDADE_MAX, CODREFERENCIA)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (codvariavel, sexo, valormin, valormax, idade_min, idade_max, referencia_normalidade or None))

            conn.commit()
            flash("Variável cadastrada com sucesso!", "success")
            return redirect(url_for('variaveis.visualizar_variaveis'))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao cadastrar variável: {str(e)}", "error")
            return redirect(request.url)

    # Buscar unidades de medida
    cur.execute("SELECT CODUNIDADEMEDIDA, DESCRICAO FROM UNIDADEMEDIDA ORDER BY DESCRICAO")
    unidades = cur.fetchall()

    # Buscar scripts
    cur.execute("SELECT CODSCRIPTLAUDO, NOME FROM SCRIPTLAUDO ORDER BY NOME")
    scripts = cur.fetchall()

    # Buscar variáveis existentes
    cur.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY NOME")
    variaveis_existentes = cur.fetchall()

    # Buscar linguagens
    cur.execute("SELECT CODLINGUAGEM, NOME FROM TIPOLINGUAGEM ORDER BY NOME")
    linguagens = cur.fetchall()

    # Buscar referências
    cur.execute("""
        SELECT DISTINCT r.CODREFERENCIA, r.TITULO, r.ANO,
               LIST(a.NOME, ', ') AS AUTORES
        FROM REFERENCIA r
        LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
        LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
        GROUP BY r.CODREFERENCIA, r.TITULO, r.ANO
        ORDER BY r.ANO DESC
    """)
    referencias = cur.fetchall()

    return render_template('nova_variavel.html',
                           unidades=unidades,
                           scripts=scripts,
                           variaveis_existentes=variaveis_existentes,
                           linguagens=linguagens,
                           referencias=referencias)


@variaveis_bp.route('/editar_variavel/<int:codvariavel>', methods=['GET', 'POST'])
def editar_variavel(codvariavel):
    if 'usuario' not in session:
        current_app.logger.error("Sessão de usuário não encontrada.")
        return redirect(url_for('auth.login'))
    
    conn, cur = get_db()
    codusuario = session['usuario']['codusuario']

    if request.method == 'POST':
        # Capturar campos do formulário
        nome = request.form['nome'].strip()
        variavel = request.form['variavel'].strip()
        sigla = request.form['sigla'].strip().upper()
        abreviacao = request.form['abreviacao'].strip()
        descricao = request.form['descricao'].strip() or None
        unidade = request.form['unidade']
        casas_decimais = request.form['casas_decimais']
        scripts = request.form.getlist('scripts[]')
        dicom_codes = request.form.getlist('dicom_codes[]')
        possui_formula = 'possui_formula' in request.form
        possui_normalidade = 'possui_normalidade' in request.form
        formula = request.form.get('formula', '').strip() or None
        formula_casas_decimais = request.form.get('formula_casas_decimais', '2')
        equacoes_linguagem = request.form.getlist('equacoes_linguagem[]')
        equacoes_referencia = request.form.getlist('equacoes_referencia[]')
        equacoes_texto = request.form.getlist('equacoes_texto[]')
        alternativas = request.form.getlist('alternativas[]')
        sexo = request.form.getlist('sexo[]')
        valormin_m = request.form.get('valormin_m', '')
        valormax_m = request.form.get('valormax_m', '')
        valormin_f = request.form.get('valormin_f', '')
        valormax_f = request.form.get('valormax_f', '')
        valormin = request.form.get('valormin', '')
        valormax = request.form.get('valormax', '')
        referencia = request.form.get('referencia', '') or None

        try:
            # Validar sigla
            if not variavel.startswith('VR_'):
                flash("A Variável deve começar com 'VR_'.", "error")
                return redirect(request.url)

            # Verificar se a sigla já existe para outra variável
            cur.execute("SELECT 1 FROM VARIAVEIS WHERE UPPER(SIGLA) = UPPER(?) AND CODVARIAVEL != ?", (sigla, codvariavel))
            if cur.fetchone():
                flash("Já existe uma variável com essa sigla.", "error")
                return redirect(request.url)

            # Atualizar variável
            cur.execute("""
                UPDATE VARIAVEIS
                SET NOME = ?, VARIAVEL = ?, SIGLA = ?, ABREVIACAO = ?, DESCRICAO = ?, 
                    CODUNIDADEMEDIDA = ?, CASASDECIMAIS = ?, CODUSUARIO = ?, DTHRULTMODIFICACAO = ?
                WHERE CODVARIAVEL = ?
            """, (nome, variavel, sigla, abreviacao, descricao, unidade, casas_decimais, 
                  codusuario, datetime.now(), codvariavel))
            current_app.logger.info(f"Variável CODVARIAVEL={codvariavel} atualizada.")

            # Atualizar alternativas
            cur.execute("DELETE FROM VARIAVEIS_ALTERNATIVAS WHERE CODVARIAVEL = ?", (codvariavel,))
            for alternativa in alternativas:
                if alternativa.strip():
                    cur.execute("""
                        INSERT INTO VARIAVEIS_ALTERNATIVAS (CODVARIAVEL, ALTERNATIVA, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?)
                    """, (codvariavel, alternativa.strip(), codusuario, datetime.now()))
            current_app.logger.info(f"Atualizadas {len([a for a in alternativas if a.strip()])} alternativas para CODVARIAVEL={codvariavel}")

            # Atualizar scripts vinculados
            cur.execute("DELETE FROM SCRIPTLAUDO_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
            for codscript in scripts:
                if codscript:
                    cur.execute("""
                        INSERT INTO SCRIPTLAUDO_VARIAVEL (CODSCRIPTLAUDO, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?)
                    """, (codscript, codvariavel, codusuario, datetime.now()))
            current_app.logger.info(f"Atualizados {len(scripts)} scripts para CODVARIAVEL={codvariavel}")

            # Atualizar códigos DICOM vinculados
            cur.execute("DELETE FROM VARIAVEL_CODIGO_UNIVERSAL WHERE CODVARIAVEL = ?", (codvariavel,))
            for cod_universal in dicom_codes:
                if cod_universal:
                    cur.execute("""
                        INSERT INTO VARIAVEL_CODIGO_UNIVERSAL (CODVARIAVEL, COD_UNIVERSAL, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?)
                    """, (codvariavel, cod_universal, codusuario, datetime.now()))
            current_app.logger.info(f"Atualizados {len(dicom_codes)} códigos DICOM para CODVARIAVEL={codvariavel}")

            # Atualizar fórmulas e equações
            if possui_formula and formula:
                # Primeiro, remover referências em FORMULA_VARIAVEL
                cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
                current_app.logger.info(f"Excluídas referências de FORMULA_VARIAVEL para CODVARIAVEL={codvariavel}")

                # Agora, remover fórmulas órfãs em FORMULAS
                cur.execute("""
                    DELETE FROM FORMULAS 
                    WHERE CODFORMULA IN (
                        SELECT CODFORMULA 
                        FROM FORMULA_VARIAVEL 
                        WHERE CODVARIAVEL = ?
                    ) OR CODFORMULA NOT IN (SELECT CODFORMULA FROM FORMULA_VARIAVEL)
                """, (codvariavel,))
                current_app.logger.info(f"Excluídas fórmulas órfãs para CODVARIAVEL={codvariavel}")

                # Inserir nova fórmula
                cur.execute("""
                    INSERT INTO FORMULAS (FORMULA, CASADECIMAIS, DTHRULTMODIFICACAO, CODUSUARIO)
                    VALUES (?, ?, ?, ?)
                    RETURNING CODFORMULA
                """, (formula, formula_casas_decimais, datetime.now(), codusuario))
                codformula = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?)
                """, (codformula, codvariavel, codusuario, datetime.now()))
                current_app.logger.info(f"Inserida fórmula CODFORMULA={codformula} para CODVARIAVEL={codvariavel}")

                # Inserir equações
                for lang, ref, texto in zip(equacoes_linguagem, equacoes_referencia, equacoes_texto):
                    if lang and texto:
                        cur.execute("""
                            INSERT INTO FORMULAS (CODLINGUAGEM, EQUACAO, CODREFERENCIA, DTHRULTMODIFICACAO, CODUSUARIO)
                            VALUES (?, ?, ?, ?, ?)
                            RETURNING CODFORMULA
                        """, (lang, texto, ref or None, datetime.now(), codusuario))
                        codformula = cur.fetchone()[0]
                        cur.execute("""
                            INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
                            VALUES (?, ?, ?, ?)
                        """, (codformula, codvariavel, codusuario, datetime.now()))
                current_app.logger.info(f"Inseridas {len([t for t in equacoes_texto if t])} equações para CODVARIAVEL={codvariavel}")
            else:
                # Se não possui fórmula, limpar todas as referências
                cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
                cur.execute("""
                    DELETE FROM FORMULAS 
                    WHERE CODFORMULA NOT IN (SELECT CODFORMULA FROM FORMULA_VARIAVEL)
                """,)
                current_app.logger.info(f"Excluídas fórmulas e referências para CODVARIAVEL={codvariavel}")

            # Atualizar normalidade
            cur.execute("DELETE FROM NORMALIDADE WHERE CODVARIAVEL = ?", (codvariavel,))
            if possui_normalidade and sexo:
                if 'M' in sexo and 'F' in sexo and valormin and valormax:
                    cur.execute("""
                        INSERT INTO NORMALIDADE (CODVARIAVEL, SEXO, VALORMIN, VALORMAX, CODREFERENCIA, CODUSUARIO, DTHRULTMODIFICACAO)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (codvariavel, 'A', valormin, valormax, referencia, codusuario, datetime.now()))
                    current_app.logger.info(f"Inserida normalidade para Ambos para CODVARIAVEL={codvariavel}")
                else:
                    if 'M' in sexo and valormin_m and valormax_m:
                        cur.execute("""
                            INSERT INTO NORMALIDADE (CODVARIAVEL, SEXO, VALORMIN, VALORMAX, CODREFERENCIA, CODUSUARIO, DTHRULTMODIFICACAO)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (codvariavel, 'M', valormin_m, valormax_m, referencia, codusuario, datetime.now()))
                        current_app.logger.info(f"Inserida normalidade para Masculino para CODVARIAVEL={codvariavel}")
                    if 'F' in sexo and valormin_f and valormax_f:
                        cur.execute("""
                            INSERT INTO NORMALIDADE (CODVARIAVEL, SEXO, VALORMIN, VALORMAX, CODREFERENCIA, CODUSUARIO, DTHRULTMODIFICACAO)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (codvariavel, 'F', valormin_f, valormax_f, referencia, codusuario, datetime.now()))
                        current_app.logger.info(f"Inserida normalidade para Feminino para CODVARIAVEL={codvariavel}")

            conn.commit()
            current_app.logger.info(f"Variável CODVARIAVEL={codvariavel} e vínculos atualizados com sucesso.")
            flash("Variável atualizada com sucesso!", "success")
            return redirect(url_for('variaveis.visualizar_variaveis'))
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao atualizar variável CODVARIAVEL={codvariavel}: {str(e)}")
            flash(f"Erro ao atualizar variável: {str(e)}", "error")
            return redirect(request.url)

    # GET: Carregar dados para o formulário
    try:
        cur.execute("""
            SELECT NOME, VARIAVEL, SIGLA, ABREVIACAO, DESCRICAO, CODUNIDADEMEDIDA, CASASDECIMAIS
            FROM VARIAVEIS
            WHERE CODVARIAVEL = ?
        """, (codvariavel,))
        variavel = cur.fetchone()
        if not variavel:
            current_app.logger.warning(f"Variável CODVARIAVEL={codvariavel} não encontrada.")
            flash("Variável não encontrada.", "error")
            return redirect(url_for('variaveis.visualizar_variaveis'))
        current_app.logger.info(f"Variável encontrada: CODVARIAVEL={codvariavel}, NOME={variavel[0]}")

        # Unidades de medida
        cur.execute("SELECT CODUNIDADEMEDIDA, DESCRICAO FROM UNIDADEMEDIDA ORDER BY DESCRICAO")
        unidades = cur.fetchall()

        # Scripts disponíveis e vinculados
        cur.execute("SELECT CODSCRIPTLAUDO, NOME FROM SCRIPTLAUDO ORDER BY NOME")
        scripts = cur.fetchall()
        cur.execute("SELECT CODSCRIPTLAUDO FROM SCRIPTLAUDO_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
        scripts_vinculados = [row[0] for row in cur.fetchall()]

        # Códigos DICOM disponíveis e vinculados
        cur.execute("SELECT COD_UNIVERSAL, CODIGO, DESCRICAOPTBR FROM CODIGO_UNIVERSAL ORDER BY CODIGO")
        codigos_universais = cur.fetchall()
        cur.execute("SELECT COD_UNIVERSAL FROM VARIAVEL_CODIGO_UNIVERSAL WHERE CODVARIAVEL = ?", (codvariavel,))
        dicom_codes_vinculados = [row[0] for row in cur.fetchall()]

        # Variáveis existentes
        cur.execute("SELECT SIGLA, NOME FROM VARIAVEIS WHERE CODVARIAVEL != ? ORDER BY NOME", (codvariavel,))
        variaveis_existentes = cur.fetchall()

        # Referências
        cur.execute("""
            SELECT DISTINCT r.CODREFERENCIA, r.TITULO, r.ANO,
                   LIST(a.NOME, ', ') AS AUTORES
            FROM REFERENCIA r
            LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
            LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
            GROUP BY r.CODREFERENCIA, r.TITULO, r.ANO
            ORDER BY r.ANO DESC
        """)
        referencias = cur.fetchall()

        # Linguagens
        cur.execute("SELECT CODLINGUAGEM, DESCRICAO FROM TIPOLINGUAGEM ORDER BY DESCRICAO")
        linguagens = cur.fetchall()

        # Alternativas
        cur.execute("SELECT ALTERNATIVA FROM VARIAVEIS_ALTERNATIVAS WHERE CODVARIAVEL = ?", (codvariavel,))
        alternativas = [row[0] for row in cur.fetchall()]

        # Equações
        cur.execute("""
            SELECT f.CODLINGUAGEM, f.EQUACAO, f.CODREFERENCIA
            FROM FORMULAS f
            JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
            WHERE fv.CODVARIAVEL = ?
        """, (codvariavel,))
        equacoes = [{'codlinguagem': row[0], 'equacao': row[1], 'codreferencia': row[2]} for row in cur.fetchall()]

        # Fórmula principal
        cur.execute("""
            SELECT f.FORMULA, f.CASADECIMAIS
            FROM FORMULAS f
            JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
            WHERE fv.CODVARIAVEL = ? AND f.CODLINGUAGEM IS NULL
        """, (codvariavel,))
        formula_data = cur.fetchone()
        formula = formula_data[0] if formula_data else None
        formula_casas_decimais = formula_data[1] if formula_data else 2

        # Normalidades
        normalidades = {'masculino': None, 'feminino': None, 'unico': None, 'referencia': None}
        cur.execute("""
            SELECT SEXO, VALORMIN, VALORMAX, CODREFERENCIA
            FROM NORMALIDADE
            WHERE CODVARIAVEL = ?
        """, (codvariavel,))
        for row in cur.fetchall():
            sexo, valormin, valormax, codreferencia = row
            if sexo == 'M':
                normalidades['masculino'] = {'valormin': valormin, 'valormax': valormax}
            elif sexo == 'F':
                normalidades['feminino'] = {'valormin': valormin, 'valormax': valormax}
            elif sexo == 'A':
                normalidades['unico'] = {'valormin': valormin, 'valormax': valormax}
            normalidades['referencia'] = codreferencia

        return render_template('editar_variavel.html',
                               variavel=(variavel[0], variavel[1], variavel[2], variavel[3], variavel[4], variavel[5], variavel[6], formula, formula_casas_decimais),
                               unidades=unidades,
                               scripts=scripts,
                               scripts_vinculados=scripts_vinculados,
                               codigos_universais=codigos_universais,
                               dicom_codes_vinculados=dicom_codes_vinculados,
                               variaveis_existentes=variaveis_existentes,
                               referencias=referencias,
                               linguagens=linguagens,
                               alternativas=alternativas,
                               equacoes=equacoes,
                               normalidades=normalidades)
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar formulário para CODVARIAVEL={codvariavel}: {str(e)}")
        flash(f"Erro ao carregar formulário: {str(e)}", "error")
        return redirect(url_for('variaveis.visualizar_variaveis'))


@variaveis_bp.route('/excluir_variavel/<int:codvariavel>', methods=["POST"])
def excluir_variavel(codvariavel):
    if 'usuario' not in session:
        current_app.logger.error("Sessão de usuário não encontrada.")
        return redirect(url_for('auth.login'))
    
    conn, cur = get_db()
    try:
        codusuario = session['usuario']['codusuario']
        current_app.logger.info(f"Usuário logado: CODUSUARIO={codusuario}")
    except KeyError as e:
        current_app.logger.error(f"Erro na sessão: 'codusuario' não encontrado. Sessão: {session['usuario']}")
        flash("Erro na sessão do usuário. Faça login novamente.", "error")
        return redirect(url_for('auth.logout'))

    try:
        # Verificar se a variável existe
        cur.execute("SELECT NOME, SIGLA FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
        variavel = cur.fetchone()
        if not variavel:
            current_app.logger.warning(f"Variável CODVARIAVEL={codvariavel} não encontrada.")
            flash("Variável não encontrada.", "error")
            return redirect(url_for('variaveis.visualizar_variaveis'))
        nome_variavel, sigla = variavel
        current_app.logger.info(f"Variável encontrada: CODVARIAVEL={codvariavel}, NOME={nome_variavel}, SIGLA={sigla}")

        # Verificar vínculos em tabelas relacionadas
        # 1. FORMULA_VARIAVEL
        cur.execute("SELECT CODFORMULA FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
        formulas = cur.fetchall()
        current_app.logger.info(f"Fórmulas vinculadas a CODVARIAVEL={codvariavel}: {len(formulas)}")

        # 2. NORMALIDADE
        cur.execute("SELECT SEXO, VALORMIN, VALORMAX, IDADE_MIN, IDADE_MAX, CODREFERENCIA FROM NORMALIDADE WHERE CODVARIAVEL = ?", (codvariavel,))
        normalidades = cur.fetchall()
        current_app.logger.info(f"Normalidades vinculadas a CODVARIAVEL={codvariavel}: {len(normalidades)}")

        # 3. SCRIPTLAUDO_VARIAVEL
        cur.execute("SELECT CODSCRIPTLAUDO FROM SCRIPTLAUDO_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
        scripts = cur.fetchall()
        current_app.logger.info(f"Scripts vinculados a CODVARIAVEL={codvariavel}: {len(scripts)}")

        # 4. SECAO_VARIAVEL
        cur.execute("SELECT CODSECAO FROM SECAO_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
        secoes = cur.fetchall()
        current_app.logger.info(f"Seções vinculadas a CODVARIAVEL={codvariavel}: {len(secoes)}")

        # 5. VARIAVEL_CODIGO_UNIVERSAL
        cur.execute("SELECT COD_UNIVERSAL FROM VARIAVEL_CODIGO_UNIVERSAL WHERE CODVARIAVEL = ?", (codvariavel,))
        codigos_dicom = cur.fetchall()
        current_app.logger.info(f"Códigos DICOM vinculados a CODVARIAVEL={codvariavel}: {len(codigos_dicom)}")

        # 6. VARIAVEIS_ALTERNATIVAS
        cur.execute("SELECT ALTERNATIVA FROM VARIAVEIS_ALTERNATIVAS WHERE CODVARIAVEL = ?", (codvariavel,))
        alternativas = cur.fetchall()
        current_app.logger.info(f"Alternativas vinculadas a CODVARIAVEL={codvariavel}: {len(alternativas)}")

        # Se houver vínculos, redirecionar para confirmação
        if formulas or normalidades or scripts or secoes or codigos_dicom or alternativas:
            session['exclusao_variavel'] = {
                'codvariavel': codvariavel,
                'nome_variavel': nome_variavel,
                'sigla': sigla,
                'formulas': [f[0] for f in formulas],
                'normalidades': [{
                    'sexo': n[0],
                    'valormin': n[1],
                    'valormax': n[2],
                    'idade_min': n[3],
                    'idade_max': n[4],
                    'codreferencia': n[5]
                } for n in normalidades],
                'scripts': [s[0] for s in scripts],
                'secoes': [s[0] for s in secoes],
                'codigos_dicom': [c[0] for c in codigos_dicom],
                'alternativas': [a[0] for a in alternativas]
            }
            current_app.logger.info(f"Redirecionando para confirmação de exclusão de CODVARIAVEL={codvariavel} com vínculos")
            return redirect(url_for('variaveis.confirmar_exclusao_variavel'))

        # Se não houver vínculos, excluir diretamente
        cur.execute("DELETE FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
        if cur.rowcount == 0:
            current_app.logger.error(f"Falha ao excluir variável CODVARIAVEL={codvariavel}: nenhum registro afetado")
            flash("Erro ao excluir variável: nenhum registro encontrado.", "error")
            return redirect(url_for('variaveis.visualizar_variaveis'))

        conn.commit()
        current_app.logger.info(f"Variável CODVARIAVEL={codvariavel} excluída com sucesso.")
        flash("Variável excluída com sucesso!", "success")
        return redirect(url_for('variaveis.visualizar_variaveis'))
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao verificar/excluir variável CODVARIAVEL={codvariavel}: {str(e)}")
        flash(f"Erro ao excluir variável: {str(e)}", "error")
        return redirect(url_for('variaveis.visualizar_variaveis'))

@variaveis_bp.route('/confirmar_exclusao_variavel', methods=['GET', 'POST'])
def confirmar_exclusao_variavel():
    if 'exclusao_variavel' not in session:
        current_app.logger.warning("Sessão exclusao_variavel não encontrada.")
        return redirect(url_for('variaveis.visualizar_variaveis'))

    conn, cur = get_db()
    data = session['exclusao_variavel']
    codvar = data['codvariavel']
    nome_variavel = data.get('nome_variavel', 'Desconhecida')
    sigla = data.get('sigla', 'Desconhecida')
    formulas = data.get('formulas', [])
    normalidades = data.get('normalidades', [])
    scripts = data.get('scripts', [])
    secoes = data.get('secoes', [])
    codigos_dicom = data.get('codigos_dicom', [])
    alternativas = data.get('alternativas', [])

    if request.method == 'POST':
        try:
            # Excluir vínculos
            # 1. NORMALIDADE
            cur.execute("DELETE FROM NORMALIDADE WHERE CODVARIAVEL = ?", (codvar,))
            current_app.logger.info(f"Excluídos {cur.rowcount} registros de NORMALIDADE para CODVARIAVEL={codvar}")

            # 2. FORMULA_VARIAVEL e FORMULAS
            for codformula in formulas:
                cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODFORMULA = ?", (codformula,))
                cur.execute("DELETE FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
            current_app.logger.info(f"Excluídas fórmulas para CODVARIAVEL={codvar}")

            # 3. SCRIPTLAUDO_VARIAVEL
            cur.execute("DELETE FROM SCRIPTLAUDO_VARIAVEL WHERE CODVARIAVEL = ?", (codvar,))
            current_app.logger.info(f"Excluídos {cur.rowcount} vínculos de SCRIPTLAUDO_VARIAVEL para CODVARIAVEL={codvar}")

            # 4. SECAO_VARIAVEL
            cur.execute("DELETE FROM SECAO_VARIAVEL WHERE CODVARIAVEL = ?", (codvar,))
            current_app.logger.info(f"Excluídos {cur.rowcount} vínculos de SECAO_VARIAVEL para CODVARIAVEL={codvar}")

            # 5. VARIAVEL_CODIGO_UNIVERSAL
            cur.execute("DELETE FROM VARIAVEL_CODIGO_UNIVERSAL WHERE CODVARIAVEL = ?", (codvar,))
            current_app.logger.info(f"Excluídos {cur.rowcount} vínculos de VARIAVEL_CODIGO_UNIVERSAL para CODVARIAVEL={codvar}")

            # 6. VARIAVEIS_ALTERNATIVAS
            cur.execute("DELETE FROM VARIAVEIS_ALTERNATIVAS WHERE CODVARIAVEL = ?", (codvar,))
            current_app.logger.info(f"Excluídos {cur.rowcount} registros de VARIAVEIS_ALTERNATIVAS para CODVARIAVEL={codvar}")

            # Excluir a variável
            cur.execute("DELETE FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvar,))
            if cur.rowcount == 0:
                current_app.logger.error(f"Falha ao excluir variável CODVARIAVEL={codvar}: nenhum registro afetado")
                flash("Erro ao excluir variável: nenhum registro encontrado.", "error")
                return redirect(url_for('variaveis.visualizar_variaveis'))

            conn.commit()
            session.pop('exclusao_variavel', None)
            current_app.logger.info(f"Variável CODVARIAVEL={codvar} e vínculos excluídos com sucesso.")
            flash("Variável e todos os vínculos excluídos com sucesso!", "success")
            return redirect(url_for('variaveis.visualizar_variaveis'))
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao confirmar exclusão de CODVARIAVEL={codvar}: {str(e)}")
            flash(f"Erro ao excluir variável: {str(e)}", "error")
            return redirect(url_for('variaveis.visualizar_variaveis'))

    # Buscar informações adicionais para exibição na tela de confirmação
    try:
        # Detalhes das fórmulas
        formulas_detalhes = []
        for codformula in formulas:
            cur.execute("SELECT FORMULA FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
            formula = cur.fetchone()
            formulas_detalhes.append({'codformula': codformula, 'formula': formula[0] if formula else "Desconhecida"})

        # Detalhes dos scripts
        scripts_detalhes = []
        for codscript in scripts:
            cur.execute("SELECT NOME FROM SCRIPTLAUDO WHERE CODSCRIPTLAUDO = ?", (codscript,))
            script = cur.fetchone()
            scripts_detalhes.append({'codscript': codscript, 'nome': script[0] if script else "Desconhecido"})

        # Detalhes das seções
        secoes_detalhes = []
        for codsecao in secoes:
            cur.execute("SELECT NOME FROM SECAO_MODO_TEXTO WHERE CODSECAO = ?", (codsecao,))
            secao = cur.fetchone()
            secoes_detalhes.append({'codsecao': codsecao, 'nome': secao[0] if secao else "Desconhecida"})

        # Detalhes dos códigos DICOM
        codigos_detalhes = []
        for cod_universal in codigos_dicom:
            cur.execute("SELECT CODIGO, DESCRICAOPTBR FROM CODIGO_UNIVERSAL WHERE COD_UNIVERSAL = ?", (cod_universal,))
            codigo = cur.fetchone()
            codigos_detalhes.append({'cod_universal': cod_universal, 'codigo': codigo[0] if codigo else "Desconhecido", 'descricaoptbr': codigo[1] if codigo else "Sem descrição"})

        return render_template('confirmar_exclusao_variavel.html',
                               codvariavel=codvar,
                               nome_variavel=nome_variavel,
                               sigla=sigla,
                               formulas=formulas_detalhes,
                               normalidades=normalidades,
                               scripts=scripts_detalhes,
                               secoes=secoes_detalhes,
                               codigos_dicom=codigos_detalhes,
                               alternativas=alternativas)
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar detalhes para confirmação de CODVARIAVEL={codvar}: {str(e)}")
        flash(f"Erro ao carregar detalhes: {str(e)}", "error")
        return redirect(url_for('variaveis.visualizar_variaveis'))

@variaveis_bp.route('/verificar_vinculo_variavel/<int:codvariavel>')
def verificar_vinculo_variavel(codvariavel):
    conn, cur = get_db()
    cur.execute("SELECT COUNT(*) FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
    total_formulas = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM NORMALIDADE WHERE CODVARIAVEL = ?", (codvariavel,))
    total_normalidades = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM SCRIPTLAUDO_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
    total_scripts = cur.fetchone()[0]
    return {
        "vinculada": (total_formulas > 0 or total_normalidades > 0 or total_scripts > 0),
        "total_formulas": total_formulas,
        "total_normalidades": total_normalidades,
        "total_scripts": total_scripts
    }

@variaveis_bp.route('/gerar_modo_texto/<int:codmodelo>')
def gerar_modo_texto(codmodelo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    codusuario = session['usuario']['codusuario']

    # Verificar se o modelo pertence ao usuário
    cur.execute("SELECT NOME FROM MODELO_MODO_TEXTO WHERE CODMODELO = ? AND CODUSUARIO = ?", (codmodelo, codusuario))
    modelo = cur.fetchone()
    if not modelo:
        flash("Modelo não encontrado ou você não tem permissão para acessá-lo.", "error")
        return redirect(url_for('modelos.visualizar_modelos'))
    nome_modelo = modelo[0]

    # Buscar todas as seções do modelo
    cur.execute("""
        SELECT CODSECAO, NOME
        FROM SECAO_MODO_TEXTO
        WHERE CODMODELO = ?
        ORDER BY ORDEM, NOME
    """, (codmodelo,))
    secoes = cur.fetchall()

    # Iniciar o conteúdo do modo texto
    modo_texto = []

    # Para cada seção, buscar as variáveis associadas
    for secao in secoes:
        codsecao, nome_secao = secao
        modo_texto.append(f"[{nome_secao}]")

        # Buscar variáveis associadas à seção
        cur.execute("""
            SELECT v.NOME, v.VARIAVEL, v.SIGLA, v.ABREVIACAO, u.DESCRICAO AS UNIDADE
            FROM SECAO_VARIAVEL sv
            JOIN VARIAVEIS v ON sv.CODVARIAVEL = v.CODVARIAVEL
            LEFT JOIN UNIDADEMEDIDA u ON v.CODUNIDADEMEDIDA = u.CODUNIDADEMEDIDA
            WHERE sv.CODSECAO = ?
            ORDER BY v.SIGLA
        """, (codsecao,))
        variaveis = cur.fetchall()

        for variavel in variaveis:
            nome, variavel_codigo, sigla, abreviacao, unidade = variavel
            unidade = unidade if unidade else "sem unidade"

            # Buscar normalidades associadas à variável
            cur.execute("""
                SELECT SEXO, VALORMIN, VALORMAX
                FROM NORMALIDADE
                WHERE CODVARIAVEL = (
                    SELECT CODVARIAVEL FROM VARIAVEIS WHERE SIGLA = ?
                )
            """, (sigla,))
            normalidades = cur.fetchall()

            # Montar as faixas de normalidade
            normalidade_texto = ""
            for normalidade in normalidades:
                sexo, valormin, valormax = normalidade
                if sexo == 'M':
                    normalidade_texto += f" (M: {valormin} a {valormax})"
                elif sexo == 'F':
                    normalidade_texto += f" (F: {valormin} a {valormax})"

            # Buscar a fórmula associada, se existir
            cur.execute("""
                SELECT f.FORMULA
                FROM FORMULAS f
                JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
                WHERE fv.CODVARIAVEL = (
                    SELECT CODVARIAVEL FROM VARIAVEIS WHERE SIGLA = ?
                )
            """, (sigla,))
            formula = cur.fetchone()
            formula_texto = f" Código: {formula[0]}" if formula else ""

            # Montar a linha do modo texto
            linha = f"{sigla}: 0.0 {unidade}{normalidade_texto}{formula_texto}"
            modo_texto.append(linha)
        modo_texto.append("")  # Linha em branco entre seções

    # Converter o modo texto em string
    modo_texto_str = "\n".join(modo_texto)

    # Gerar o arquivo .txt para download
    from flask import make_response
    response = make_response(modo_texto_str)
    response.headers["Content-Disposition"] = f"attachment; filename=modo_texto_{nome_modelo.lower().replace(' ', '_')}.txt"
    response.headers["Content-Type"] = "text/plain"
    return response

@variaveis_bp.route('/visualizar_modelos')
def visualizar_modelos():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    
    conn, cur = get_db()

    # Configurações de paginação
    itens_por_pagina = 10
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * itens_por_pagina

    # Filtro por nome
    filtro_nome = request.args.get('nome', '').strip()

    # Consulta para modelos
    query = """
        SELECT CODMODELO, NOME
        FROM MODELO_MODO_TEXTO
        WHERE 1=1
    """
    params = []
    if filtro_nome:
        query += " AND UPPER(NOME) LIKE UPPER(?)"
        params.append(f"%{filtro_nome}%")
    query += " ORDER BY NOME"

    # Contagem total
    count_query = """
        SELECT COUNT(*)
        FROM MODELO_MODO_TEXTO
        WHERE 1=1
    """
    count_params = []
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
            WHERE 1=1
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
                'secoes': secoes,
                'codmodelo': codmodelo  # Adicionando codmodelo aqui
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

@variaveis_bp.route('/vincular_anexo/<int:codvariavel>', methods=['GET', 'POST'])
def vincular_anexo(codvariavel):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    codusuario = session['usuario']['codusuario']

    # Buscar informações da variável
    cur.execute("SELECT NOME, VARIAVEL FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
    variavel = cur.fetchone()
    if not variavel:
        flash("Variável não encontrada.", "error")
        return redirect(url_for('variaveis.visualizar_variaveis'))
    nome_variavel, variavel_nome = variavel

    if request.method == 'POST':
        tipo_anexo = request.form['tipo_anexo']
        nome = request.form['nome'].strip() or None
        descricao = request.form['descricao'].strip() or None
        codformula = request.form['codformula']
        codreferencia = request.form['codreferencia'] or None
        caminho = None
        link = None

        # Processar o anexo
        if tipo_anexo == 'URL':
            link = request.form.get('link', '').strip()
            if not link:
                flash("A URL é obrigatória para anexos do tipo URL.", "error")
                return redirect(url_for('variaveis.vincular_anexo', codvariavel=codvariavel))
        else:
            if 'arquivo' not in request.files:
                flash("Nenhum arquivo selecionado.", "error")
                return redirect(url_for('variaveis.vincular_anexo', codvariavel=codvariavel))
            arquivo = request.files['arquivo']
            if arquivo.filename == '':
                flash("Nenhum arquivo selecionado.", "error")
                return redirect(url_for('variaveis.vincular_anexo', codvariavel=codvariavel))

            # Salvar o arquivo
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            filename = secure_filename(arquivo.filename)
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(upload_folder, filename)):
                filename = f"{base}_{counter}{ext}"
                counter += 1
            caminho_absoluto = os.path.join(upload_folder, filename)
            arquivo.save(caminho_absoluto)
            caminho = f"/{upload_folder}/{filename}"

        try:
            # Inserir o anexo
            cur.execute("""
                INSERT INTO ANEXOS (CODREFERENCIA, DESCRICAO, NOME, LINK, CAMINHO, CODUSUARIO, DTHRULTMODIFICACAO, TIPO_ANEXO)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING CODANEXO
            """, (codreferencia, descricao, nome, link, caminho, codusuario, datetime.now(), tipo_anexo))
            cod_anexo = cur.fetchone()[0]

            # Vincular o anexo
            cur.execute("""
                INSERT INTO ANEXO_VARIAVEL_FORMULA (COD_ANEXO, CODVARIAVEL, CODFORMULA, COD_REFERENCIA)
                VALUES (?, ?, ?, ?)
            """, (cod_anexo, codvariavel, codformula, codreferencia))

            conn.commit()
            flash("Anexo vinculado com sucesso!", "success")
            return redirect(url_for('variaveis.visualizar_variaveis'))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao vincular anexo: {str(e)}", "error")
            return redirect(url_for('variaveis.vincular_anexo', codvariavel=codvariavel))

    # Buscar fórmulas
    cur.execute("""
        SELECT f.CODFORMULA, f.FORMULA
        FROM FORMULAS f
        JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
        WHERE fv.CODVARIAVEL = ?
    """, (codvariavel,))
    formulas = cur.fetchall()

    # Buscar referências
    cur.execute("""
        SELECT DISTINCT r.CODREFERENCIA, r.TITULO, r.ANO,
               LIST(a.NOME, ', ') AS AUTORES
        FROM REFERENCIA r
        LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
        LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
        GROUP BY r.CODREFERENCIA, r.TITULO, r.ANO
        ORDER BY r.ANO DESC
    """)
    referencias = cur.fetchall()

    return render_template('vincular_anexo.html',
                           codvariavel=codvariavel,
                           nome_variavel=nome_variavel,
                           formulas=formulas,
                           referencias=referencias)

@variaveis_bp.route('/consultar_estudos/<int:codvariavel>')
def consultar_estudos(codvariavel):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()

    # Buscar informações da variável
    cur.execute("SELECT NOME, VARIAVEL FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
    variavel = cur.fetchone()
    if not variavel:
        flash("Variável não encontrada.", "error")
        return redirect(url_for('variaveis.visualizar_variaveis'))
    nome_variavel, variavel_nome = variavel

    # Buscar fórmulas, referências e anexos
    cur.execute("""
        SELECT f.CODFORMULA, f.FORMULA, r.TITULO, r.ANO,
               LIST(a.NOME, ', ') AS AUTORES,
               a2.CODANEXO, a2.TIPO_ANEXO, a2.CAMINHO, a2.LINK, a2.DESCRICAO
        FROM FORMULA_VARIAVEL fv
        JOIN FORMULAS f ON fv.CODFORMULA = f.CODFORMULA
        LEFT JOIN EQUACOES_LINGUAGEM el ON f.CODFORMULA = el.CODFORMULA
        LEFT JOIN REFERENCIA r ON el.CODREFERENCIA = r.CODREFERENCIA
        LEFT JOIN REFERENCIA_AUTORES ra ON r.CODREFERENCIA = ra.CODREFERENCIA
        LEFT JOIN AUTORES a ON ra.CODAUTOR = a.CODAUTOR
        LEFT JOIN ANEXO_VARIAVEL_FORMULA avf ON fv.CODVARIAVEL = avf.CODVARIAVEL AND f.CODFORMULA = avf.CODFORMULA
        LEFT JOIN ANEXOS a2 ON avf.COD_ANEXO = a2.CODANEXO
        WHERE fv.CODVARIAVEL = ?
        GROUP BY f.CODFORMULA, f.FORMULA, r.TITULO, r.ANO,
                 a2.CODANEXO, a2.TIPO_ANEXO, a2.CAMINHO, a2.LINK, a2.DESCRICAO
    """, (codvariavel,))
    estudos = cur.fetchall()

    estudos_detalhes = []
    for estudo in estudos:
        estudos_detalhes.append({
            'codformula': estudo[0],
            'formula': estudo[1],
            'referencia': {'titulo': estudo[2], 'ano': estudo[3], 'autores': estudo[4]} if estudo[2] else None,
            'anexo': {
                'cod_anexo': estudo[5],
                'tipo_anexo': estudo[6],
                'caminho': estudo[7] or estudo[8],
                'descricao': estudo[9]
            } if estudo[5] else None
        })

    return render_template('consultar_estudos.html',
                           codvariavel=codvariavel,
                           nome_variavel=nome_variavel,
                           estudos=estudos_detalhes)

@variaveis_bp.route('/vincular_codigo_universal', methods=['GET', 'POST'])
def vincular_codigo_universal():
    if 'usuario' not in session:
        current_app.logger.error("Sessão de usuário não encontrada.")
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    try:
        codusuario = session['usuario']['codusuario']
        current_app.logger.info(f"Usuário logado: CODUSUARIO={codusuario}")
    except KeyError as e:
        current_app.logger.error(f"Erro na sessão: 'codusuario' não encontrado em session['usuario']. Sessão: {session['usuario']}")
        flash("Erro na sessão do usuário. Faça login novamente.", "error")
        return redirect(url_for('auth.logout'))

    if request.method == 'POST':
        codvariavel = request.form['codvariavel']
        dicom_codes = request.form.getlist('dicom_codes[]')

        if not codvariavel or not dicom_codes:
            flash('Selecione uma variável e pelo menos um código DICOM.', 'error')
            return redirect(request.url)

        try:
            # Verificar se a variável existe
            cur.execute("SELECT 1 FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
            if not cur.fetchone():
                current_app.logger.warning(f"Variável CODVARIAVEL={codvariavel} não encontrada.")
                flash('Variável não encontrada.', 'error')
                return redirect(request.url)

            # Inserir vínculos
            vinculos_criados = 0
            for cod_universal in dicom_codes:
                # Verificar se o código DICOM existe
                cur.execute("SELECT 1 FROM CODIGO_UNIVERSAL WHERE COD_UNIVERSAL = ?", (cod_universal,))
                if not cur.fetchone():
                    current_app.logger.warning(f"Código DICOM COD_UNIVERSAL={cod_universal} não encontrado.")
                    flash(f'Código DICOM {cod_universal} não encontrado.', 'error')
                    continue

                # Evitar duplicatas
                cur.execute("""
                    SELECT 1 FROM VARIAVEL_CODIGO_UNIVERSAL
                    WHERE CODVARIAVEL = ? AND COD_UNIVERSAL = ?
                """, (codvariavel, cod_universal))
                if cur.fetchone():
                    current_app.logger.info(f"Vínculo já existe: CODVARIAVEL={codvariavel}, COD_UNIVERSAL={cod_universal}")
                    continue

                cur.execute("""
                    INSERT INTO VARIAVEL_CODIGO_UNIVERSAL (CODVARIAVEL, COD_UNIVERSAL, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?, ?)
                """, (codvariavel, cod_universal, codusuario, datetime.now()))
                vinculos_criados += 1

            conn.commit()
            if vinculos_criados > 0:
                flash(f'{vinculos_criados} código(s) DICOM vinculado(s) com sucesso!', 'success')
            else:
                flash('Nenhum novo vínculo criado (já existiam ou inválidos).', 'warning')
            return redirect(url_for('variaveis.visualizar_variaveis'))
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao vincular códigos DICOM: {str(e)}")
            flash(f"Erro ao vincular códigos DICOM: {str(e)}", 'error')
            return redirect(request.url)

    # Buscar dados para o formulário
    try:
        # Buscar todas as variáveis
        cur.execute("SELECT CODVARIAVEL, NOME, SIGLA FROM VARIAVEIS ORDER BY NOME")
        variaveis = cur.fetchall()
        current_app.logger.info(f"Variáveis encontradas (todas): {len(variaveis)}")

        # Buscar códigos DICOM
        cur.execute("SELECT COD_UNIVERSAL, CODIGO, DESCRICAOPTBR FROM CODIGO_UNIVERSAL ORDER BY CODIGO")
        codigos_universais = cur.fetchall()
        current_app.logger.info(f"Códigos DICOM encontrados: {len(codigos_universais)}")
        if codigos_universais:
            current_app.logger.debug(f"Exemplo de código DICOM: {codigos_universais[0]}")
        else:
            current_app.logger.warning("Nenhum código DICOM encontrado na tabela CODIGO_UNIVERSAL.")

        if not variaveis:
            flash("Nenhuma variável cadastrada no sistema.", "warning")
        if not codigos_universais:
            flash("Nenhum código DICOM cadastrado no sistema.", "warning")

        return render_template('vincular_codigo_universal.html',
                               variaveis=variaveis,
                               codigos_universais=codigos_universais)
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar dados do formulário: {str(e)}")
        flash(f"Erro ao carregar formulário: {str(e)}", "error")
        return redirect(url_for('variaveis.visualizar_variaveis'))

@variaveis_bp.route('/get_codigos_vinculados/<int:codvariavel>', methods=['GET'])
def get_codigos_vinculados(codvariavel):
    if 'usuario' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    conn, cur = get_db()
    try:
        cur.execute("""
            SELECT cu.CODIGO, cu.DESCRICAOPTBR
            FROM VARIAVEL_CODIGO_UNIVERSAL vcu
            JOIN CODIGO_UNIVERSAL cu ON vcu.COD_UNIVERSAL = cu.COD_UNIVERSAL
            WHERE vcu.CODVARIAVEL = ?
            ORDER BY cu.CODIGO
        """, (codvariavel,))
        codigos = [{'codigo': row[0], 'descricaoptbr': row[1]} for row in cur.fetchall()]
        current_app.logger.info(f"Códigos DICOM vinculados encontrados para CODVARIAVEL={codvariavel}: {len(codigos)}")
        return jsonify(codigos)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar códigos vinculados para CODVARIAVEL={codvariavel}: {str(e)}")
        return jsonify({'error': str(e)}), 500