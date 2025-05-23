from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app


biblioteca_pb = Blueprint('bibliotecas', __name__)

def get_db():
    #from app import conn, cur
    #return conn, cur
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        raise Exception("Conexão com o banco de dados não foi inicializada.")
    return conn, cur


@biblioteca_pb.route('/biblioteca')
def biblioteca():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    return render_template('biblioteca.html')
