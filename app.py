from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebird.driver as fbd
from database import conectar
from datetime import datetime
import re, hashlib, os


app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_segura'  # Usada para sessão

# Conexão com o banco de dados
conn = conectar()
cur = conn.cursor()

@app.context_processor
def inject_menu_links():
    if request.endpoint == 'login':
        return dict(links_menu=[])
    links = [
        ('Início', 'home', 'house'),
        ('Nova Variável', 'nova_variavel', 'plus-square'),
        ('Nova Fórmula', 'nova_formula', 'calculator'),
        ('Cadastrar referencia', 'nova_referencia', 'book-open'),
        ('Cadastrar usuario', 'novo_usuario', 'book-open'),
        ('Visualizar usuario', 'usuarios', 'person-fill-gear'),
        ('Fórmulas Cadastradas', 'visualizar_formulas', 'list-check'),
        ('Visualizar variaveis', 'visualizar_variaveis', 'list-check')
    ]
    return dict(links_menu=links)

@app.route('/novo_usuario', methods=['GET', 'POST'])
def novo_usuario():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        identificacao = request.form['identificacao'].strip().lower()
        senha = request.form['senha']
        perfil = request.form['perfil']
        status = int(request.form['status'])
        ucaseNome = nome
        
        # Verifica se já existe o login (identificação)
        cur.execute("SELECT 1 FROM USUARIO WHERE IDENTIFICACAO = ? ", (identificacao,))
        if cur.fetchone():
            flash("Esse login já está em uso.", "error")
            return redirect(url_for('novo_usuario'))

        # Criptografa a senha
        senha_criptografada = hashlib.sha256(senha.encode()).hexdigest()

        # Insere usuário
        cur.execute("""
            INSERT INTO USUARIO (NOME, IDENTIFICACAO,UCASE_NOME, SENHA, PERFIL,STATUS,DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nome, identificacao,ucaseNome, senha_criptografada, perfil, status, datetime.now()))

        conn.commit()
        flash("Usuário cadastrado com sucesso!", "success")
        return redirect(url_for('home'))

    return render_template('novo_usuario.html')



@app.route('/editar_usuario/<int:codusuario>', methods=['GET', 'POST'])
def editar_usuario(codusuario):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        identificacao = request.form['identificacao'].strip().lower()
        perfil = request.form['perfil']
      

        cur.execute("""
            UPDATE USUARIO SET
            NOME = ?, IDENTIFICACAO = ?, PERFIL = ?
            WHERE CODUSUARIO = ?
        """, (nome, identificacao, perfil, codusuario))

        conn.commit()
        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for('usuarios'))

    cur.execute("SELECT NOME, IDENTIFICACAO, PERFIL FROM USUARIO WHERE CODUSUARIO = ?", (codusuario,))
    usuario = cur.fetchone()
    return render_template('editar_usuario.html', codusuario=codusuario, usuario=usuario)


@app.route('/excluir_usuario/<int:codusuario>', methods=['POST'])
def excluir_usuario(codusuario):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cur.execute("DELETE FROM USUARIO WHERE CODUSUARIO = ?", (codusuario,))
    conn.commit()
    flash("Usuário excluído com sucesso!", "success")
    return redirect(url_for('usuarios'))


@app.route('/visualizar_usuarios')
def usuarios():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cur.execute("SELECT CODUSUARIO, NOME, IDENTIFICACAO, PERFIL FROM USUARIO ORDER BY NOME")
    usuarios = cur.fetchall()
    return render_template('visualizar_usuarios.html', usuarios=usuarios)

@app.route('/')
def home():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # Gráfico 1: Variáveis por unidade
    cur.execute("""
        SELECT U.DESCRICAO, COUNT(*) FROM VARIAVEIS V
        JOIN UNIDADEMEDIDA U ON V.CODUNIDADEMEDIDA = U.CODUNIDADEMEDIDA
        GROUP BY U.DESCRICAO
        ORDER BY COUNT(*) DESC
    """)
    variaveis_unidade = cur.fetchall()
    labels1 = [row[0] for row in variaveis_unidade]
    dados1 = [row[1] for row in variaveis_unidade]

    # Gráfico 2: Total de variáveis com fórmula
    cur.execute("""
        SELECT COUNT(DISTINCT CODVARIAVEL) FROM FORMULA_VARIAVEL
    """)
    com_formula = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM VARIAVEIS")
    total_variaveis = cur.fetchone()[0]
    sem_formula = total_variaveis - com_formula

    # Gráfico 3: Quantidade de variáveis por casas decimais
    cur.execute("SELECT v.CODUNIDADEMEDIDA, COUNT(*) FROM VARIAVEIS v GROUP BY 1 ORDER BY CODUNIDADEMEDIDA")
    decimais = cur.fetchall()
    labels2 = [str(row[0]) for row in decimais]
    dados2 = [row[1] for row in decimais]

    # Gráfico 4: Variáveis com e sem normalidade
    cur.execute("SELECT COUNT(DISTINCT CODVARIAVEL) FROM NORMALIDADE")
    com_normalidade = cur.fetchone()[0]
    sem_normalidade = total_variaveis - com_normalidade

    return render_template('index.html',
        labels1=labels1, dados1=dados1,
        labels2=labels2, dados2=dados2,
        com_formula=com_formula, sem_formula=sem_formula,
        com_normalidade=com_normalidade, sem_normalidade=sem_normalidade
    )



@app.route('/visualizar_variaveis')
def visualizar_variaveis():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    cur.execute("SELECT CODVARIAVEL, NOME,VARIAVEL, SIGLA,ABREVIACAO FROM VARIAVEIS ORDER BY NOME")
    variaveis = cur.fetchall()
    return render_template('visualizar_variaveis.html', variaveis=variaveis)


@app.route('/editar_variavel/<int:codvariavel>', methods=['GET', 'POST'])
def editar_variavel(codvariavel):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        sigla = request.form['sigla']
        abreviacao = request.form['abreviacao']
        casas_decimais = request.form['casas_decimais']
        descricao = request.form['descricao']
        codunidade = request.form['unidade']
        variavel = request.form['variavel']
        cur.execute("""
            UPDATE VARIAVEIS SET
            NOME = ?, VARIAVEL=?, SIGLA = ?, ABREVIACAO = ?, CASASDECIMAIS = ?, DESCRICAO = ?, CODUNIDADEMEDIDA = ?, DTHRULTMODIFICACAO = ?, CODUSUARIO = ?
            WHERE CODVARIAVEL = ?
        """, (nome,variavel, sigla, abreviacao, casas_decimais, descricao, codunidade, datetime.now(), 4, codvariavel))

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
        return redirect(url_for('visualizar_variaveis'))

    # Busca os dados da variável para edição
    cur.execute("""
        SELECT v.NOME,v.VARIAVEL, v.SIGLA, v.ABREVIACAO, v.CASASDECIMAIS, v.DESCRICAO, v.CODUNIDADEMEDIDA,
               f.FORMULA, f.CASADECIMAIS as FORMULA_CASAS,
               n.SEXO, n.VALORMIN, n.VALORMAX, n.IDADE_MIN, n.IDADE_MAX, n.CODREFERENCIA
        FROM VARIAVEIS v
        LEFT JOIN FORMULA_VARIAVEL fv ON v.CODVARIAVEL = fv.CODVARIAVEL
        LEFT JOIN FORMULAS f ON fv.CODFORMULA = f.CODFORMULA
        LEFT JOIN NORMALIDADE n ON v.CODVARIAVEL = n.CODVARIAVEL
        WHERE v.CODVARIAVEL = ?
    """, (codvariavel,))
    variavel = cur.fetchone()

    # Busca unidades de medida
    cur.execute("SELECT CODUNIDADEMEDIDA, DESCRICAO FROM UNIDADEMEDIDA ORDER BY DESCRICAO")
    unidades = cur.fetchall()

    # Busca referências
    cur.execute("SELECT CODREFERENCIA, AUTOR, ANO FROM REFERENCIA ORDER BY ANO DESC")
    referencias = cur.fetchall()
    
    cur.execute("SELECT VARIAVEL,NOME FROM VARIAVEIS ORDER BY VARIAVEL")
    variaveis_existentes = [(row[0], row[1]) for row in cur.fetchall()]
    
    return render_template('editar_variavel.html',
                         variavel=variavel,
                         unidades=unidades,
                         referencias=referencias,
                         codvariavel=codvariavel,
                         variaveis_existentes=variaveis_existentes)


@app.route('/excluir_variavel/<int:codvariavel>', methods=["POST"])
def excluir_variavel(codvariavel):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # Verifica se a variável está vinculada a alguma fórmula
    cur.execute("SELECT CODFORMULA FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
    formulas = cur.fetchall()

    if formulas:
        formula_ids = [f[0] for f in formulas]
        for codformula in formula_ids:
            cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODFORMULA = ?", (codformula,))
            cur.execute("DELETE FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))

    cur.execute("DELETE FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
    conn.commit()
    flash("Variável e fórmulas vinculadas excluídas com sucesso!" if formulas else "Variável excluída com sucesso!")
    return redirect(url_for('visualizar_variaveis'))


@app.route('/confirmar_exclusao_variavel', methods=['GET', 'POST'])
def confirmar_exclusao_variavel():
    if 'exclusao_variavel' not in session:
        return redirect(url_for('index'))

    data = session['exclusao_variavel']
    codvar = data['codvariavel']
    formulas = data['formulas']

    if request.method == 'POST':
        for codformula in formulas:
            cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODFORMULA = ?", (codformula,))
            cur.execute("DELETE FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
        cur.execute("DELETE FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvar,))
        conn.commit()
        session.pop('exclusao_variavel')
        flash("Variável e fórmulas vinculadas excluídas com sucesso!")
        return redirect(url_for('index'))

    return render_template('confirmar_exclusao_variavel.html', formulas=formulas)

@app.route('/verificar_vinculo_variavel/<int:codvariavel>')
def verificar_vinculo_variavel(codvariavel):
    cur.execute("SELECT COUNT(*) FROM FORMULA_VARIAVEL WHERE CODVARIAVEL = ?", (codvariavel,))
    total = cur.fetchone()[0]
    return {"vinculada": total > 0, "total": total}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificacao = request.form['usuario'].strip().lower()
        senha = request.form['senha']

        # Criptografa a senha digitada para comparar com o banco
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        cur.execute("""
            SELECT NOME FROM USUARIO
            WHERE IDENTIFICACAO = ? AND SENHA = ? AND STATUS = -1
        """, (identificacao, senha_hash))
        resultado = cur.fetchone()

        if resultado:
            session['usuario'] = resultado[0]
            return redirect(url_for('home'))
        else:
            return render_template('login.html', erro='Usuário ou senha inválidos.')
          

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))



@app.route('/nova_referencia', methods=['GET', 'POST'])
def nova_referencia():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        autor = request.form['autor']
        ano = request.form['ano']

        cur.execute("""
            INSERT INTO REFERENCIA (AUTOR, ANO, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?)
        """, (autor, ano, 4, datetime.now()))

        conn.commit()
        flash("success", "Referência cadastrada com sucesso!")
        return redirect(url_for('nova_variavel'))

    return render_template('nova_referencia.html')

@app.route('/nova_formula', methods=['GET', 'POST'])
def nova_formula():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        sigla = request.form['sigla']
        formula = request.form['formula']

        cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE SIGLA = ?", (sigla,))
        var_principal = cur.fetchone()
        if not var_principal:
            return "Variável principal não encontrada", 400

        codvar = var_principal[0]
        cur.execute("""
            INSERT INTO FORMULAS (NOME, DESCRICAO, FORMULA, CASADECIMAIS, DTHRULTMODIFICACAO, CODUSUARIO)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING CODFORMULA
        """, (
            sigla, f"Fórmula para {sigla}", formula, 2, datetime.now(), 4
        ))
        codformula = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?)
        """, (codformula, codvar, 4, datetime.now()))

        conn.commit()
        #flash("success", "Fórmula salva com sucesso!")

        return redirect(url_for('home'))

    cur.execute("SELECT SIGLA FROM VARIAVEIS ORDER BY SIGLA")
    siglas = [row[0] for row in cur.fetchall()]
    return render_template('nova_formula.html', siglas=siglas)

