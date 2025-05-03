from flask import Blueprint, render_template, request, redirect, url_for, session, flash


biblioteca_pb = Blueprint('bibliotecas', __name__)

def get_db():
    from app import conn, cur
    return conn, cur



@biblioteca_pb.route('/biblioteca')
def biblioteca():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('biblioteca.html')
