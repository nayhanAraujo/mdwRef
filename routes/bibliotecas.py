from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
from functools import wraps


biblioteca_pb = Blueprint('bibliotecas', __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session or session['usuario'].get('role') != 'admin':
            flash("Acesso negado: Apenas administradores podem acessar esta funcionalidade.", "error")
            return redirect(url_for('variaveis.visualizar_variaveis'))
        return f(*args, **kwargs)
    return decorated_function    

@biblioteca_pb.route('/biblioteca')
@admin_required
def biblioteca():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    return render_template('biblioteca.html')
