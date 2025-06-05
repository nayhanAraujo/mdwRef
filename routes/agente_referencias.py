from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session
from werkzeug.utils import secure_filename
import os
from services import pdf_processor, grok_client, db_updater # Seus módulos de serviço
import logging
from datetime import datetime # <<< ADICIONE ESTA LINHA

logger = logging.getLogger(__name__)
agente_bp = Blueprint('agente_referencias', __name__, url_prefix='/agente')

# Helper para verificar se o usuário está logado e é admin (adapte conforme sua lógica de roles)
from functools import wraps
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session or session['usuario'].get('role') != 'admin':
            flash("Acesso negado. Requer privilégios de administrador.", "danger")
            return redirect(url_for('auth.login')) # Ou outra página
        return f(*args, **kwargs)
    return decorated_function

@agente_bp.route('/processar_documento', methods=['GET', 'POST'])
@admin_required
def processar_documento():
    if request.method == 'POST':
        # ... (seu código POST existente) ...
        if 'pdf_file' not in request.files:
            flash('Nenhum arquivo PDF selecionado.', 'warning')
            # Passar 'now' também em caso de erro no POST para re-renderizar o template corretamente
            conn_get, cur_get = db_updater.get_db_from_app()
            cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
            variaveis_db = cur_get.fetchall()
            return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())


        file = request.files['pdf_file']
        variable_sigla = request.form.get('variable_sigla', '').strip()
        ref_titulo = request.form.get('ref_titulo', '').strip()
        ref_ano_str = request.form.get('ref_ano', '').strip()

        # Validar se o arquivo foi selecionado
        if not file.filename: # Adicionado para consistência
            flash('Nenhum arquivo selecionado.', 'warning')
            conn_get, cur_get = db_updater.get_db_from_app()
            cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
            variaveis_db = cur_get.fetchall()
            return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())


        if not variable_sigla:
            flash('Sigla ou Nome da Variável é obrigatório.', 'warning')
            conn_get, cur_get = db_updater.get_db_from_app()
            cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
            variaveis_db = cur_get.fetchall()
            return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())
        
        if not ref_titulo:
            flash('Título da Referência é obrigatório.', 'warning')
            conn_get, cur_get = db_updater.get_db_from_app()
            cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
            variaveis_db = cur_get.fetchall()
            return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())

        if not ref_ano_str or not ref_ano_str.isdigit():
            flash('Ano da Referência é obrigatório e deve ser um número.', 'warning')
            conn_get, cur_get = db_updater.get_db_from_app()
            cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
            variaveis_db = cur_get.fetchall()
            return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())
            
        ref_ano = int(ref_ano_str)

        try:
            # Salvar o arquivo PDF temporariamente
            upload_folder = current_app.config.get('UPLOAD_FOLDER_DOCUMENTOS', 'static/uploads_documentos_academicos')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(upload_folder, filename)
            file.save(pdf_path)
            logger.info(f"Arquivo PDF salvo em: {pdf_path}")

            # 1. Processar PDF
            texto_documento = pdf_processor.extract_text_from_pdf(pdf_path)
            if not texto_documento:
                flash(f'Não foi possível extrair texto do PDF: {filename}. O arquivo pode ser baseado em imagem ou estar corrompido.', 'danger')
                conn_get, cur_get = db_updater.get_db_from_app()
                cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
                variaveis_db = cur_get.fetchall()
                return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())


            # 2. Obter CODVARIAVEL e NOME da variável para o prompt
            codvariavel = db_updater.get_variable_cod(variable_sigla)
            if not codvariavel:
                flash(f'Variável com sigla/nome "{variable_sigla}" não encontrada no banco de dados.', 'danger')
                conn_get, cur_get = db_updater.get_db_from_app()
                cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
                variaveis_db = cur_get.fetchall()
                return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())
            
            conn, cur = db_updater.get_db_from_app()
            cur.execute("SELECT NOME FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
            var_record = cur.fetchone()
            variable_name_human_readable = var_record[0] if var_record else variable_sigla

            # 3. Consultar Grok
            logger.info(f"Consultando Grok para variável '{variable_name_human_readable}' do documento '{ref_titulo}' ({ref_ano}).")
            extracted_ranges = grok_client.get_reference_ranges_from_grok(texto_documento, variable_name_human_readable, ref_titulo, ref_ano)

            if extracted_ranges is None:
                flash('Erro ao consultar a API Grok. Verifique os logs.', 'danger')
                conn_get, cur_get = db_updater.get_db_from_app()
                cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
                variaveis_db = cur_get.fetchall()
                return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())
            if not extracted_ranges:
                flash('Nenhuma faixa de normalidade encontrada pela API Grok para os critérios fornecidos.', 'info')
                conn_get, cur_get = db_updater.get_db_from_app()
                cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
                variaveis_db = cur_get.fetchall()
                return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())
            
            logger.info(f"Faixas extraídas pelo Grok: {extracted_ranges}")

            # 4. Obter/Criar CODREFERENCIA
            codusuario_logado = session['usuario']['codusuario']
            codreferencia = db_updater.get_or_create_referencia(ref_titulo, ref_ano, codusuario=codusuario_logado)
            if not codreferencia:
                flash(f'Erro ao obter ou criar a referência "{ref_titulo}" no banco de dados.', 'danger')
                conn_get, cur_get = db_updater.get_db_from_app()
                cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
                variaveis_db = cur_get.fetchall()
                return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())


            # 5. Preparar e Inserir dados de NORMALIDADE
            normalidades_para_inserir = []
            for faixa in extracted_ranges:
                if 'sexo' not in faixa or 'unidade_medida' not in faixa :
                    logger.warning(f"Faixa ignorada por falta de campos obrigatórios: {faixa}")
                    continue
                
                normalidades_para_inserir.append({
                    'codvariavel': codvariavel,
                    'codreferencia': codreferencia,
                    'valormin': faixa.get('valor_min'),
                    'valormax': faixa.get('valor_max'),
                    'sexo': faixa.get('sexo', 'A')[:1].upper(),
                    'idade_min': faixa.get('idade_min'),
                    'idade_max': faixa.get('idade_max'),
                    'codusuario': codusuario_logado
                })
            
            if normalidades_para_inserir:
                if db_updater.insert_normalidade_batch(normalidades_para_inserir):
                    flash(f'{len(normalidades_para_inserir)} faixas de normalidade inseridas com sucesso para a variável "{variable_sigla}" da referência "{ref_titulo}".', 'success')
                else:
                    flash('Erro ao inserir faixas de normalidade no banco de dados.', 'danger')
            else:
                flash('Nenhuma faixa válida para inserção foi retornada pela API Grok.', 'info')

            # os.remove(pdf_path) 
            # logger.info(f"Arquivo PDF removido: {pdf_path}")

        except Exception as e:
            logger.error(f"Erro no processamento do documento: {e}", exc_info=True)
            flash(f'Erro ao processar o documento: {str(e)}', 'danger')
        
        # Mesmo após o POST, se houver redirecionamento para a mesma página, é bom ter 'now'
        conn_get, cur_get = db_updater.get_db_from_app()
        cur_get.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
        variaveis_db = cur_get.fetchall()
        return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now())


    # GET request
    conn, cur = db_updater.get_db_from_app()
    cur.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA") 
    variaveis_db = cur.fetchall()
    return render_template('interface_agente.html', variaveis_db=variaveis_db, now=datetime.now()) # <<< ADICIONE 'now' AQUI