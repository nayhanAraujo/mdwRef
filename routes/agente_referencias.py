from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session, g
from services import pubmed_client, db_updater, grok_client
from services.grok_client import get_reference_ranges_from_grok
import logging
from datetime import datetime
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
    # Carrega a lista de variáveis para o template
    variaveis_db_para_template = []
    try:
        _conn, _cur = db_updater.get_db_from_g()
        _cur.execute("SELECT SIGLA, NOME FROM VARIAVEIS ORDER BY SIGLA")
        variaveis_db_para_template = _cur.fetchall()
    except Exception as e:
        logger.error(f"Erro ao buscar lista de variáveis para template: {e}", exc_info=True)
        flash('Erro ao carregar dados iniciais da página.', 'danger')
        return render_template('interface_agente.html', variaveis_db=[])

    if request.method == 'POST':
        variable_sigla = request.form.get('variable_sigla', '').strip()
        years_back = request.form.get('years_back', '5')
        max_results = request.form.get('max_results', '10')

        if not variable_sigla:
            flash('Selecione uma medida para pesquisar.', 'warning')
            return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

        try:
            years_back = int(years_back)
            max_results = int(max_results)
            
            if years_back < 1 or years_back > 20:
                flash('O número de anos deve estar entre 1 e 20.', 'warning')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)
            
            if max_results < 1 or max_results > 50:
                flash('O número máximo de resultados deve estar entre 1 e 50.', 'warning')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

            # Obtém o nome completo da variável
            _conn_nome_var, _cur_nome_var = db_updater.get_db_from_g()
            _cur_nome_var.execute("SELECT NOME FROM VARIAVEIS WHERE SIGLA = ?", (variable_sigla,))
            var_record = _cur_nome_var.fetchone()
            
            if not var_record:
                flash(f'Variável com sigla "{variable_sigla}" não encontrada no banco de dados.', 'danger')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)
            
            measure_name = var_record[0]
            logger.info(f"Buscando artigos na PubMed para a medida '{measure_name}'")
            
            # Busca artigos na PubMed
            articles = pubmed_client.search_pubmed_references(
                measure_name=measure_name,
                years_back=years_back,
                max_results=max_results
            )

            if articles is None:
                flash('Erro ao consultar a API PubMed. Verifique os logs.', 'danger')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)
            
            if not articles:
                flash(f'Nenhum artigo encontrado para a medida "{measure_name}" nos últimos {years_back} anos.', 'info')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

            # Extrai normalidades de cada artigo
            normalized_data = []
            for article in articles:
                try:
                    extracted_ranges = get_reference_ranges_from_grok(article['abstract'])
                    if extracted_ranges:
                        # Filtra apenas as medidas relevantes
                        relevant_ranges = [
                            range_data for range_data in extracted_ranges
                            if measure_name.lower() in range_data['nome_medida'].lower()
                        ]
                        if relevant_ranges:
                            normalized_data.append({
                                'pmid': article['pmid'],
                                'title': article['title'],
                                'year': article['year'],
                                'url': article['url'],
                                'reference_ranges': relevant_ranges
                            })
                except Exception as e:
                    logger.error(f"Erro ao processar artigo {article['pmid']}: {e}")
                    continue

            return render_template(
                'interface_agente.html',
                variaveis_db=variaveis_db_para_template,
                articles=articles,
                normalized_data=normalized_data,
                measure_name=measure_name
            )

        except ValueError:
            flash('Valores inválidos para anos ou número máximo de resultados.', 'warning')
            return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)
        except Exception as e:
            logger.error(f"Erro ao processar a busca: {e}", exc_info=True)
            flash(f'Erro ao processar a busca: {str(e)}', 'danger')
            return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

    return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)