from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services import db_updater

codigos_universais_bp = Blueprint('codigos_universais', __name__)

def get_db():
    return db_updater.get_db_from_g()

@codigos_universais_bp.route('/visualizar', methods=['GET', 'POST'])
def visualizar_codigos_universais():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()

    # Configurações de paginação
    itens_por_pagina = 10
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * itens_por_pagina

    # Obter o filtro de pesquisa
    filtro = request.args.get('filtro', '').strip()

    # Montar a consulta com filtro
    query = """
        SELECT COD_UNIVERSAL, TIPO_CODIGO, CODIGO, DESCRICAO, UNIDADE, DESCRICAOPTBR
        FROM CODIGO_UNIVERSAL
        WHERE 1=1
    """
    params = []
    if filtro:
        query += " AND (UPPER(TIPO_CODIGO) LIKE UPPER(?) OR UPPER(CODIGO) LIKE UPPER(?) OR UPPER(DESCRICAOPTBR) LIKE UPPER(?))"
        params.extend([f"%{filtro}%", f"%{filtro}%", f"%{filtro}%"])
    query += " ORDER BY CODIGO"

    # Contagem total de códigos
    count_query = "SELECT COUNT(*) FROM CODIGO_UNIVERSAL WHERE 1=1"
    if filtro:
        count_query += " AND (UPPER(TIPO_CODIGO) LIKE UPPER(?) OR UPPER(CODIGO) LIKE UPPER(?) OR UPPER(DESCRICAOPTBR) LIKE UPPER(?))"
    cur.execute(count_query, params)
    total_codigos = cur.fetchone()[0]
    total_paginas = (total_codigos + itens_por_pagina - 1) // itens_por_pagina

    # Consulta com LIMIT e OFFSET
    paginated_query = f"""
        SELECT FIRST {itens_por_pagina} SKIP {offset}
            COD_UNIVERSAL, TIPO_CODIGO, CODIGO, DESCRICAO, UNIDADE, DESCRICAOPTBR
        FROM ({query})
    """
    cur.execute(paginated_query, params)
    codigos = cur.fetchall()

    return render_template('visualizar_codigos_universais.html',
                           codigos=codigos,
                           pagina=pagina,
                           total_paginas=total_paginas,
                           filtro=filtro)