from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
from datetime import datetime
from get_db import get_db

import json

uploads_bp = Blueprint('uploads', __name__)


@uploads_bp.route('/uploaddll', methods=['GET', 'POST'])
def uploaddll():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
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

@uploads_bp.route('/importar_variavel', methods=['POST'])
def importar_variavel():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    with get_db() as (conn, cur):
        sigla = request.form.get('sigla')
        if not sigla:
            flash('Sigla da variável não foi recebida.', 'error')
            return redirect(url_for('uploads.uploaddll'))
        cur.execute("SELECT 1 FROM VARIAVEIS WHERE SIGLA = ?", (sigla,))
        if cur.fetchone():
            flash(f'A variável {sigla} já está cadastrada.', 'info')
            return redirect(url_for('uploads.uploaddll'))
        cur.execute("""
            INSERT INTO VARIAVEIS (NOME, VARIAVEL, SIGLA, ABREVIACAO, CASASDECIMAIS, DESCRICAO, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (sigla, sigla, sigla.replace("VR_", ""), sigla.replace("VR_", ""), 2, '', 4, datetime.now()))
        conn.commit()
        flash(f'Variável {sigla} importada com sucesso!', 'success')
        return redirect(url_for('uploads.uploaddll'))

@uploads_bp.route('/importar_formula', methods=['POST'])
def importar_formula():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    with get_db() as (conn, cur):
        sigla = request.form.get('sigla')
        formula = request.form.get('formula')
        if not sigla or not formula:
            flash('Dados incompletos para importar fórmula.', 'error')
            return redirect(url_for('uploads.uploaddll'))
        cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE VARIAVEL = ?", (sigla,))
        var = cur.fetchone()
        if not var:
            flash(f'A variável associada à fórmula {sigla} não foi encontrada.', 'error')
            return redirect(url_for('uploads.uploaddll'))
        codvar = var[0]
        cur.execute("""
            INSERT INTO FORMULAS (NOME, DESCRICAO, FORMULA, DTHRULTMODIFICACAO, CODUSUARIO)
            VALUES (?, ?, ?, ?, ?)
            RETURNING CODFORMULA
        """, (sigla, f"Fórmula para {sigla}", formula, datetime.now(), 4))
        codformula = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?)
        """, (codformula, codvar, 4, datetime.now()))
        conn.commit()
        flash(f'Fórmula para {sigla} importada com sucesso!', 'success')
        return redirect(url_for('uploads.uploaddll'))

@uploads_bp.route('/importar_normalidade', methods=['POST'])
def importar_normalidade():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    with get_db() as (conn, cur):
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
            return redirect(url_for('uploads.uploaddll'))
        codvar = var[0]
        cur.execute("""
            INSERT INTO NORMALIDADE (CODVARIAVEL, SEXO, VALORMIN, VALORMAX, IDADE_MIN, IDADE_MAX, CODREFERENCIA, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codvar, sexo, valormin, valormax, idade_min, idade_max, codreferencia, 4, datetime.now()))
        conn.commit()
        flash(f'Normalidade para {sigla} importada com sucesso!', 'success')
        return redirect(url_for('uploads.uploaddll'))

@uploads_bp.route('/biblioteca')
def biblioteca():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    return render_template('biblioteca.html')