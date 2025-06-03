from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session,send_file,jsonify
from datetime import datetime
import io,re,os,uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email import encoders

scripts_bp = Blueprint('scripts', __name__)

def get_db():
    conn = current_app.config.get('db_conn')
    cur = current_app.config.get('db_cursor')
    if conn is None or cur is None:
        raise Exception("Conexão com o banco de dados não foi inicializada.")
    return conn, cur


@scripts_bp.app_template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M'):
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = re.sub(r'\.\d+', '', value)
            value = datetime.strptime(value, '%d.%m.%Y, %H:%M:%S')
        except ValueError:
            return ''
    return value.strftime(format)

def save_file(file, folder, prefix):
    if not file:
        return None, None
    filename = f"{prefix}_{uuid.uuid4().hex}{os.path.splitext(file.filename)[1]}"
    filepath = os.path.join(current_app.root_path, folder, filename)
    file.save(filepath)
    return f"/{folder}/{filename}", file.filename

@scripts_bp.route('/send_images_email', methods=['POST'])
def send_images_email():
    if 'usuario' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401

    data = request.get_json()
    codscriptlaudo = data.get('codscriptlaudo')
    recipient_email = data.get('email')
    sistema = data.get('sistema')

    if not codscriptlaudo or not recipient_email or not sistema:
        return jsonify({'success': False, 'message': 'Parâmetros inválidos.'}), 400

    conn, cur = get_db()
    try:
        # Fetch script name and sistema
        cur.execute("SELECT NOME, SISTEMA FROM SCRIPTLAUDO WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
        script = cur.fetchone()
        if not script:
            return jsonify({'success': False, 'message': 'Script não encontrado.'}), 404
        script_name, db_sistema = script

        # Validate sistema matches database
        if db_sistema != sistema:
            return jsonify({'success': False, 'message': 'Sistema inválido para este script.'}), 400

        # Append sistema to script name
        script_name = f"{script_name} - {sistema}"

        # Fetch images
        cur.execute("""
            SELECT CAMINHO, NOME_ARQUIVO
            FROM SCRIPT_ARQUIVOS
            WHERE CODSCRIPTLAUDO = ? AND TIPO = 'IMAGEM'
        """, (codscriptlaudo,))
        images = cur.fetchall()
        if not images:
            return jsonify({'success': False, 'message': 'Nenhuma imagem encontrada para este script.'}), 404

        # Setup email
        msg = MIMEMultipart('related')
        msg['From'] = current_app.config['SMTP_SENDER']
        msg['To'] = recipient_email
        msg['Subject'] = f'Imagens do Script: {script_name}'

        # Alternative part for plain text and HTML
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        # Plain text fallback
        plain_text = f"""Olá,

Em anexo, seguem as imagens vinculadas ao script "{script_name}".

Atenciosamente,
Equipe Laudos
"""
        msg_alternative.attach(MIMEText(plain_text, 'plain'))

        # HTML email with logo and marketing text
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .logo {{ max-width: 150px; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 5px; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        .cta {{ background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="cid:logo" alt="Laudos Logo" class="logo">
        </div>
                <div class="content">
            <h2>Olá,</h2>
            <p>Estamos felizes em compartilhar com você as imagens do script <strong>{script_name}</strong>, desenvolvido para otimizar e agilizar seus laudos médicos com precisão e eficiência.</p>
            <p>Em anexo, você encontrará capturas de tela que demonstram a interface e os recursos do script. Acreditamos que essas ferramentas podem transformar sua prática clínica, economizando tempo e melhorando a qualidade dos diagnósticos.</p>
            <p><strong>Por que escolher nossos Sistemas de prontuário eletrônico</strong></p>
            <ul>
                <li>Soluções personalizadas para suas necessidades.</li>
                <li>Interface intuitiva e fácil de usar.</li>
                <li>Suporte técnico dedicado para médicos e clínicas.</li>
            </ul>
            <p style="text-align: center;">
                <a href="https://www.medware.com.br/whatsapp-medware/" class="cta">Entre em Contato para uma Demonstração do modelo</a>
            </p>
        </div>
        <div class="footer">
            <p>Medware - Soluções em sistemas médicos<br>
            <a href="https://laudosux.medware.com.br/">Conheça o Laudos UX</a> | vendas@medware.com.br<br>
            Este é um email automático, por favor, não responda diretamente.</p>
        </div>
    </div>
</body>
</html>"""
        msg_alternative.attach(MIMEText(html_content, 'html'))

        # Attach logo as inline image
        logo_path = os.path.join(current_app.root_path, 'static/img/logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo = MIMEImage(f.read(), name='logo.png')
                logo.add_header('Content-ID', '<logo>')
                logo.add_header('Content-Disposition', 'inline', filename='logo.png')
                msg.attach(logo)
        else:
            current_app.logger.warning("Logo file not found at static/img/logo.png")

        # Attach images
        for image in images:
            caminho, nome_arquivo = image
            filepath = os.path.join(current_app.root_path, caminho.lstrip('/'))
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{nome_arquivo}"'
                )
                msg.attach(part)
            else:
                current_app.logger.warning(f"Image file not found: {filepath}")

        # Send email
        with smtplib.SMTP(current_app.config['SMTP_SERVER'], current_app.config['SMTP_PORT']) as server:
            server.starttls()
            server.login(current_app.config['SMTP_USERNAME'], current_app.config['SMTP_PASSWORD'])
            server.send_message(msg)

        current_app.logger.info(f"Imagens do script CODSCRIPTLAUDO={codscriptlaudo} enviadas para {recipient_email}.")
        return jsonify({'success': True})

    except Exception as e:
        current_app.logger.error(f"Erro ao enviar email para CODSCRIPTLAUDO={codscriptlaudo}: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao enviar email: {str(e)}'}), 500

@scripts_bp.route('/novo_script', methods=['GET', 'POST'])
def novo_script():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    codusuario = session['usuario']['codusuario']

    cur.execute("SELECT CODPACOTE, NOME, DESCRICAO FROM PACOTES ORDER BY NOME")
    pacotes = cur.fetchall()

    if request.method == 'POST':
        nome = request.form['nome'].strip()
        codpacote = request.form['codpacote'] or None
        descricao = request.form['descricao'].strip() or None
        linguagem = request.form['linguagem'].strip() or None
        caminho_projeto = request.form['caminho_projeto'].strip() or None
        sistema = request.form['sistema'].strip() or None
        aprovado = 1 if 'aprovado' in request.form else 0
        aprovado_por = request.form['aprovado_por'].strip() or None if aprovado else None
        ativo = 1 if 'ativo' in request.form else 0
        arquivo_json = request.files.get('arquivo_json')
        imagens = request.files.getlist('imagens[]')
        pdfs = request.files.getlist('pdfs[]')

        if not nome:
            flash("O nome do script é obrigatório.", "error")
            return redirect(request.url)

        cur.execute("SELECT 1 FROM SCRIPTLAUDO WHERE UPPER(NOME) = UPPER(?)", (nome,))
        if cur.fetchone():
            flash("Já existe um script com esse nome.", "error")
            return redirect(request.url)

        if sistema and sistema not in ('Laudos UX', 'Laudos Flex'):
            flash("Sistema inválido. Escolha 'Laudos UX' ou 'Laudos Flex'.", "error")
            return redirect(request.url)

        arquivo_json_blob = None
        if sistema == 'Laudos UX':
            if not arquivo_json:
                flash("O arquivo JSON é obrigatório para o sistema Laudos UX.", "error")
                return redirect(request.url)
            if not arquivo_json.filename.endswith('.json'):
                flash("O arquivo deve ser no formato JSON.", "error")
                return redirect(request.url)
            arquivo_json_blob = arquivo_json.read()

        if linguagem and linguagem.upper() == 'C#' and not caminho_projeto:
            flash("O caminho do projeto é recomendado para scripts C#.", "warning")

        if aprovado and not aprovado_por:
            flash("O nome do aprovador é obrigatório quando o script é aprovado.", "error")
            return redirect(request.url)

        try:
            cur.execute("""
                INSERT INTO SCRIPTLAUDO (NOME, CODPACOTE, DESCRICAO, LINGUAGEM, CAMINHO_PROJETO, SISTEMA, APROVADO, DATA_VERIFICACAO, APROVADO_POR, ATIVO, ARQUIVO_JSON)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING CODSCRIPTLAUDO
            """, (nome, codpacote, descricao, linguagem, caminho_projeto, sistema, aprovado,
                  datetime.now() if aprovado else None, aprovado_por, ativo, arquivo_json_blob))
            codscriptlaudo = cur.fetchone()[0]

            # Salvar imagens
            for imagem in imagens:
                if imagem and imagem.filename:
                    caminho, nome_arquivo = save_file(imagem, 'static/uploads/interfaces', f"interface_{codscriptlaudo}")
                    if caminho:
                        cur.execute("""
                            INSERT INTO SCRIPT_ARQUIVOS (CODSCRIPTLAUDO, TIPO, CAMINHO, NOME_ARQUIVO, CODUSUARIO, DTHRULTMODIFICACAO)
                            VALUES (?, 'IMAGEM', ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (codscriptlaudo, caminho, nome_arquivo, codusuario))

            # Salvar PDFs
            for pdf in pdfs:
                if pdf and pdf.filename:
                    caminho, nome_arquivo = save_file(pdf, 'static/uploads/impressoes', f"impressao_{codscriptlaudo}")
                    if caminho:
                        cur.execute("""
                            INSERT INTO SCRIPT_ARQUIVOS (CODSCRIPTLAUDO, TIPO, CAMINHO, NOME_ARQUIVO, CODUSUARIO, DTHRULTMODIFICACAO)
                            VALUES (?, 'PDF', ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (codscriptlaudo, caminho, nome_arquivo, codusuario))

            conn.commit()
            current_app.logger.info(f"Script CODSCRIPTLAUDO={codscriptlaudo} cadastrado com sucesso.")
            flash("Script cadastrado com sucesso!", "success")
            return redirect(url_for('variaveis.home'))
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao cadastrar script: {str(e)}")
            flash(f"Erro ao cadastrar script: {str(e)}", "error")
            return redirect(request.url)

    return render_template('novo_script.html', pacotes=pacotes)

@scripts_bp.route('/editar_script/<int:codscriptlaudo>', methods=['GET', 'POST'])
def editar_script(codscriptlaudo):
    if 'usuario' not in session:
        current_app.logger.error("Sessão de usuário não encontrada.")
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    codusuario = session['usuario']['codusuario']

    cur.execute("SELECT CODPACOTE, NOME, DESCRICAO FROM PACOTES ORDER BY NOME")
    pacotes = cur.fetchall()

    if request.method == 'POST':
        nome = request.form['nome'].strip()
        codpacote = request.form['codpacote'] or None
        descricao = request.form['descricao'].strip() or None
        linguagem = request.form['linguagem'].strip() or None
        caminho_projeto = request.form['caminho_projeto'].strip() or None
        sistema = request.form['sistema'].strip() or None
        aprovado = 1 if 'aprovado' in request.form else 0
        aprovado_por = request.form['aprovado_por'].strip() or None if aprovado else None
        ativo = 1 if 'ativo' in request.form else 0
        arquivo_json = request.files.get('arquivo_json')
        imagens = request.files.getlist('imagens[]')
        pdfs = request.files.getlist('pdfs[]')

        if not nome:
            flash("O nome do script é obrigatório.", "error")
            return redirect(request.url)

        cur.execute("SELECT 1 FROM SCRIPTLAUDO WHERE UPPER(NOME) = UPPER(?) AND CODSCRIPTLAUDO != ?", (nome, codscriptlaudo))
        if cur.fetchone():
            flash("Já existe um script com esse nome.", "error")
            return redirect(request.url)

        if sistema and sistema not in ('Laudos UX', 'Laudos Flex'):
            flash("Sistema inválido. Escolha 'Laudos UX' ou 'Laudos Flex'.", "error")
            return redirect(request.url)

        arquivo_json_blob = None
        if sistema == 'Laudos UX' and arquivo_json and arquivo_json.filename:
            if not arquivo_json.filename.endswith('.json'):
                flash("O arquivo deve ser no formato JSON.", "error")
                return redirect(request.url)
            arquivo_json_blob = arquivo_json.read()

        if linguagem and linguagem.upper() == 'C#' and not caminho_projeto:
            flash("O caminho do projeto é recomendado para scripts C#.", "warning")

        if aprovado and not aprovado_por:
            flash("O nome do aprovador é obrigatório quando o script é aprovado.", "error")
            return redirect(request.url)

        try:
            cur.execute("""
                UPDATE SCRIPTLAUDO
                SET NOME = ?, CODPACOTE = ?, DESCRICAO = ?, LINGUAGEM = ?, CAMINHO_PROJETO = ?, 
                    SISTEMA = ?, APROVADO = ?, DATA_VERIFICACAO = CASE WHEN ? = 1 THEN COALESCE(DATA_VERIFICACAO, CURRENT_TIMESTAMP) ELSE NULL END,
                    APROVADO_POR = ?, ATIVO = ?, ARQUIVO_JSON = COALESCE(?, ARQUIVO_JSON)
                WHERE CODSCRIPTLAUDO = ?
            """, (nome, codpacote, descricao, linguagem, caminho_projeto, sistema, aprovado, aprovado, aprovado_por, ativo, arquivo_json_blob, codscriptlaudo))
            if cur.rowcount == 0:
                flash("Script não encontrado.", "error")
                return redirect(url_for('scripts.visualizar_scripts'))

            # Salvar novas imagens
            for imagem in imagens:
                if imagem and imagem.filename:
                    caminho, nome_arquivo = save_file(imagem, 'static/uploads/interfaces', f"interface_{codscriptlaudo}")
                    if caminho:
                        cur.execute("""
                            INSERT INTO SCRIPT_ARQUIVOS (CODSCRIPTLAUDO, TIPO, CAMINHO, NOME_ARQUIVO, CODUSUARIO, DTHRULTMODIFICACAO)
                            VALUES (?, 'IMAGEM', ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (codscriptlaudo, caminho, nome_arquivo, codusuario))

            # Salvar novos PDFs
            for pdf in pdfs:
                if pdf and pdf.filename:
                    caminho, nome_arquivo = save_file(pdf, 'static/uploads/impressoes', f"impressao_{codscriptlaudo}")
                    if caminho:
                        cur.execute("""
                            INSERT INTO SCRIPT_ARQUIVOS (CODSCRIPTLAUDO, TIPO, CAMINHO, NOME_ARQUIVO, CODUSUARIO, DTHRULTMODIFICACAO)
                            VALUES (?, 'PDF', ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (codscriptlaudo, caminho, nome_arquivo, codusuario))

            conn.commit()
            current_app.logger.info(f"Script CODSCRIPTLAUDO={codscriptlaudo} atualizado com sucesso.")
            flash("Script atualizado com sucesso!", "success")
            return redirect(url_for('scripts.visualizar_scripts'))
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao atualizar script CODSCRIPTLAUDO={codscriptlaudo}: {str(e)}")
            flash(f"Erro ao atualizar script: {str(e)}", "error")
            return redirect(request.url)

    try:
        cur.execute("""
            SELECT NOME, DESCRICAO, LINGUAGEM, CAMINHO_PROJETO, SISTEMA, CODPACOTE, APROVADO, DATA_VERIFICACAO, ATIVO,
                   CASE WHEN ARQUIVO_JSON IS NOT NULL THEN 1 ELSE 0 END AS TEM_ARQUIVO_JSON, APROVADO_POR
            FROM SCRIPTLAUDO
            WHERE CODSCRIPTLAUDO = ?
        """, (codscriptlaudo,))
        script = cur.fetchone()
        if not script:
            current_app.logger.warning(f"Script CODSCRIPTLAUDO={codscriptlaudo} não encontrado.")
            flash("Script não encontrado.", "error")
            return redirect(url_for('scripts.visualizar_scripts'))

        # Buscar arquivos
        cur.execute("""
            SELECT CODARQUIVO, TIPO, CAMINHO, NOME_ARQUIVO
            FROM SCRIPT_ARQUIVOS
            WHERE CODSCRIPTLAUDO = ?
            ORDER BY NOME_ARQUIVO
        """, (codscriptlaudo,))
        arquivos = cur.fetchall()
        imagens = [{'codarquivo': row[0], 'caminho': row[2], 'nome': row[3]} for row in arquivos if row[1] == 'IMAGEM']
        pdfs = [{'codarquivo': row[0], 'caminho': row[2], 'nome': row[3]} for row in arquivos if row[1] == 'PDF']

        script_data = {
            'nome': script[0],
            'descricao': script[1] or '',
            'linguagem': script[2] or '',
            'caminho_projeto': script[3] or '',
            'sistema': script[4] or '',
            'codpacote': script[5],
            'aprovado': bool(script[6]),
            'data_verificacao': script[7],
            'ativo': bool(script[8]),
            'tem_arquivo_json': bool(script[9]),
            'aprovado_por': script[10],
            'imagens': imagens,
            'pdfs': pdfs
        }

        return render_template('editar_script.html',
                               script=script_data,
                               codscriptlaudo=codscriptlaudo,
                               pacotes=pacotes)
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar formulário para CODSCRIPTLAUDO={codscriptlaudo}: {str(e)}")
        flash(f"Erro ao carregar formulário: {str(e)}", "error")
        return redirect(url_for('scripts.visualizar_scripts'))

@scripts_bp.route('/visualizar_scripts')
def visualizar_scripts():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    itens_por_pagina = 10
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * itens_por_pagina

    nome = request.args.get('nome', '').strip()
    sistema = request.args.get('sistema', '').strip()
    pacote = request.args.get('pacote', '').strip()
    aprovado = request.args.get('aprovado', '').strip()
    ativo = request.args.get('ativo', '').strip()

    where_clauses = []
    params = []
    if nome:
        where_clauses.append("UPPER(s.NOME) LIKE UPPER(?)")
        params.append(f"%{nome}%")
    if sistema in ('Laudos UX', 'Laudos Flex'):
        where_clauses.append("s.SISTEMA = ?")
        params.append(sistema)
    if pacote:
        where_clauses.append("s.CODPACOTE = ?")
        params.append(pacote)
    if aprovado in ('0', '1'):
        where_clauses.append("s.APROVADO = ?")
        params.append(aprovado)
    if ativo in ('0', '1'):
        where_clauses.append("s.ATIVO = ?")
        params.append(ativo)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    cur.execute(f"""
        SELECT COUNT(*)
        FROM SCRIPTLAUDO s
        {where_sql}
    """, params)
    total_scripts = cur.fetchone()[0]
    total_paginas = (total_scripts + itens_por_pagina - 1) // itens_por_pagina

    query = f"""
        SELECT FIRST {itens_por_pagina} SKIP {offset}
            s.CODSCRIPTLAUDO, s.NOME, s.DESCRICAO, s.LINGUAGEM, s.CAMINHO_PROJETO, s.SISTEMA,
            s.APROVADO, s.DATA_VERIFICACAO, s.ATIVO,
            CASE WHEN s.ARQUIVO_JSON IS NOT NULL THEN 1 ELSE 0 END AS TEM_ARQUIVO_JSON,
            s.APROVADO_POR, p.NOME
        FROM SCRIPTLAUDO s
        LEFT JOIN PACOTES p ON s.CODPACOTE = p.CODPACOTE
        {where_sql}
        ORDER BY s.NOME
    """
    cur.execute(query, params)
    scripts = cur.fetchall()

    scripts_detalhes = []
    for script in scripts:
        codscriptlaudo = script[0]
        # Buscar variáveis vinculadas
        cur.execute("""
            SELECT v.VARIAVEL, v.NOME
            FROM SCRIPTLAUDO_VARIAVEL sv
            JOIN VARIAVEIS v ON sv.CODVARIAVEL = v.CODVARIAVEL
            WHERE sv.CODSCRIPTLAUDO = ?
            ORDER BY v.NOME
        """, (codscriptlaudo,))
        variaveis = cur.fetchall()

        # Buscar arquivos de imagem e PDF
        cur.execute("""
            SELECT TIPO, CAMINHO, NOME_ARQUIVO
            FROM SCRIPT_ARQUIVOS
            WHERE CODSCRIPTLAUDO = ?
            ORDER BY NOME_ARQUIVO
        """, (codscriptlaudo,))
        arquivos = cur.fetchall()
        imagens = [{'caminho': row[1], 'nome': row[2]} for row in arquivos if row[0] == 'IMAGEM']
        pdfs = [{'caminho': row[1], 'nome': row[2]} for row in arquivos if row[0] == 'PDF']

        scripts_detalhes.append({
            'script': script,
            'variaveis': variaveis,
            'tem_arquivo_json': bool(script[9]),
            'pacote_nome': script[11],
            'imagens': imagens,
            'pdfs': pdfs
        })

    cur.execute("SELECT CODPACOTE, NOME, DESCRICAO FROM PACOTES ORDER BY NOME")
    pacotes = cur.fetchall()

    return render_template('visualizar_scripts.html',
                           scripts_detalhes=scripts_detalhes,
                           pagina=pagina,
                           total_paginas=total_paginas,
                           nome=nome,
                           sistema=sistema,
                           pacote=pacote,
                           aprovado=aprovado,
                           ativo=ativo,
                           pacotes=pacotes)

@scripts_bp.route('/exportar_json/<int:codscriptlaudo>')
def exportar_json(codscriptlaudo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    try:
        cur.execute("""
            SELECT ARQUIVO_JSON, NOME
            FROM SCRIPTLAUDO
            WHERE CODSCRIPTLAUDO = ? AND SISTEMA = 'Laudos UX' AND ARQUIVO_JSON IS NOT NULL
        """, (codscriptlaudo,))
        result = cur.fetchone()
        if not result:
            current_app.logger.warning(f"Arquivo JSON não encontrado para CODSCRIPTLAUDO={codscriptlaudo}")
            flash("Nenhum arquivo JSON encontrado para este script.", "error")
            return redirect(url_for('scripts.visualizar_scripts'))

        arquivo_json, nome_script = result
        return send_file(
            io.BytesIO(arquivo_json),
            mimetype='application/json',
            as_attachment=True,
            download_name=f"script_{nome_script.replace(' ', '_')}_{codscriptlaudo}.json"
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao exportar JSON para CODSCRIPTLAUDO={codscriptlaudo}: {str(e)}")
        flash(f"Erro ao exportar arquivo: {str(e)}", "error")
        return redirect(url_for('scripts.visualizar_scripts'))

@scripts_bp.route('/toggle_aprovacao/<int:codscriptlaudo>')
def toggle_aprovacao(codscriptlaudo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    aprovado_por = request.args.get('aprovado_por', '').strip() or None
    conn, cur = get_db()
    try:
        cur.execute("SELECT APROVADO FROM SCRIPTLAUDO WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
        script = cur.fetchone()
        if not script:
            flash("Script não encontrado.", "error")
            return redirect(url_for('scripts.visualizar_scripts'))

        novo_aprovado = 0 if script[0] else 1
        if novo_aprovado and not aprovado_por:
            flash("O nome do aprovador é obrigatório para aprovação.", "error")
            return redirect(url_for('scripts.visualizar_scripts'))

        cur.execute("""
            UPDATE SCRIPTLAUDO
            SET APROVADO = ?, DATA_VERIFICACAO = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END,
                APROVADO_POR = CASE WHEN ? = 1 THEN ? ELSE NULL END
            WHERE CODSCRIPTLAUDO = ?
        """, (novo_aprovado, novo_aprovado, novo_aprovado, aprovado_por, codscriptlaudo))
        conn.commit()
        flash("Status de aprovação atualizado com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao alternar aprovação para CODSCRIPTLAUDO={codscriptlaudo}: {str(e)}")
        flash(f"Erro ao atualizar aprovação: {str(e)}", "error")
    return redirect(url_for('scripts.visualizar_scripts'))

@scripts_bp.route('/toggle_ativo/<int:codscriptlaudo>')
def toggle_ativo(codscriptlaudo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    try:
        cur.execute("SELECT ATIVO FROM SCRIPTLAUDO WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
        script = cur.fetchone()
        if not script:
            flash("Script não encontrado.", "error")
            return redirect(url_for('scripts.visualizar_scripts'))

        novo_ativo = 0 if script[0] else 1
        cur.execute("""
            UPDATE SCRIPTLAUDO
            SET ATIVO = ?
            WHERE CODSCRIPTLAUDO = ?
        """, (novo_ativo, codscriptlaudo))
        conn.commit()
        flash("Status de ativo atualizado com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao alternar ativo para CODSCRIPTLAUDO={codscriptlaudo}: {str(e)}")
        flash(f"Erro ao atualizar ativo: {str(e)}", "error")
    return redirect(url_for('scripts.visualizar_scripts'))

@scripts_bp.route('/vincular_variaveis/<int:codscriptlaudo>', methods=['GET', 'POST'])
def vincular_variaveis(codscriptlaudo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    if not isinstance(session['usuario'], dict) or 'codusuario' not in session['usuario']:
        flash("Erro na sessão do usuário. Por favor, faça login novamente.", "error")
        return redirect(url_for('auth.logout'))

    cur.execute("SELECT NOME FROM SCRIPTLAUDO WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
    script = cur.fetchone()
    if not script:
        flash("Script não encontrado.", "error")
        return redirect(url_for('scripts.visualizar_scripts'))
    nome_script = script[0]

    if request.method == 'POST':
        variaveis = request.form.getlist('variaveis[]')
        try:
            cur.execute("DELETE FROM SCRIPTLAUDO_VARIAVEL WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
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

    cur.execute("SELECT CODVARIAVEL FROM SCRIPTLAUDO_VARIAVEL WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
    variaveis_associadas = [row[0] for row in cur.fetchall()]

    cur.execute("""
        SELECT v.CODVARIAVEL, v.NOME, v.SIGLA
        FROM VARIAVEIS v
        ORDER BY v.NOME
    """)
    variaveis = cur.fetchall()

    variaveis_detalhes = []
    for variavel in variaveis:
        codvariavel = variavel[0]
        cur.execute("""
            SELECT f.FORMULA
            FROM FORMULAS f
            JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
            WHERE fv.CODVARIAVEL = ?
        """, (codvariavel,))
        formula = cur.fetchone()
        formula_texto = formula[0] if formula else "Nenhuma fórmula"

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
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    try:
        cur.execute("SELECT ATIVO FROM SCRIPTLAUDO WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
        script = cur.fetchone()
        if not script:
            flash("Script não encontrado.", "error")
            return redirect(url_for('scripts.visualizar_scripts'))

        novo_ativo = 0 if script[0] else 1
        cur.execute("""
            UPDATE SCRIPTLAUDO
            SET ATIVO = ?
            WHERE CODSCRIPTLAUDO = ?
        """, (novo_ativo, codscriptlaudo))
        conn.commit()
        flash("Status de ativo atualizado com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao alternar ativo para CODSCRIPTLAUDO={codscriptlaudo}: {str(e)}")
        flash(f"Erro ao atualizar ativo: {str(e)}", "error")
    return redirect(url_for('scripts.visualizar_scripts'))
    

    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    if not isinstance(session['usuario'], dict) or 'codusuario' not in session['usuario']:
        flash("Erro na sessão do usuário. Por favor, faça login novamente.", "error")
        return redirect(url_for('auth.logout'))

    cur.execute("SELECT NOME FROM SCRIPTLAUDO WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
    script = cur.fetchone()
    if not script:
        flash("Script não encontrado.", "error")
        return redirect(url_for('scripts.visualizar_scripts'))
    nome_script = script[0]

    if request.method == 'POST':
        variaveis = request.form.getlist('variaveis[]')
        try:
            cur.execute("DELETE FROM SCRIPTLAUDO_VARIAVEL WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
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

    cur.execute("SELECT CODVARIAVEL FROM SCRIPTLAUDO_VARIAVEL WHERE CODSCRIPTLAUDO = ?", (codscriptlaudo,))
    variaveis_associadas = [row[0] for row in cur.fetchall()]

    cur.execute("""
        SELECT v.CODVARIAVEL, v.NOME, v.SIGLA
        FROM VARIAVEIS v
        ORDER BY v.NOME
    """)
    variaveis = cur.fetchall()

    variaveis_detalhes = []
    for variavel in variaveis:
        codvariavel = variavel[0]
        cur.execute("""
            SELECT f.FORMULA
            FROM FORMULAS f
            JOIN FORMULA_VARIAVEL fv ON f.CODFORMULA = fv.CODFORMULA
            WHERE fv.CODVARIAVEL = ?
        """, (codvariavel,))
        formula = cur.fetchone()
        formula_texto = formula[0] if formula else "Nenhuma fórmula"

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

@scripts_bp.route('/excluir_arquivo/<int:codarquivo>')
def excluir_arquivo(codarquivo):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    conn, cur = get_db()
    try:
        cur.execute("""
            SELECT CODSCRIPTLAUDO, TIPO, CAMINHO
            FROM SCRIPT_ARQUIVOS
            WHERE CODARQUIVO = ?
        """, (codarquivo,))
        arquivo = cur.fetchone()
        if not arquivo:
            flash("Arquivo não encontrado.", "error")
            return redirect(url_for('scripts.visualizar_scripts'))

        codscriptlaudo, tipo, caminho = arquivo
        cur.execute("DELETE FROM SCRIPT_ARQUIVOS WHERE CODARQUIVO = ?", (codarquivo,))
        if cur.rowcount > 0:
            # Remover arquivo do sistema de arquivos
            filepath = os.path.join(current_app.root_path, caminho.lstrip('/'))
            if os.path.exists(filepath):
                os.remove(filepath)
            conn.commit()
            current_app.logger.info(f"Arquivo CODARQUIVO={codarquivo} excluído com sucesso.")
            flash("Arquivo excluído com sucesso!", "success")
        else:
            flash("Erro ao excluir arquivo.", "error")
        return redirect(url_for('scripts.editar_script', codscriptlaudo=codscriptlaudo))
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao excluir arquivo CODARQUIVO={codarquivo}: {str(e)}")
        flash(f"Erro ao excluir arquivo: {str(e)}", "error")
        return redirect(url_for('scripts.visualizar_scripts'))
    


