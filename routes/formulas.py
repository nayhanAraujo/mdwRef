from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime

formulas_bp = Blueprint('formulas', __name__)

def get_db():
    from app import conn, cur
    return conn, cur

@formulas_bp.route('/nova_formula', methods=['GET', 'POST'])
def nova_formula():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
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
        """, (sigla, f"Fórmula para {sigla}", formula, 2, datetime.now(), 4))
        codformula = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO FORMULA_VARIAVEL (CODFORMULA, CODVARIAVEL, CODUSUARIO, DTHRULTMODIFICACAO)
            VALUES (?, ?, ?, ?)
        """, (codformula, codvar, 4, datetime.now()))
        conn.commit()
        return redirect(url_for('variables.home'))
    cur.execute("SELECT SIGLA FROM VARIAVEIS ORDER BY SIGLA")
    siglas = [row[0] for row in cur.fetchall()]
    return render_template('nova_formula.html', siglas=siglas)

@formulas_bp.route('/formulas')
def visualizar_formulas():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
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

@formulas_bp.route('/editar_formula/<int:codformula>', methods=['GET', 'POST'])
def editar_formula(codformula):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    if request.method == 'POST':
        nova_formula = request.form['formula']
        cur.execute("""
            UPDATE FORMULAS SET FORMULA = ?, DTHRULTMODIFICACAO = ? WHERE CODFORMULA = ?
        """, (nova_formula, datetime.now(), codformula))
        conn.commit()
        return redirect(url_for('formulas.visualizar_formulas'))
    cur.execute("SELECT FORMULA FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
    formula = cur.fetchone()
    return render_template('editar_formula.html', codformula=codformula, formula=formula[0] if formula else '')

@formulas_bp.route('/excluir_formula/<int:codformula>')
def excluir_formula(codformula):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    conn, cur = get_db()
    cur.execute("DELETE FROM FORMULA_VARIAVEL WHERE CODFORMULA = ?", (codformula,))
    cur.execute("DELETE FROM FORMULAS WHERE CODFORMULA = ?", (codformula,))
    conn.commit()
    return redirect(url_for('formulas.visualizar_formulas'))