@app.route('/nova_variavel', methods=['GET', 'POST'])
def nova_variavel():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        sigla = request.form['sigla'].strip().upper()
        descricao = request.form['descricao']
        unidade = request.form['unidade']
        casas_decimais = request.form['casas_decimais']
        variavel = request.form['variavel']

        if not sigla.startswith("VR_"):
            flash(("error", "A variável deve começar com 'VR_'"))
            return redirect(request.url)
        
        # Verifica se a variável começa com << ou termina com >>
        if variavel.startswith("<<") or variavel.endswith(">>"):
            flash(("error", "A variável não pode começar com '<<' ou terminar com '>>'"))
            return redirect(request.url)
        
        # Verifica se já existe a sigla
        cur.execute("SELECT 1 FROM VARIAVEIS WHERE UPPER(VARIAVEL) = ?", (variavel,))
        if cur.fetchone():
            flash("Já existe um rsgistro no banco com essa variável.", "error")
            return redirect(request.url)

        cur.execute("""
            INSERT INTO VARIAVEIS (NOME,VARIAVEL, SIGLA, DESCRICAO, CODUNIDADEMEDIDA, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING CODVARIAVEL
        """, (nome,variavel, sigla, descricao, unidade, 4, datetime.now()))

        codvar = cur.fetchone()[0]

        # Se tiver fórmula
        if 'possui_formula' in request.form:
            formula = request.form['formula']
            cur.execute("""
                INSERT INTO FORMULAS (NOME, DESCRICAO, FORMULA, CASADECIMAIS, CODUSUARIO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING CODFORMULA
            """, (sigla, f"Fórmula para {sigla}", formula, casas_decimais, 4, datetime.now()))

            codform = cur.fetchone()[0]

            # Insere vínculo da fórmula com a variável
            cur.execute("""
                INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
                VALUES (?, ?, ?, ?)
            """, (codform, codvar, 4, datetime.now()))

        # Se tiver normalidade
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
        flash(("success", "Variável cadastrada com sucesso!"))
        return redirect(url_for('nova_variavel'))

    cur.execute("SELECT CODUNIDADEMEDIDA, DESCRICAO FROM UNIDADEMEDIDA ORDER BY DESCRICAO")
    unidades = cur.fetchall()
    cur.execute("SELECT CODREFERENCIA, AUTOR, ANO FROM REFERENCIA ORDER BY ANO DESC")
    referencias = cur.fetchall()

    cur.execute("SELECT VARIAVEL,NOME FROM VARIAVEIS ORDER BY VARIAVEL")
    variaveis_existentes = [(row[0], row[1]) for row in cur.fetchall()]
        
   

    return render_template('nova_variavel.html', unidades=unidades, referencias=referencias, variaveis_existentes=variaveis_existentes)

