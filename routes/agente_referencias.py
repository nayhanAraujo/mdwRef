from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session, g
from werkzeug.utils import secure_filename
import os
from services import pdf_processor, grok_client, db_updater
import logging
from datetime import datetime
# O 'get_db.py' com contextmanager não é mais necessário se usarmos 'g' consistentemente
from functools import wraps

logger = logging.getLogger(__name__)
agente_bp = Blueprint('agente_referencias', __name__, url_prefix='/agente')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session or session['usuario'].get('role') != 'admin':
            flash("Acesso negado. Requer privilégios de administrador.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@agente_bp.route('/processar_documento', methods=['GET', 'POST'])
@admin_required
def processar_documento():
    variaveis_db_para_template = []
    try:

        _conn, _cur = db_updater.get_db_from_g() # Renomeado para evitar conflito de escopo
        _cur.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
        variaveis_db_para_template = _cur.fetchall()

    except Exception as e:
        logger.error(f"Erro ao buscar lista de variáveis para template: {e}", exc_info=True)
        flash('Erro ao carregar dados iniciais da página.', 'danger')

        return render_template('interface_agente.html', variaveis_db=[], now=datetime.now())

    template_args = {
        'variaveis_db': variaveis_db_para_template,
        'now': datetime.now()
    }

    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            flash('Nenhum arquivo PDF selecionado.', 'warning')
            return render_template('interface_agente.html', **template_args)

        file = request.files['pdf_file']
        variable_sigla = request.form.get('variable_sigla', '').strip()
        ref_titulo = request.form.get('ref_titulo', '').strip()
        ref_ano_str = request.form.get('ref_ano', '').strip()

        if not file.filename:
            flash('Nenhum arquivo selecionado.', 'warning')
            return render_template('interface_agente.html', **template_args)
        if not variable_sigla:
            flash('Sigla ou Nome da Variável é obrigatório.', 'warning')
            return render_template('interface_agente.html', **template_args)
        if not ref_titulo:
            flash('Título da Referência é obrigatório.', 'warning')
            return render_template('interface_agente.html', **template_args)
        if not ref_ano_str or not ref_ano_str.isdigit():
            flash('Ano da Referência é obrigatório e deve ser um número.', 'warning')
            return render_template('interface_agente.html', **template_args)

        ref_ano = int(ref_ano_str)

        try:
            upload_folder = current_app.config.get('UPLOAD_FOLDER_DOCUMENTOS', 'static/uploads_documentos_academicos')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            filename = secure_filename(file.filename)
            pdf_path = os.path.join(upload_folder, filename)
            file.save(pdf_path)
            logger.info(f"Arquivo PDF salvo em: {pdf_path}")

            texto_documento = pdf_processor.extract_text_from_pdf(pdf_path)
            if not texto_documento:
                flash(f'Não foi possível extrair texto do PDF: {filename}. O arquivo pode ser baseado em imagem ou estar corrompido.', 'danger')
                return render_template('interface_agente.html', **template_args)

            codvariavel = db_updater.get_variable_cod(variable_sigla) # Já usa get_db_from_g()
            if not codvariavel:
                flash(f'Variável com sigla/nome "{variable_sigla}" não encontrada no banco de dados.', 'danger')
                return render_template('interface_agente.html', **template_args)

            _conn_nome_var, _cur_nome_var = db_updater.get_db_from_g()
            _cur_nome_var.execute("SELECT NOME FROM VARIAVEIS WHERE CODVARIAVEL = ?", (codvariavel,))
            var_record = _cur_nome_var.fetchone()
            variable_name_human_readable = var_record[0] if var_record else variable_sigla

            logger.info(f"Consultando Grok para variável '{variable_name_human_readable}' do documento '{ref_titulo}' ({ref_ano}).")
            extracted_ranges = grok_client.get_reference_ranges_from_grok(texto_documento, variable_name_human_readable, ref_titulo, ref_ano)

            if extracted_ranges is None:
                flash('Erro ao consultar a API Grok. Verifique os logs.', 'danger')
                return render_template('interface_agente.html', **template_args)
            if not extracted_ranges: # Se a lista for vazia
                flash('Nenhuma faixa de normalidade encontrada pela API Grok para os critérios fornecidos.', 'info')
                return render_template('interface_agente.html', **template_args)

            logger.info(f"Faixas extraídas pelo Grok: {extracted_ranges}")

            codusuario_logado = session['usuario']['codusuario']
            codreferencia = db_updater.get_or_create_referencia(ref_titulo, ref_ano, codusuario=codusuario_logado) # Já usa get_db_from_g()
            if not codreferencia:
                flash(f'Erro ao obter ou criar a referência "{ref_titulo}" no banco de dados.', 'danger')
                return render_template('interface_agente.html', **template_args)

            normalidades_para_inserir = []
            for faixa in extracted_ranges:
                if 'sexo' not in faixa or 'unidade_medida' not in faixa: # Validação mínima
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
                if db_updater.insert_normalidade_batch(normalidades_para_inserir): # Já usa get_db_from_g()
                    flash(f'{len(normalidades_para_inserir)} faixas de normalidade inseridas com sucesso para a variável "{variable_sigla}" da referência "{ref_titulo}".', 'success')
                else:
                    flash('Erro ao inserir faixas de normalidade no banco de dados.', 'danger')
            else:
                flash('Nenhuma faixa válida para inserção foi retornada pela API Grok (após validação).', 'info')
            
            # Opcional: remover PDF após processamento
            # try:
            #     os.remove(pdf_path)
            #     logger.info(f"Arquivo PDF temporário removido: {pdf_path}")
            # except OSError as e:
            #     logger.error(f"Erro ao remover arquivo PDF temporário {pdf_path}: {e}")

        except Exception as e:
            logger.error(f"Erro no processamento do documento: {e}", exc_info=True)
            flash(f'Erro ao processar o documento: {str(e)}', 'danger')

        return redirect(url_for('agente_referencias.processar_documento')) # Redireciona para limpar o form POST

    # GET request
    return render_template('interface_agente.html', **template_args)