@app.route('/formulas')
def visualizar_formulas():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cur.execute("""
        SELECT F.CODFORMULA, F.NOME, F.FORMULA, V.SIGLA
        FROM FORMULAS F
        JOIN FORMULA_VARIAVEL FV ON FV.CODFORMULA = F.CODFORMULA
        JOIN VARIAVEIS V ON V.CODVARIAVEL = FV.CODVARIAVEL
        GROUP BY F.CODFORMULA, F.NOME, F.FORMULA, V.SIGLA
        ORDER BY F.NOME
    """)
    formulas = cur.fetchall()
    return render_template('formulas.html', formulas=formulas)

@app.route('/editar_formula/<int:codformula>', methods=['GET', 'POST'])
def editar_formula(codformula):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nova_formula = request.form['formula']
        cur.execute("""
            UPDATE FORMULAS SET FORMULA = ?, DTHRULTMODIFICACAO = ? WHERE CODFORMULA = ?
        """, (nova_formula, datetime.now(), codformula))
        conn.commit()
        return redirect(url_for('visualizar_formulas'))

    cur.execute("SELECT FORMULA FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
    formula = cur.fetchone()
    return render_template('editar_formula.html', codformula=codformula, formula=formula[0] if formula else '')

@app.route('/excluir_formula/<int:codformula>')
def excluir_formula(codformula):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODFORMULA = ?", (codformula,))
    cur.execute("DELETE FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
    conn.commit()
    return redirect(url_for('visualizar_formulas'))

@app.route('/uploaddll', methods=['GET', 'POST'])
def uploaddll():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    variaveis, formulas, normalidades = [], [], []

    if request.method == 'POST':
        if 'dllfile' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        file = request.files['dllfile']

        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        if not file.filename.endswith('.json'):
            flash('O arquivo deve ser um JSON exportado pela ferramenta', 'error')
            return redirect(request.url)

        try:
            import json
            conteudo = json.load(file)

            variaveis = conteudo.get("variaveis", [])
            formulas = conteudo.get("formulas", [])
            normalidades = conteudo.get("normalidades", [])

            if not variaveis:
                flash("Nenhuma variável encontrada no JSON enviado.", "error")
                return redirect(request.url)

            flash('Arquivo JSON carregado com sucesso!', 'success')

        except Exception as e:
            flash(f'Erro ao processar o JSON: {e}', 'error')

    return render_template('uploaddll.html', variaveis=variaveis, formulas=formulas, normalidades=normalidades)


@app.route('/importar_variavel', methods=['POST'])
def importar_variavel():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    sigla = request.form.get('sigla')

    if not sigla:
        flash('Sigla da variável não foi recebida.', 'error')
        return redirect(url_for('uploaddll'))

    # Verifica se já existe
    cur.execute("SELECT 1 FROM VARIAVEIS WHERE SIGLA = ?", (sigla,))
    if cur.fetchone():
        flash(f'A variável {sigla} já está cadastrada.', 'info')
        return redirect(url_for('uploaddll'))

    # Cria a variável com dados básicos
    cur.execute("""
        INSERT INTO VARIAVEIS (NOME, VARIAVEL, SIGLA, ABREVIACAO, CASASDECIMAIS, DESCRICAO, CODUSUARIO, DTHRULTMODIFICACAO)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (sigla, sigla, sigla.replace("VR_", ""), sigla.replace("VR_", ""), 2, '', 4, datetime.now()))

    conn.commit()
    flash(f'Variável {sigla} importada com sucesso!', 'success')
    return redirect(url_for('uploaddll'))


@app.route('/importar_formula', methods=['POST'])
def importar_formula():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    sigla = request.form.get('sigla')
    formula = request.form.get('formula')

    if not sigla or not formula:
        flash('Dados incompletos para importar fórmula.', 'error')
        return redirect(url_for('uploaddll'))

    cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE VARIAVEL = ?", (sigla,))
    var = cur.fetchone()

    if not var:
        flash(f'A variável associada à fórmula {sigla} não foi encontrada.', 'error')
        return redirect(url_for('uploaddll'))

    codvar = var[0]

    cur.execute("""
        INSERT INTO FORMULAS (NOME, DESCRICAO, FORMULA, CASADECIMAIS, DTHRULTMODIFICACAO, CODUSUARIO)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING CODFORMULA
    """, (sigla, f"Fórmula para {sigla}", formula, 2, datetime.now(), 4))
    codformula = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
        VALUES (?, ?, ?, ?)
    """, (codformula, codvar, 4, datetime.now()))

    conn.commit()
    flash(f'Fórmula para {sigla} importada com sucesso!', 'success')
    return redirect(url_for('uploaddll'))


@app.route('/importar_normalidade', methods=['POST'])
def importar_normalidade():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    sigla = request.form.get('sigla')
    sexo = request.form.get('sexo')
    valormin = request.form.get('valormin') or None
    valormax = request.form.get('valormax') or None
    idade_min = request.form.get('idade_min') or None
    idade_max = request.form.get('idade_max') or None
    codreferencia = request.form.get('referencia') or None

    cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE VARIAVEL = ?", (sigla,))
    var = cur.fetchone()

    if not var:
        flash(f'A variável associada à normalidade {sigla} não foi encontrada.', 'error')
        return redirect(url_for('uploaddll'))

    codvar = var[0]

    cur.execute("""
        INSERT INTO NORMALIDADE (CODVARIAVEL, SEXO, VALORMIN, VALORMAX, IDADE_MIN, IDADE_MAX, CODREFERENCIA, CODUSUARIO, DTHRULTMODIFICACAO)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (codvar, sexo, valormin, valormax, idade_min, idade_max, codreferencia, 4, datetime.now()))

    conn.commit()
    flash(f'Normalidade para {sigla} importada com sucesso!', 'success')
    return redirect(url_for('uploaddll'))


@app.route('/biblioteca')
def biblioteca():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('biblioteca.html')


if __name__ == '__main__':

    app.run(host='192.168.10.34', port=5000, debug=True)